"""Expected funding for a venture borrower, and the check that notices when it slips."""
import uuid
from datetime import date

from sqlalchemy import CheckConstraint, select
from sqlalchemy.orm import Session

from app.core import ledger
from app.core.db import Base, CreatedMixin, IdMixin
from app.domain import work_items
from app.domain.common import Date, Decimal, Mapped, Numeric, String, fk, json_col, mapped_column

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
