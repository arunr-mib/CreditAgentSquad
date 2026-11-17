"""Early warning signals. Rules in code decide what fires; an agent may later explain and rank
the signals, but it cannot create or suppress one."""
import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calc import signals as sig
from app.calc.periods import FactValue, month_end
from app.core import ledger
from app.domain.covenant_service import fact_provider
from app.domain.credit import Borrower, Facility
from app.domain.facts import Fact
from app.domain.facts_service import current_fact
from app.domain.monitoring import CovenantTest, Cycle, Signal
from app.domain.terms import ReportingObligation
from app.domain.work_items import raise_item

HISTORY_QUARTERS = 8


def quarter_ends(period_end: date, count: int) -> list[date]:
    ends, year, month = [], period_end.year, period_end.month
    for _ in range(count):
        ends.append(month_end(year, month))
        month -= 3
        if month <= 0:
            year, month = year - 1, month + 12
    return sorted(ends)


def _series(db: Session, borrower: Borrower, period_end: date) -> list[sig.PeriodMetrics]:
    provider = fact_provider(db, borrower.id)
    fye = borrower.fiscal_year_end_month
    series = []
    for end in quarter_ends(period_end, HISTORY_QUARTERS):
        inputs = sig.compute_signal_inputs(end, provider, fye_month=fye)
        metrics: dict[str, Any] = dict(inputs.values)
        availability = current_fact(db, borrower.id, "bb.availability", end, 0)
        metrics["availability"] = FactValue(availability.value, str(availability.id)) if availability else None
        headroom = {}
        for test in db.execute(select(CovenantTest).where(
                CovenantTest.borrower_id == borrower.id, CovenantTest.period_end == end,
                CovenantTest.superseded.is_(False), CovenantTest.covenant_id != "*")).scalars():
            headroom[test.covenant_id] = test.headroom_pct
        months = ((end.month - fye) % 12) or 12
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
                                      system_rows=_system_rows(db, borrower), reporting=reporting, as_of=as_of)
    stored: list[Signal] = []
    for fired in evaluation.signals:
        basis = ledger._jsonable({**fired.basis, "subject": fired.subject})
        existing = db.execute(select(Signal).where(
            Signal.borrower_id == borrower.id, Signal.period_end == period_end, Signal.rule_id == fired.rule_id,
            Signal.basis["subject"].astext == (fired.subject or ""))).scalar_one_or_none() if fired.subject else \
            db.execute(select(Signal).where(
                Signal.borrower_id == borrower.id, Signal.period_end == period_end,
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


def facility_for_signals(db: Session, borrower_id: uuid.UUID) -> Facility | None:
    return db.execute(select(Facility).where(Facility.borrower_id == borrower_id)
                      .order_by(Facility.has_borrowing_base.desc())).scalars().first()
