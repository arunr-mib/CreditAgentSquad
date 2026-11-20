"""Expected funding for a venture borrower, and the check that notices when it slips."""
import uuid
from datetime import date

from sqlalchemy import CheckConstraint, select
from sqlalchemy.orm import Session

from app.core import clock, ledger
from app.core.db import Base, CreatedMixin, IdMixin
from app.domain import work_items
from app.domain.common import Date, Decimal, Mapped, Numeric, String, fk, json_col, mapped_column
from app.domain.documents import Document

KINDS = ("equity_round", "extension", "milestone_tranche", "venture_debt")
STATUSES = ("expected", "signed", "closed", "slipped")


class FundingEvent(Base, IdMixin, CreatedMixin):
    __tablename__ = "funding_events"
    __table_args__ = (
        CheckConstraint("kind IN ('equity_round','extension','milestone_tranche','venture_debt')", name="kind"),
        CheckConstraint("status IN ('expected','signed','closed','slipped')", name="status"),
    )

    borrower_id: Mapped[uuid.UUID] = fk("borrowers.id")
    kind: Mapped[str] = mapped_column(String(24))
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    expected_close: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(12), default="expected")
    evidence_document_ids: Mapped[list[str]] = json_col(default=list)


# legal status changes: closed is final; a slipped round may be given a new timeline
TRANSITIONS: dict[str, tuple[str, ...]] = {
    "expected": ("signed", "closed", "slipped"),
    "signed": ("closed", "slipped"),
    "slipped": ("expected", "signed", "closed"),
    "closed": (),
}


def valid_evidence(db: Session, borrower_id: uuid.UUID, ids: list[str]) -> list[str]:
    """The document ids as canonical text. Each must be a document of this borrower."""
    out: list[str] = []
    for raw in ids:
        try:
            doc_id = uuid.UUID(str(raw))
        except ValueError as exc:
            raise ValueError(f"{raw!r} is not a document id") from exc
        document = db.get(Document, doc_id)
        if document is None or document.borrower_id != borrower_id:
            raise ValueError(f"document {raw} does not exist for this borrower")
        if str(doc_id) not in out:
            out.append(str(doc_id))
    return out


def update_funding_event(db: Session, event: FundingEvent, *, status: str | None = None,
                         expected_close: date | None = None, add_evidence: list[str] | None = None,
                         actor: tuple[str, str]) -> FundingEvent:
    """Change an event's status or close date, or add evidence, and record before and after.
    Raises ValueError for an illegal change; nothing is changed then."""
    if status is None and expected_close is None and not add_evidence:
        raise ValueError("nothing to change: give a status, an expected close or evidence documents")
    if status is not None:
        if status not in STATUSES:
            raise ValueError(f"status must be one of: {', '.join(STATUSES)}")
        if status not in TRANSITIONS[event.status]:
            legal = ", ".join(TRANSITIONS[event.status]) or "none, a closed event is final"
            raise ValueError(f"a {event.status} event cannot become {status}; it can become: {legal}")
    if event.status == "closed":
        raise ValueError("a closed event is final; record a new event instead")
    if event.status == "slipped" and status in ("expected", "signed"):
        # reviving a slipped round needs the new timeline, after today: an old date would be
        # marked slipped again on the next tick with no one asked
        if expected_close is None or expected_close <= clock.today(db):
            raise ValueError("a slipped round can be expected again only with a new expected close after today")
    evidence = valid_evidence(db, event.borrower_id, add_evidence or [])
    before = {"status": event.status, "expected_close": event.expected_close,
              "evidence_document_ids": list(event.evidence_document_ids)}
    if status is not None:
        event.status = status
    if expected_close is not None:
        event.expected_close = expected_close
    if evidence:
        event.evidence_document_ids = [*event.evidence_document_ids,
                                       *[i for i in evidence if i not in event.evidence_document_ids]]
    after = {"status": event.status, "expected_close": event.expected_close,
             "evidence_document_ids": list(event.evidence_document_ids)}
    ledger.record(db, actor_type=actor[0], actor_id=actor[1], action="funding_event.updated",
                  entity_type="funding_event", entity_id=event.id,
                  payload={"borrower_id": event.borrower_id, "before": before, "after": after})
    db.flush()
    return event


# the responses to a slipped round, default first; no email is sent (drafting is Phase 4)
SLIPPED_DECISIONS = ("ask_for_new_timeline", "note_and_watch", "reserve_rights", "escalate")


def check_funding_events(db: Session, as_of: date, *, actor: tuple[str, str] = ("system", "funding")) -> list[FundingEvent]:
    """Mark every expected or signed event whose close date has passed as slipped, record it, and
    ask a person about it. An event is only ever marked once, so the item is raised once."""
    events = db.execute(select(FundingEvent).where(
        FundingEvent.status.in_(("expected", "signed")), FundingEvent.expected_close < as_of)
        .order_by(FundingEvent.expected_close, FundingEvent.id)).scalars().all()
    for event in events:
        previous = event.status
        event.status = "slipped"
        ledger.record(db, actor_type=actor[0], actor_id=actor[1], action="funding_event.slipped",
                      entity_type="funding_event", entity_id=event.id,
                      payload={"borrower_id": event.borrower_id, "kind": event.kind, "amount": event.amount,
                               "expected_close": event.expected_close, "was": previous, "as_of": as_of})
        work_items.raise_item(
            db, borrower_id=event.borrower_id, item_type="funding_slipped", severity="high",
            title=f"Expected {event.kind.replace('_', ' ')} of {event.amount:,.2f} has slipped",
            question=f"The {event.kind.replace('_', ' ')} expected to close on {event.expected_close.isoformat()} "
                     "has not closed. What should we do: ask the client for a new timeline (Squad drafts the "
                     "email for you to send), note it and keep watching, reserve the bank's rights, or "
                     "escalate to the credit officer?",
            allowed_decisions=list(SLIPPED_DECISIONS), blocks_stage=False,
            evidence={"funding_event_id": str(event.id), "expected_close": event.expected_close.isoformat()},
            dedupe_key=f"funding_slipped:{event.id}", actor=actor)
    db.flush()
    return list(events)
