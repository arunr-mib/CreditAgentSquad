"""Create and look up facts. A fact's value is never changed: a correction is a new fact that
supersedes the old one, and the only field that ever moves on an existing fact is its status."""
import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import ledger
from app.domain.documents import Document
from app.domain.documents_service import get_page
from app.domain.facts import USABLE_STATUSES, Fact
from app.guardrails.quotes import CellCheck, verify_cell

# kinds that code or a named person stands behind at creation
_INITIAL_STATUS = {"seeded": "verified", "system": "verified", "calculated": "verified", "manual": "confirmed"}


def current_fact(db: Session, borrower_id: uuid.UUID, key: str, period_end: date, months: int) -> Fact | None:
    """The latest usable fact for this line and period, or None. Proposed facts are not usable."""
    return db.execute(
        select(Fact).where(
            Fact.borrower_id == borrower_id, Fact.key == key, Fact.period_end == period_end,
            Fact.months == months, Fact.status.in_(USABLE_STATUSES),
        ).order_by(Fact.seq.desc()).limit(1)
    ).scalar_one_or_none()


def add_fact(
    db: Session, *, borrower_id: uuid.UUID, key: str, period_end: date, months: int, value: Decimal,
    kind: str, unit: str = "usd", status: str | None = None, actor: tuple[str, str] = ("system", "facts"),
    **fields: Any,
) -> Fact:
    if not isinstance(value, Decimal):
        raise TypeError("fact values are decimals")
    fact = Fact(borrower_id=borrower_id, key=key, period_end=period_end, months=months, value=value,
                unit=unit, kind=kind, status=status or _INITIAL_STATUS.get(kind, "proposed"), **fields)
    db.add(fact)
    db.flush()
    ledger.record(db, actor_type=actor[0], actor_id=actor[1], action="fact.recorded", entity_type="fact",
                  entity_id=fact.id, payload={"key": key, "period_end": period_end, "months": months,
                                              "value": value, "kind": kind, "status": fact.status})
    return fact


def store_extracted_cell(
    db: Session, *, borrower_id: uuid.UUID, key: str, period_end: date, months: int, document: Document,
    page_number: int, printed_figure: str, printed_label: str | None, column_header: str | None,
    scale: int, presentation_sign: int, agent_run_id: uuid.UUID | None, unit: str = "usd",
    actor: tuple[str, str] = ("agent", "spreading"), doubt_for: Callable[[str], str | None] | None = None,
    column_anchor: str | None = None,
) -> tuple[Fact | None, CellCheck]:
    """Verify one cell on its page and store it. The value comes from the page, never the model.

    A verified cell is stored as `verified`. A cell whose figure was read but whose row or column
    could not be confirmed is stored as `proposed` for a person. Anything else stores nothing.
    `doubt_for` is given the row's label as code read it from the page and returns a reason to
    hold the cell for a person, or None; the label the reader reported is never what is judged.
    """
    page = get_page(db, document.id, page_number)
    if page is None:
        return None, CellCheck("not_found", detail=f"page {page_number} does not exist in this document")
    if not page.has_text:
        return None, CellCheck("not_found", detail=f"page {page_number} has no text layer")
    check = verify_cell(page.words, printed_figure=printed_figure, printed_label=printed_label,
                        column_header=column_header, column_anchor=column_anchor)
    if check.value is None:
        return None, check
    doubt = doubt_for(check.row_label) if doubt_for is not None and check.ok else None
    value = Decimal(presentation_sign) * check.value * Decimal(scale)
    fact = add_fact(
        db, borrower_id=borrower_id, key=key, period_end=period_end, months=months, value=value, unit=unit,
        kind="extracted", status="verified" if check.ok and not doubt else "proposed", document_id=document.id,
        page=page_number, bbox=list(check.bbox) if check.bbox else None, quote=printed_figure,
        label_text=check.row_label or printed_label, scale_as_reported=scale, agent_run_id=agent_run_id,
        note=doubt if check.ok and doubt else None if check.ok else f"{check.status}: {check.detail}", actor=actor)
    if check.ok and doubt:
        check = CellCheck("mapping_doubt", value=check.value, unit=check.unit, bbox=check.bbox,
                          occurrences=check.occurrences, detail=doubt, row_label=check.row_label)
    return fact, check


def label_confirmed(db: Session, borrower_id: uuid.UUID, keys: Sequence[str], label: str) -> bool:
    """True when a person has already confirmed a figure read from a row with this label for one
    of these keys for this borrower: that is what makes an unfamiliar label a known one."""
    if not label.strip():
        return False
    return db.execute(select(Fact.id).where(
        Fact.borrower_id == borrower_id, Fact.key.in_(list(keys)), Fact.label_text == label,
        Fact.confirmed_by.is_not(None), Fact.status.in_(("confirmed", "superseded"))).limit(1)).first() is not None


def confirm_fact(db: Session, fact: Fact, user_id: uuid.UUID) -> Fact:
    """A person accepts a proposed or verified fact as it stands."""
    if fact.status not in ("proposed", "verified"):
        raise ValueError(f"a {fact.status} fact cannot be confirmed")
    fact.status = "confirmed"
    fact.confirmed_by = user_id
    fact.confirmed_at = datetime.now(UTC)
    ledger.record(db, actor_type="user", actor_id=user_id, action="fact.confirmed", entity_type="fact",
                  entity_id=fact.id, payload={"key": fact.key, "value": fact.value})
    db.flush()
    return fact


def correct_fact(db: Session, fact: Fact, *, value: Decimal, user_id: uuid.UUID, reason: str) -> Fact:
    """A person replaces a fact. The old fact is kept and marked superseded."""
    if not reason.strip():
        raise ValueError("a correction needs a reason")
    new = add_fact(
        db, borrower_id=fact.borrower_id, facility_id=fact.facility_id, key=fact.key,
        period_end=fact.period_end, months=fact.months, value=value, unit=fact.unit, kind="manual",
        entered_by=user_id, reason=reason, supersedes_fact_id=fact.id, document_id=fact.document_id,
        page=fact.page, actor=("user", str(user_id)))
    fact.status = "superseded"
    ledger.record(db, actor_type="user", actor_id=user_id, action="fact.superseded", entity_type="fact",
                  entity_id=fact.id, payload={"by": new.id, "old_value": fact.value, "new_value": value,
                                              "reason": reason})
    db.flush()
    return new


def reject_fact(db: Session, fact: Fact, *, user_id: uuid.UUID, reason: str) -> Fact:
    fact.status = "rejected"
    ledger.record(db, actor_type="user", actor_id=user_id, action="fact.rejected", entity_type="fact",
                  entity_id=fact.id, payload={"reason": reason})
    db.flush()
    return fact
