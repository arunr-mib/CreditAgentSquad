"""My Portfolio: every client by the one measure it is watched by, lowest first, and the habits people taught Squad.
The measure is `client_file.measure_series`, the same function the client file reads, so the two cannot disagree.
Values are compared here, as Decimals, so the browser never orders by a parsed figure."""
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.fact_labels import FactLabels
from app.core import clock
from app.domain.agents import Lesson
from app.domain.credit import Borrower
from app.domain.monitoring import WorkItem
from app.domain.org import User
from app.squad.client_file import NOT_MEANINGFUL, measure_series

SECTIONS = (("vc-1", "Innovation clients", "Runway (months)"),
            ("ci-1", "Commercial and industrial clients", "Tightest covenant headroom"))


def _latest_value(row: dict[str, Any]) -> tuple[int, Decimal]:
    """Measured first, lowest first; then clients with nothing measured (not knowing is a risk); then cash-flow
    positive clients last (no runway because they burn nothing, the safest). The Decimal(0) on the last two only
    fills the tuple."""
    points = row["measure"]["points"]
    last = points[-1] if points else None
    if last and last["fact"]:
        return 0, Decimal(last["fact"]["value"])
    return (2, Decimal(0)) if last and last["note"] == NOT_MEANINGFUL else (1, Decimal(0))


def open_work_item_counts(db: Session) -> dict[uuid.UUID, int]:
    """Open work items per client: the one count behind the nav's "Open cases" and the Portfolio's "Open" column.
    A signal, a funding event or an overdue report is watched, not a case, and is not counted."""
    return dict(db.execute(select(WorkItem.borrower_id, func.count()).where(WorkItem.status == "open")
                           .group_by(WorkItem.borrower_id)).all())


def build_portfolio(db: Session, user: User) -> dict[str, Any]:
    names = {u.id: u.name for u in db.execute(select(User)).scalars()}
    labels = FactLabels(db)  # built once for the whole book
    open_items = open_work_item_counts(db)
    rows: dict[str, list[dict[str, Any]]] = {t: [] for t, _, _ in SECTIONS}
    for b in db.execute(select(Borrower).order_by(Borrower.name)).scalars():
        rows.setdefault(b.template_id, []).append({
            "borrower_id": str(b.id), "code": b.code, "name": b.name, "analyst": names.get(b.analyst_id),
            "mine": b.analyst_id == user.id, "open": open_items.get(b.id, 0),
            "measure": measure_series(db, b, labels=labels)})
    sections = []
    for template_id, title, label in SECTIONS:
        if rows.get(template_id):
            sections.append({"template_id": template_id, "title": title, "measure_label": label,
                             "rows": sorted(rows[template_id], key=lambda r: (*_latest_value(r), r["name"]))})
    known = {t for t, _, _ in SECTIONS}
    others = [r for t, rs in rows.items() if t not in known for r in rs]
    if others:  # a template with no section of its own is listed, never dropped
        sections.append({"template_id": "other", "title": "Other clients", "measure_label": "Measure",
                         "rows": sorted(others, key=lambda r: (*_latest_value(r), r["name"]))})
    owns = any(r["mine"] for rs in rows.values() for r in rs)
    return {"as_of": clock.today(db).isoformat(), "owns_clients": owns, "sections": sections}


def lessons_for(db: Session, borrower_id: uuid.UUID, topic: str | None = None,
                names: dict[uuid.UUID, str] | None = None) -> list[dict[str, Any]]:
    names = names if names is not None else {u.id: u.name for u in db.execute(select(User)).scalars()}
    query = select(Lesson).where(Lesson.borrower_id == borrower_id).order_by(Lesson.created_at.desc())
    if topic is not None:
        query = query.where(Lesson.topic == topic)
    return [{"id": str(x.id), "topic": x.topic, "tag": x.tag, "text": x.text, "by": names.get(x.written_by, "A person"),
             "at": x.created_at.isoformat(), "work_item_id": str(x.work_item_id) if x.work_item_id else None}
            for x in db.execute(query).scalars()]
