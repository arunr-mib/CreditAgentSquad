"""What happens to results when a person corrects, or rejects, a figure they were calculated from.

Nothing calculated from the old figure may stay in use. Every result that names it, directly or
through another result, is retired; statement totals, review metrics and covenant tests for the
periods touched are run again from the figures now on file; and a person is told when a covenant
outcome changed. If the corrected statements no longer foot, the totals are not stored and the
question goes to a person, as it would for a new spread.
"""
import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calc import template
from app.core import ledger
from app.domain import facts_service
from app.domain.credit import Borrower, Facility
from app.domain.documents import Document
from app.domain.facts import USABLE_STATUSES, CalcRun, Fact
from app.domain.monitoring import CovenantTest, Cycle
from app.domain.work_items import raise_item

_ABSENT = "absent_lines_verified_by_footing"
_SUM = "sum_of_printed_rows"


def dependents(db: Session, roots: list[Fact]) -> list[Fact]:
    """Usable facts calculated from any of `roots`, directly or through other results, in the
    order they were written."""
    if not roots:
        return []
    borrower_id = roots[0].borrower_id
    runs_by_input: dict[str, set[uuid.UUID]] = {}
    for run_id, inputs in db.execute(select(CalcRun.id, CalcRun.inputs).where(CalcRun.borrower_id == borrower_id)):
        for entry in inputs or []:
            if isinstance(entry, dict) and entry.get("fact_id"):
                runs_by_input.setdefault(str(entry["fact_id"]), set()).add(run_id)
    found: dict[uuid.UUID, Fact] = {}
    seen_runs: set[uuid.UUID] = set()
    frontier = [f.id for f in roots]
    root_ids = set(frontier)
    while frontier:
        run_ids = runs_by_input.get(str(frontier.pop()), set()) - seen_runs
        if not run_ids:
            continue
        seen_runs |= run_ids
        for fact in db.execute(select(Fact).where(Fact.calc_run_id.in_(run_ids))).scalars():
            if fact.id not in found and fact.id not in root_ids:
                found[fact.id] = fact
                frontier.append(fact.id)
    return sorted((f for f in found.values() if f.status in USABLE_STATUSES), key=lambda f: f.seq)


def _statement_totals(db: Session, fact: Fact) -> list[Fact]:
    """The stored totals for the statement period a line belongs to, however they were stored.
    History loaded from a system of record has totals with no calculation naming their inputs,
    so they are found by period, not by lineage."""
    key = fact.key.removeprefix(template.STATED_PREFIX)
    if key not in template.LINE_BY_KEY:
        return []
    computed = [line.key for line in template.LINES if line.computed]
    return list(db.execute(select(Fact).where(
        Fact.borrower_id == fact.borrower_id, Fact.period_end == fact.period_end, Fact.key.in_(computed),
        Fact.status.in_(USABLE_STATUSES))).scalars())


def _cycle(db: Session, borrower_id: uuid.UUID, period_end: date) -> Cycle | None:
    return db.execute(select(Cycle).where(Cycle.borrower_id == borrower_id, Cycle.period_end == period_end)
                      .order_by(Cycle.created_at.desc())).scalars().first()


def _flow_months(db: Session, old: Fact, stale: list[Fact], cycle: Cycle | None) -> int | None:
    if old.months:
        return old.months
    flows = [f.months for f in stale if f.period_end == old.period_end and f.months
             and f.key in template.LINE_BY_KEY]
    if flows:
        return max(flows)
    if cycle is not None:
        return cycle.months
    months = db.execute(select(Fact.months).where(
        Fact.borrower_id == old.borrower_id, Fact.period_end == old.period_end, Fact.key == "is.revenue",
        Fact.status.in_(USABLE_STATUSES)).order_by(Fact.months.desc())).scalars().first()
    return months or None


def _current_tests(db: Session, facility_id: uuid.UUID, period_end: date) -> dict[str, str]:
    return {t.covenant_id: t.outcome for t in db.execute(select(CovenantTest).where(
        CovenantTest.facility_id == facility_id, CovenantTest.period_end == period_end,
        CovenantTest.superseded.is_(False))).scalars()}


def _totals_were_stored(db: Session, old: Fact) -> bool:
    """True when this statement period once had totals, even if none is in use now (they are
    withheld while corrected figures do not foot)."""
    if old.key.removeprefix(template.STATED_PREFIX) not in template.LINE_BY_KEY:
        return False
    computed = [line.key for line in template.LINES if line.computed]
    return db.execute(select(Fact.id).where(
        Fact.borrower_id == old.borrower_id, Fact.period_end == old.period_end, Fact.key.in_(computed),
        Fact.status == "superseded").limit(1)).first() is not None


def _restore_metrics(db: Session, borrower: Borrower) -> list[dict[str, Any]]:
    """Metrics that were retired and have nothing in their place are computed again; one that
    cannot be measured from the figures on file stays absent."""
    from app.domain import metrics_service

    retired = db.execute(select(Fact.key, Fact.period_end).where(
        Fact.borrower_id == borrower.id, Fact.key.like("metric.%"), Fact.status == "superseded").distinct()).all()
    out = []
    for key, period_end in sorted(retired, key=lambda row: (row[1], row[0])):
        if facts_service.current_fact(db, borrower.id, key, period_end, 0) is not None:
            continue
        again = metrics_service.store_metric(db, borrower, key.removeprefix("metric."), period_end)
        out.append({"key": key, "period_end": period_end.isoformat(), "fact_id": str(again.id) if again else None})
    return out


def _retest(db: Session, borrower: Borrower, pairs: set[tuple[uuid.UUID, date]], before: dict, *,
            raise_items: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from app.domain.covenant_service import run_covenant_tests

    results, changed = [], []
    for facility_id, period_end in sorted(pairs, key=lambda pair: (pair[1], str(pair[0]))):
        run_covenant_tests(db, borrower=borrower, facility=db.get(Facility, facility_id), period_end=period_end,
                           cycle=_cycle(db, borrower.id, period_end), raise_items=raise_items)
        names = {t.covenant_id: t.covenant_name for t in db.execute(select(CovenantTest).where(
            CovenantTest.facility_id == facility_id, CovenantTest.period_end == period_end,
            CovenantTest.superseded.is_(False))).scalars()}
        for covenant_id, outcome in sorted(_current_tests(db, facility_id, period_end).items()):
            entry = {"facility_id": str(facility_id), "period_end": period_end.isoformat(),
                     "covenant_id": covenant_id, "covenant_name": names.get(covenant_id, covenant_id),
                     "before": before[(facility_id, period_end)].get(covenant_id), "after": outcome}
            results.append(entry)
            if entry["before"] != entry["after"]:
                changed.append(entry)
    return results, changed


def _withheld_tests(db: Session, borrower_id: uuid.UUID, from_period: date) -> set[tuple[uuid.UUID, date]]:
    """Covenant tests that could not be run from this period on: candidates to run again."""
    return {(t.facility_id, t.period_end) for t in db.execute(select(CovenantTest).where(
        CovenantTest.borrower_id == borrower_id, CovenantTest.period_end >= from_period,
        CovenantTest.superseded.is_(False), CovenantTest.outcome == "cannot_test",
        CovenantTest.covenant_id != "*")).scalars()}


def _tell_a_person(db: Session, borrower: Borrower, period_end: date, changed: list[dict[str, Any]],
                   evidence: dict[str, Any]) -> None:
    item = raise_item(
        db, borrower_id=borrower.id, item_type="fact.correction_changed_outcome", severity="high",
        blocks_stage=False, stage="covenant_testing", cycle_id=getattr(_cycle(db, borrower.id, period_end), "id", None),
        title=f"{borrower.name}: a corrected figure changed a covenant outcome",
        question="A figure was corrected after covenant tests had been recorded, and at least one outcome is now "
                 "different. Earlier decisions, commentary and packages used the old outcome. Has the change "
                 "been reviewed?",
        allowed_decisions=["reviewed", "escalate_to_committee"], evidence={**evidence, "changes": changed},
        actor=("system", "corrections"), dedupe_key=f"fact.correction_changed_outcome:{borrower.id}:{period_end}")
    if item.evidence.get("changes") != changed:  # an open item for the period: add to it
        item.evidence = {**item.evidence, "changes": [*item.evidence.get("changes", []), *changed]}


def _refresh_signals(db: Session, borrower: Borrower, from_period: date) -> list[dict[str, Any]]:
    """Early warning signals from this period on were computed from figures that have changed.
    Each is closed, with any open question it raised, and the rules are run again on the figures
    now on file."""
    from app.core import clock
    from app.domain.monitoring import Signal, WorkItem
    from app.domain.signals_service import run_signals

    stale = list(db.execute(select(Signal).where(
        Signal.borrower_id == borrower.id, Signal.period_end >= from_period, Signal.status != "closed")).scalars())
    if not stale:
        return []
    closed = {str(s.id) for s in stale}
    for signal in stale:
        signal.status = "closed"
    for item in db.execute(select(WorkItem).where(
            WorkItem.borrower_id == borrower.id, WorkItem.item_type == "signal.high", WorkItem.status == "open")).scalars():
        if item.evidence.get("signal_id") in closed:
            item.status = "dismissed"
            ledger.record(db, actor_type="system", actor_id="corrections", action="work_item.dismissed",
                          entity_type="work_item", entity_id=item.id,
                          payload={"reason": "the signal was computed from a figure that has since been corrected"})
    out = []
    for period_end in sorted({s.period_end for s in stale}):
        fired = run_signals(db, borrower=borrower, period_end=period_end, as_of=clock.today(db),
                            cycle=_cycle(db, borrower.id, period_end))
        out.append({"period_end": period_end.isoformat(),
                    "closed": sorted(s.rule_id for s in stale if s.period_end == period_end),
                    "fired": sorted(s.rule_id for s in fired)})
    ledger.record(db, actor_type="system", actor_id="corrections", action="signals.refreshed", entity_type="borrower",
                  entity_id=borrower.id, payload={"periods": out})
    return out


def recalculate(db: Session, old: Fact, new: Fact | None, user_id: uuid.UUID) -> dict[str, Any]:
    """Bring every result that used `old` back in line after it was replaced by `new` (or
    rejected, when `new` is None). Returns a summary for the caller and the ledger."""
    from app.agents import spreading  # imported here: it imports the workflow

    totals = _statement_totals(db, old)
    stale = {f.id: f for f in totals + dependents(db, [old, *totals])}
    refoot = bool(totals) or _totals_were_stored(db, old)
    summary: dict[str, Any] = {"retired": len(stale), "totals": None, "metrics": [], "covenants": []}
    if not stale and not refoot and not old.key.startswith("cert."):
        return summary
    runs = {r.id: r for r in db.execute(select(CalcRun).where(
        CalcRun.id.in_({f.calc_run_id for f in stale.values() if f.calc_run_id}))).scalars()}
    formula = {f.id: runs[f.calc_run_id].formula_key if f.calc_run_id in runs else None for f in stale.values()}
    borrower = db.get(Borrower, old.borrower_id)
    pairs = {(f.facility_id, f.period_end) for f in stale.values() if f.key.startswith("cov.") and f.facility_id}
    pairs |= _withheld_tests(db, borrower.id, old.period_end)
    if old.key.startswith("cert."):
        # what the borrower reported is compared with the calculation at test time, so a
        # corrected certificate figure means the period's covenants are tested again
        pairs |= {(t.facility_id, t.period_end) for t in db.execute(select(CovenantTest).where(
            CovenantTest.borrower_id == borrower.id, CovenantTest.period_end == old.period_end,
            CovenantTest.superseded.is_(False), CovenantTest.covenant_id != "*")).scalars()}
    before = {pair: _current_tests(db, *pair) for pair in pairs}

    if stale:
        for fact in stale.values():
            fact.status = "superseded"
        ledger.record(db, actor_type="user", actor_id=user_id, action="fact.results_retired", entity_type="fact",
                      entity_id=old.id,
                      payload={"replaced_by": new.id if new else None,
                               "retired": [{"fact_id": f.id, "key": f.key, "period_end": f.period_end,
                                            "value": f.value} for f in sorted(stale.values(), key=lambda f: f.seq)]})
        db.flush()

    # several printed rows added into one line: add them again with the replacement
    for fact in stale.values():
        run = runs.get(fact.calc_run_id)
        if run is None or run.formula_key != _SUM:
            continue
        ids = [entry["fact_id"] for entry in run.inputs]
        if str(old.id) not in ids:
            continue
        parts = [new if i == str(old.id) else db.get(Fact, uuid.UUID(i)) for i in ids]
        parts = [p for p in parts if p is not None and p.status in USABLE_STATUSES]
        if parts:
            spreading._sum_fact(db, borrower, fact.key, parts)

    # statement totals for the period, when the corrected figure is a statement line
    if refoot:
        cycle = _cycle(db, borrower.id, old.period_end)
        months = _flow_months(db, old, list(stale.values()), cycle)
        if months is None:
            summary["totals"] = "not_recalculated"
        else:
            absent = sorted(f.key for f in stale.values()
                            if formula[f.id] == _ABSENT and f.period_end == old.period_end)
            document = db.get(Document, old.document_id) if old.document_id else None
            result = spreading.finalize_spread(
                db, borrower=borrower, document=document, period_end=old.period_end, months=months,
                scale=old.scale_as_reported or 1, absent=absent, cycle=cycle)
            summary["totals"] = "recalculated" if result.status == "spread" else "does_not_foot"

    # while the statements do not foot the tests cannot run; the footing question is the one
    # put to a person, so no second question is raised for each test
    footed = summary["totals"] in (None, "recalculated")
    summary["metrics"] = _restore_metrics(db, borrower)
    summary["covenants"], changed = _retest(db, borrower, pairs, before, raise_items=footed)
    if changed and footed:
        _tell_a_person(db, borrower, old.period_end, changed,
                       {"corrected_fact_id": str(old.id), "replacement_fact_id": str(new.id) if new else None})
    summary["signals"] = _refresh_signals(db, borrower, old.period_end) if footed and (stale or refoot) else []
    ledger.record(db, actor_type="system", actor_id="corrections", action="fact.results_recalculated",
                  entity_type="fact", entity_id=new.id if new else old.id, payload=summary)
    db.flush()
    return summary


def refresh_after_repair(db: Session, borrower: Borrower, period_end: date) -> dict[str, Any]:
    """After a person has put a held statement right and its totals are stored again: restore the
    metrics and run the covenant tests that were waiting for them."""
    pairs = _withheld_tests(db, borrower.id, period_end)
    before = {pair: _current_tests(db, *pair) for pair in pairs}
    summary: dict[str, Any] = {"metrics": _restore_metrics(db, borrower)}
    summary["covenants"], changed = _retest(db, borrower, pairs, before, raise_items=True)
    if changed:
        _tell_a_person(db, borrower, period_end, changed, {})
    summary["signals"] = _refresh_signals(db, borrower, period_end)
    if summary["metrics"] or summary["covenants"] or summary["signals"]:
        ledger.record(db, actor_type="system", actor_id="corrections", action="fact.results_recalculated",
                      entity_type="borrower", entity_id=borrower.id, payload=summary)
        db.flush()
    return summary


def correct(db: Session, fact: Fact, *, value: Decimal, user_id: uuid.UUID, reason: str) -> tuple[Fact, dict[str, Any]]:
    """A person replaces a figure, and everything calculated from it is brought back in line."""
    if fact.kind == "calculated":
        raise ValueError("a calculated figure cannot be corrected; correct the figure it was calculated from")
    if fact.status not in ("proposed", "verified", "confirmed"):
        raise ValueError(f"a {fact.status} figure cannot be corrected")
    if not value.is_finite():
        raise ValueError("a figure must be a finite number")
    new = facts_service.correct_fact(db, fact, value=value, user_id=user_id, reason=reason)
    return new, recalculate(db, fact, new, user_id)


def enter(db: Session, *, borrower_id: uuid.UUID, key: str, period_end: date, months: int, value: Decimal,
          user_id: uuid.UUID, reason: str) -> tuple[Fact, dict[str, Any]]:
    """A person keys a statement line by hand. If the line already has a figure this is a
    correction; if it was taken as zero because the statement did not print it, the zero goes."""
    if not value.is_finite():
        raise ValueError("a figure must be a finite number")
    existing = facts_service.current_fact(db, borrower_id, key, period_end, months)
    if existing is not None and existing.kind != "calculated":
        return correct(db, existing, value=value, user_id=user_id, reason=reason)
    new = facts_service.add_fact(
        db, borrower_id=borrower_id, key=key, period_end=period_end, months=months, value=value, kind="manual",
        entered_by=user_id, reason=reason, supersedes_fact_id=existing.id if existing else None,
        actor=("user", str(user_id)))
    if existing is not None:
        existing.status = "superseded"
        ledger.record(db, actor_type="user", actor_id=user_id, action="fact.superseded", entity_type="fact",
                      entity_id=existing.id, payload={"by": new.id, "old_value": existing.value, "new_value": value,
                                                      "reason": reason})
        db.flush()
    return new, recalculate(db, existing or new, new, user_id)


def reject(db: Session, fact: Fact, *, user_id: uuid.UUID, reason: str) -> dict[str, Any]:
    """A person sets a figure aside; nothing calculated from it stays in use."""
    if fact.kind == "calculated":
        raise ValueError("a calculated figure cannot be rejected; reject the figure it was calculated from")
    facts_service.reject_fact(db, fact, user_id=user_id, reason=reason)
    return recalculate(db, fact, None, user_id)
