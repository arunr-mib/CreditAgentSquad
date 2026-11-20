"""Early warning signals. Rules in code decide what fires; an agent may later explain and rank
the signals, but it cannot create or suppress one."""
import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calc import signals as sig
from app.calc.periods import FactValue, month_end, ytd_months
from app.core import ledger
from app.domain import periods_service
from app.domain.covenant_service import fact_provider, governing_terms
from app.domain.credit import Borrower, Facility
from app.domain.facts import Fact
from app.domain.facts_service import current_fact
from app.domain.monitoring import CovenantTest, Cycle, Signal, WorkItem
from app.domain.terms import ReportingObligation
from app.domain.work_items import raise_item
from app.guardrails.numbers import same_number

HISTORY_QUARTERS = 8
HISTORY_MONTHS = 14  # a venture borrower's history: the month and the thirteen before it


def period_end_steps(period_end: date, count: int, step: int = 3) -> list[date]:
    """`count` period ends ending at `period_end`, `step` months apart, oldest first."""
    ends, year, month = [], period_end.year, period_end.month
    for _ in range(count):
        ends.append(month_end(year, month))
        month -= step
        while month <= 0:
            year, month = year - 1, month + 12
    return sorted(ends)


def quarter_ends(period_end: date, count: int) -> list[date]:
    return period_end_steps(period_end, count, 3)


def monthly_ends(period_end: date, count: int) -> list[date]:
    return period_end_steps(period_end, count, 1)


def approved_plan(db: Session, borrower: Borrower, period_end: date) -> dict[date, Decimal] | None:
    found = approved_plan_with_terms(db, borrower, period_end)
    return None if found is None else found[0]


def approved_plan_with_terms(db: Session, borrower: Borrower,
                             period_end: date) -> tuple[dict[date, Decimal], uuid.UUID] | None:
    """The monthly revenue plan from the approved terms in force at `period_end` (design spec 5). Plan figures are
    terms data a person entered and a second person approved, never a budget column read from a borrower document. A
    proposed version never governs; a covenant on ARR is not a revenue plan. None when the terms hold no revenue plan."""
    plan: dict[date, Decimal] = {}
    version_id: uuid.UUID | None = None
    for facility in db.execute(select(Facility).where(Facility.borrower_id == borrower.id)).scalars():
        row, version = governing_terms(db, facility, period_end)
        if row is None:
            continue
        for covenant in version.terms.covenants:
            if covenant.archetype == "revenue_vs_plan" and covenant.typed_params.metric == "revenue":
                # overlapping plan months across facilities resolve last-wins (one facility per borrower in practice)
                plan.update({month.period_end: month.amount for month in covenant.typed_params.plan})
                version_id = row.id
    return (plan, version_id) if plan and version_id is not None else None


def _series(db: Session, borrower: Borrower, period_end: date) -> list[sig.PeriodMetrics]:
    provider = fact_provider(db, borrower.id)
    fye = borrower.fiscal_year_end_month
    has_base = db.execute(select(Facility.id).where(
        Facility.borrower_id == borrower.id, Facility.has_borrowing_base.is_(True))).first() is not None
    venture = borrower.template_id == "vc-1"  # which signal inputs exist
    monthly = periods_service.step_months(db, borrower, period_end) == 1  # how often the borrower reports
    ends = monthly_ends(period_end, HISTORY_MONTHS) if monthly else quarter_ends(period_end, HISTORY_QUARTERS)
    plan = approved_plan(db, borrower, period_end) if venture else None
    venture_inputs = sig.compute_signal_inputs(
        period_end, provider, fye_month=fye, template_id="vc-1", history_months=HISTORY_MONTHS - 1,
        plan=plan) if venture else None
    series = []
    for end in ends:
        if venture_inputs is not None:
            inputs = venture_inputs if end == period_end else venture_inputs.history.get(end)
            if inputs is None:
                continue  # a month with no inputs is skipped, never filled with zeros
        else:
            inputs = sig.compute_signal_inputs(end, provider, fye_month=fye)
        metrics: dict[str, Any] = dict(inputs.values)
        # the availability rule is about borrowing-base lines only; a line without one is
        # covered by the line-usage rule, so it gets no availability here
        availability = current_fact(db, borrower.id, "bb.availability", end, 0) if has_base else None
        metrics["availability"] = FactValue(availability.value, str(availability.id)) if availability else None
        headroom = {}
        for test in db.execute(select(CovenantTest).where(
                CovenantTest.borrower_id == borrower.id, CovenantTest.period_end == end,
                CovenantTest.superseded.is_(False), CovenantTest.covenant_id != "*")).scalars():
            # carry the stored fact, so the signal's basis links each figure to its source
            stored = current_fact(db, borrower.id, f"cov.{test.covenant_id}.headroom_pct", end, 0)
            headroom[test.covenant_id] = (FactValue(stored.value, str(stored.id))
                                          if stored is not None and stored.value == test.headroom_pct
                                          else test.headroom_pct)
        months = ytd_months(end, fye) if monthly else ((end.month - fye) % 12) or 12
        series.append(sig.PeriodMetrics(end, months, metrics, headroom))
    return series


def _system_rows(db: Session, borrower: Borrower) -> list[sig.SystemRow]:
    facts = db.execute(select(Fact).where(
        Fact.borrower_id == borrower.id, Fact.kind == "system", Fact.status.in_(("verified", "confirmed")),
        Fact.key.in_(("sys.revolver_outstanding", "sys.commitment", "sys.past_due_days")))).scalars()
    by_date: dict[date, dict[str, Decimal]] = {}
    for f in facts:
        by_date.setdefault(f.period_end, {})[f.key] = f.value
    rows = []
    for day, values in sorted(by_date.items()):
        if "sys.revolver_outstanding" in values and "sys.commitment" in values:
            rows.append(sig.SystemRow(day, values["sys.revolver_outstanding"], values["sys.commitment"],
                                      int(values.get("sys.past_due_days", Decimal(0)))))
    return rows


def run_signals(
    db: Session, *, borrower: Borrower, period_end: date, as_of: date, cycle: Cycle | None = None,
    origin: str = "live", raise_items: bool = True,
) -> list[Signal]:
    reporting = [sig.ReportingItem(ob.requirement_id, ob.period_end, ob.due_date, ob.received_date)
                 for ob in db.execute(select(ReportingObligation).where(
                     ReportingObligation.borrower_id == borrower.id,
                     ReportingObligation.period_end == period_end)).scalars()]
    evaluation = sig.evaluate_signals(period_end, _series(db, borrower, period_end),
                                      system_rows=_system_rows(db, borrower), reporting=reporting, as_of=as_of,
                                      template_id=borrower.template_id)
    stored: list[Signal] = []
    for fired in _one_per_period(evaluation.signals):
        basis = ledger._jsonable({**fired.basis, "subject": fired.subject,
                                  **_source_facts(db, borrower, period_end, fired)})
        # a signal closed because a correction changed its figures no longer stands in for a new one
        existing = db.execute(select(Signal).where(
            Signal.borrower_id == borrower.id, Signal.period_end == period_end, Signal.rule_id == fired.rule_id,
            Signal.status != "closed",
            Signal.basis["subject"].astext == (fired.subject or ""))).scalars().first() if fired.subject else \
            db.execute(select(Signal).where(
                Signal.borrower_id == borrower.id, Signal.period_end == period_end, Signal.status != "closed",
                Signal.rule_id == fired.rule_id)).scalars().first()
        if existing is not None:
            stored.append(existing)
            continue
        row = Signal(borrower_id=borrower.id, cycle_id=cycle.id if cycle else None, period_end=period_end,
                     rule_id=fired.rule_id, rule_version=sig.SIGNALS_VERSION, severity=fired.severity,
                     basis=basis, origin=origin)
        db.add(row)
        db.flush()
        ledger.record(db, actor_type="system", actor_id="signals", action="signal.fired", entity_type="signal",
                      entity_id=row.id, payload={"rule": fired.rule_id, "severity": fired.severity,
                                                 "period_end": period_end, "subject": fired.subject})
        stored.append(row)
        if raise_items and fired.severity == "high":
            chaser = _open_chaser(db, borrower.id, period_end) if fired.rule_id == "reporting_late" else None
            if chaser is not None:
                _attach_signal(db, chaser, row)
                continue
            raise_item(
                db, borrower_id=borrower.id, cycle_id=cycle.id if cycle else None, stage="signals",
                item_type="signal.high", severity="high",
                title=f"{borrower.name}: {fired.rule_id.replace('_', ' ')}",
                question="A high-severity early warning fired. Acknowledge it and decide whether the risk rating needs review?",
                allowed_decisions=["acknowledged", "rating_review_requested", "add_to_watch_list"],
                evidence={"signal_id": str(row.id), "rule_id": fired.rule_id, "basis": basis},
                actor=("system", "signals"), dedupe_key=f"signal.high:{row.id}")
    db.flush()
    return stored


def _open_chaser(db: Session, borrower_id: uuid.UUID, period_end: date) -> WorkItem | None:
    """The open chaser for the period's missing reporting, if the calendar raised one. Late
    reporting that is still missing is one exception: the chaser asks the person to act, and the
    early warning is recorded on it rather than raised as a second item."""
    return db.execute(select(WorkItem).join(Cycle, Cycle.id == WorkItem.cycle_id).where(
        WorkItem.borrower_id == borrower_id, WorkItem.item_type == "intake.missing_document",
        WorkItem.status == "open", Cycle.period_end == period_end)
        .order_by(WorkItem.created_at)).scalars().first()


def _attach_signal(db: Session, item: WorkItem, signal: Signal) -> None:
    attached = list(item.evidence.get("signals", []))
    if any(s.get("signal_id") == str(signal.id) for s in attached):
        return
    attached.append({"signal_id": str(signal.id), "rule_id": signal.rule_id})
    item.evidence = {**item.evidence, "signals": attached}  # a new dict, so the JSON column is saved
    ledger.record(db, actor_type="system", actor_id="signals", action="work_item.signal_attached",
                  entity_type="work_item", entity_id=item.id,
                  payload={"signal_id": signal.id, "rule_id": signal.rule_id, "severity": signal.severity,
                           "period_end": signal.period_end})


def facility_for_signals(db: Session, borrower_id: uuid.UUID) -> Facility | None:
    return db.execute(select(Facility).where(Facility.borrower_id == borrower_id)
                      .order_by(Facility.has_borrowing_base.desc())).scalars().first()


def _one_per_period(fired: list[sig.Signal]) -> list[sig.Signal]:
    """Late reporting is one signal per period: the most overdue item, with the others listed."""
    late = [f for f in fired if f.rule_id == "reporting_late"]
    if len(late) <= 1:
        return fired
    worst = max(late, key=lambda f: f.basis.get("days_late", 0))
    merged = sig.Signal(worst.rule_id, worst.severity, worst.period_end, None, {
        **worst.basis, "late_items": [{"requirement_id": f.basis.get("requirement_id"),
                                       "days_late": f.basis.get("days_late"), "due_date": f.basis.get("due_date")}
                                      for f in sorted(late, key=lambda f: -f.basis.get("days_late", 0))]})
    out, placed = [], False
    for f in fired:
        if f.rule_id != "reporting_late":
            out.append(f)
        elif not placed:
            out.append(merged)
            placed = True
    return out


_RULES = {rule.id: rule for rule in sig.RULES}


# the stored metric behind each venture rule's figures ("plan_ratio" is stored by `store_plan_ratio`)
VENTURE_RULE_METRIC = {"runway_below_watch": "rml", "runway_falling": "rml", "burn_rising": "avg_net_burn",
                       "revenue_below_plan": "plan_ratio"}


def _venture_source_facts(db: Session, borrower: Borrower, period_end: date, fired: sig.Signal) -> dict[str, Any]:
    """Store each figure of a venture signal as a calculated fact and carry its id on the figure, so the basis
    shows nothing without a source. A figure whose stored fact disagrees with it is left unlinked, never forced."""
    from app.domain.metrics_service import store_metric, store_plan_ratio

    metric = VENTURE_RULE_METRIC[fired.rule_id]
    governing = approved_plan_with_terms(db, borrower, period_end) if metric == "plan_ratio" else None

    def link(point: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(point, dict) or "value" not in point:
            return point
        end = point["period_end"]
        if metric == "plan_ratio":
            plan, terms_version_id = governing if governing else ({}, None)
            months = monthly_ends(end, 3)
            fact = (store_plan_ratio(db, borrower, end, {m: plan[m] for m in months}, terms_version_id)
                    if governing and all(m in plan for m in months) else None)
        else:
            fact = store_metric(db, borrower, metric, end)
        if fact is None or not same_number(fact.value, Decimal(str(point["value"]))):
            return point
        return {**point, "fact_id": str(fact.id)}

    basis, ids = fired.basis, {}
    out: dict[str, Any] = {}
    for name in ("current", "prior"):
        if name in basis:
            out[name] = link(basis[name])
            if out[name] and out[name].get("fact_id"):
                ids[name] = out[name]["fact_id"]
    if "values" in basis:
        out["values"] = [link(p) for p in basis["values"]]
        ids.update({p["period_end"].isoformat(): p["fact_id"] for p in out["values"] if p and p.get("fact_id")})
        if out["values"] and out["values"][-1] and out["values"][-1].get("fact_id"):
            ids["current"] = out["values"][-1]["fact_id"]
    out["metric_fact_ids"] = ids
    return out


def _source_facts(db: Session, borrower: Borrower, period_end: date, fired: sig.Signal) -> dict[str, Any]:
    """Stored facts behind a signal's figures: the metric at the period and a year earlier, or the
    system-of-record balances on the row's date. A figure shown to a person must have a source."""
    from app.calc import metrics as lib
    from app.calc.periods import same_period_prior_year
    from app.domain.metrics_service import EXTRA, store_metric

    out: dict[str, Any] = {}
    if borrower.template_id == "vc-1" and fired.rule_id in VENTURE_RULE_METRIC:
        out.update(_venture_source_facts(db, borrower, period_end, fired))
        metric = None
    else:
        metric = _RULES[fired.rule_id].params.get("metric") if fired.rule_id in _RULES else None
    if metric and (metric in EXTRA or metric in lib.METRICS):
        ids = {}
        for label, end in (("current", period_end), ("year_earlier", same_period_prior_year(period_end))):
            fact = store_metric(db, borrower, metric, end)
            if fact is not None:
                ids[label] = str(fact.id)
        out["metric_fact_ids"] = ids
    row_date = fired.basis.get("date")
    if row_date is not None:
        ids = {}
        for key in ("sys.revolver_outstanding", "sys.commitment", "sys.past_due_days"):
            fact = current_fact(db, borrower.id, key, row_date, 0)
            if fact is not None:
                ids[key] = str(fact.id)
        out["system_fact_ids"] = ids
    return out
