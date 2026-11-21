"""The one measure each client is watched by, period by period: runway in months for a venture client (`vc-1`), the
tightest covenant headroom for a C&I client. Every point is a stored fact or says why there is none; nothing is
calculated here and an unmeasured point is never a zero."""
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.fact_labels import FactLabels, fact_summary
from app.domain.credit import Borrower
from app.domain.facts import USABLE_STATUSES, Fact
from app.domain.monitoring import CovenantTest, Cycle
from app.squad.words import NOTE_WORDS

RUNWAY_COVENANT = "min_runway_months"
NOT_MEASURED = "Not measured"
NOT_MEANINGFUL = NOTE_WORDS["not_meaningful_cash_flow_positive"]


def _periods(db: Session, borrower: Borrower, limit: int) -> list[date]:
    ends = sorted(set(db.execute(select(Cycle.period_end).where(Cycle.borrower_id == borrower.id)).scalars()))
    return ends[-limit:]


def _runway_for(tests: list[CovenantTest], facts: dict[Any, Fact]) -> tuple[Fact | None, str | None]:
    """The stored runway covenant value for one period (the tightest if several loans test it), else the stored
    reason there is none (the test's own note), else nothing."""
    values = [facts[t.value_fact_id] for t in tests if t.value_fact_id in facts]
    if values:
        return min(values, key=lambda f: f.value), None
    if any(t.note == "not_meaningful_cash_flow_positive" for t in tests):
        return None, NOT_MEANINGFUL
    return None, None


def measure_series(db: Session, borrower: Borrower, limit: int = 6, labels: FactLabels | None = None) -> dict[str, Any]:
    """Read from the live (non-superseded) covenant tests, the same source the covenants view reads, so the two screens
    cannot disagree: runway is the runway covenant's stored value fact (its stored note says "not meaningful");
    headroom is the tightest stored headroom among the period's live tests."""
    labels = labels or FactLabels(db)
    periods = _periods(db, borrower, limit)
    venture = borrower.template_id == "vc-1"
    tests = db.execute(select(CovenantTest).where(
        CovenantTest.borrower_id == borrower.id, CovenantTest.superseded.is_(False),
        CovenantTest.period_end.in_(periods or [None]))).scalars().all()
    by_period: dict[date, list[CovenantTest]] = {}
    for t in tests:
        by_period.setdefault(t.period_end, []).append(t)
    wanted: dict[Any, None] = {}
    for t in tests:
        if t.value_fact_id:
            wanted[t.value_fact_id] = None
    facts: dict[Any, Fact] = {f.id: f for f in db.execute(select(Fact).where(
        Fact.id.in_(list(wanted) or [None]), Fact.status.in_(USABLE_STATUSES))).scalars()}
    headroom: dict[tuple[str, date], Fact] = {}
    if not venture and periods:
        for fact in db.execute(select(Fact).where(Fact.borrower_id == borrower.id, Fact.key.like("cov.%.headroom_pct"),
                                                  Fact.months == 0, Fact.status.in_(USABLE_STATUSES),
                                                  Fact.period_end.in_(periods)).order_by(Fact.seq)).scalars():
            headroom[(fact.key, fact.period_end)] = fact  # by sequence: the last stored fact wins
    points = []
    for end in periods:
        mine = by_period.get(end, [])
        if venture:
            mine = [t for t in mine if t.covenant_id == RUNWAY_COVENANT]
        fact: Fact | None
        if venture:
            fact, note = _runway_for(mine, facts)
        else:
            keys = {f"cov.{t.covenant_id}.headroom_pct" for t in mine}
            found = [headroom[(k, end)] for k in keys if (k, end) in headroom]
            fact, note = (min(found, key=lambda f: f.value) if found else None), None  # chosen, not computed
        if fact is None and note is None:
            note = NOT_MEASURED
        points.append({"period_end": end.isoformat(), "fact": fact_summary(fact, labels) if fact else None, "note": note})
    return {"kind": "rml" if venture else "headroom",
            "label": "Runway (months)" if venture else "Tightest covenant headroom", "points": points}
