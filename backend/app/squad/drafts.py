"""Drafts to a client. Squad writes them; only a person sends (spec 9). A draft is a short run of
ledger events, so its history cannot be rewritten and no migration is needed. "Send" records that
a person sent it; nothing is delivered (a mail connector is a later phase)."""
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import ledger
from app.core.ledger import LedgerEvent
from app.domain.monitoring import WorkItem
from app.domain.org import User


def _names(db: Session) -> dict[str, str]:
    return {str(u.id): u.name for u in db.execute(select(User)).scalars()}


def _who(names: dict[str, str], event: LedgerEvent) -> str:
    return "Squad" if event.actor_type == "agent" else names.get(event.actor_id, event.actor_id)


def _fold(events: list[LedgerEvent], names: dict[str, str]) -> dict[str, Any]:
    first = events[0]
    p = first.payload
    draft = {"draft_id": first.entity_id, "borrower_id": p["borrower_id"], "to": p["to"], "subject": p["subject"],
             "body": p["body"], "kind": p.get("kind", "message"), "work_item_id": p.get("work_item_id"),
             "status": "draft", "created_by": _who(names, first), "created_at": first.ts.isoformat(),
             "edited_by": None, "sent_by": None, "sent_at": None}
    for event in events[1:]:
        if draft["status"] == "sent":  # nothing after the send counts, whatever the ledger holds
            break
        if event.action == "draft.edited":
            draft["subject"] = event.payload.get("subject", draft["subject"])
            draft["body"] = event.payload.get("body", draft["body"])
            draft["edited_by"] = _who(names, event)
        elif event.action == "draft.sent":
            draft.update(status="sent", sent_by=_who(names, event), sent_at=event.ts.isoformat())
    return draft


def _events(db: Session, draft_id: uuid.UUID) -> list[LedgerEvent]:
    return list(db.execute(select(LedgerEvent).where(LedgerEvent.entity_type == "draft",
                                                     LedgerEvent.entity_id == str(draft_id)).order_by(LedgerEvent.seq)).scalars())


def get_draft(db: Session, draft_id: uuid.UUID) -> dict[str, Any]:
    events = _events(db, draft_id)
    if not events:
        raise LookupError("draft not found")
    return _fold(events, _names(db))


def drafts_for(db: Session, borrower_id: uuid.UUID) -> list[dict[str, Any]]:
    events = db.execute(select(LedgerEvent).where(LedgerEvent.entity_type == "draft",
                                                  LedgerEvent.payload["borrower_id"].astext == str(borrower_id))
                        .order_by(LedgerEvent.seq)).scalars()
    by_draft: dict[str, list[LedgerEvent]] = {}
    for event in events:
        by_draft.setdefault(event.entity_id, []).append(event)
    names = _names(db)
    return [_fold(group, names) for group in by_draft.values()]


def create_draft(db: Session, *, borrower_id: uuid.UUID, to: str, subject: str, body: str, kind: str = "message",
                 work_item_id: uuid.UUID | None = None, actor: tuple[str, str] = ("agent", "squad")) -> dict[str, Any]:
    if not to.strip() or not subject.strip():
        raise ValueError("a draft needs a recipient and a subject")
    if work_item_id is not None:
        item = db.get(WorkItem, work_item_id)
        if item is None or item.borrower_id != borrower_id:
            raise ValueError("that work item does not belong to this client")
    draft_id = uuid.uuid4()
    ledger.record(db, actor_type=actor[0], actor_id=actor[1], action="draft.created", entity_type="draft",
                  entity_id=draft_id, payload={"borrower_id": borrower_id, "to": to.strip(), "subject": subject.strip(),
                                               "body": body, "kind": kind, "work_item_id": work_item_id})
    db.flush()
    return get_draft(db, draft_id)


def edit_draft(db: Session, draft_id: uuid.UUID, user: User, *, subject: str | None = None,
               body: str | None = None) -> dict[str, Any]:
    ledger.lock(db)  # before the status check, so a concurrent send cannot slip in between
    current = get_draft(db, draft_id)
    if current["status"] == "sent":
        raise ValueError("this draft has been sent and cannot be changed")
    payload: dict[str, Any] = {"borrower_id": current["borrower_id"]}
    if subject is not None:
        if not subject.strip():
            raise ValueError("a draft needs a subject")
        payload["subject"] = subject.strip()
    if body is not None:
        payload["body"] = body
    ledger.record(db, actor_type="user", actor_id=user.id, action="draft.edited", entity_type="draft",
                  entity_id=draft_id, payload=payload)
    db.flush()
    return get_draft(db, draft_id)


def send_draft(db: Session, draft_id: uuid.UUID, user: User) -> dict[str, Any]:
    ledger.lock(db)
    current = get_draft(db, draft_id)
    if current["status"] == "sent":
        raise ValueError("this draft has already been sent")
    if not current["body"].strip():
        raise ValueError("an empty message cannot be sent")
    ledger.record(db, actor_type="user", actor_id=user.id, action="draft.sent", entity_type="draft", entity_id=draft_id,
                  payload={"borrower_id": current["borrower_id"], "to": current["to"], "delivery": "recorded_only"})
    db.flush()
    return get_draft(db, draft_id)
