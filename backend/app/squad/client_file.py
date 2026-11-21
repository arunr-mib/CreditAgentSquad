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
from app.domain.metrics_service import runway_not_meaningful
from app.domain.monitoring import Cycle

NOT_MEASURED = "Not measured"
NOT_MEANINGFUL = "Not meaningful: cash-flow positive"


def _periods(db: Session, borrower: Borrower, limit: int) -> list[date]:
    ends = sorted(set(db.execute(select(Cycle.period_end).where(Cycle.borrower_id == borrower.id)).scalars()))
    return ends[-limit:]


def measure_series(db: Session, borrower: Borrower, limit: int = 6, labels: FactLabels | None = None) -> dict[str, Any]:
    labels = labels or FactLabels(db)
    periods = _periods(db, borrower, limit)
    venture = borrower.template_id == "vc-1"
    pattern = "metric.rml" if venture else "cov.%.headroom_pct"
    stored: dict[tuple[str, date], Fact] = {}
    if periods:
        for fact in db.execute(select(Fact).where(Fact.borrower_id == borrower.id, Fact.key.like(pattern),
                                                  Fact.months == 0, Fact.status.in_(USABLE_STATUSES),
                                                  Fact.period_end.in_(periods)).order_by(Fact.seq)).scalars():
            stored[(fact.key, fact.period_end)] = fact  # by sequence: the last stored fact for a key and period wins
    points = []
    for end in periods:
        candidates = [f for (_, p), f in stored.items() if p == end]
        fact = min(candidates, key=lambda f: f.value) if candidates else None  # chosen, not computed
        note = None
        if fact is None:
            is_latest = end == periods[-1]  # the full runway computation runs once, for the point people read first
            note = NOT_MEANINGFUL if venture and is_latest and runway_not_meaningful(db, borrower, end) else NOT_MEASURED
        points.append({"period_end": end.isoformat(), "fact": fact_summary(fact, labels) if fact else None, "note": note})
    return {"kind": "rml" if venture else "headroom",
            "label": "Runway (months)" if venture else "Tightest covenant headroom", "points": points}
