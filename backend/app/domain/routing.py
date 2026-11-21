"""Routing a case to a person who may decide it, with the router's view; returning it with a reason; attaching what
was asked for. Engine rules, beside `decide_work_item`:
- who may receive a case is who may decide it (`workflow.decision_refusal`);
- a person who routes a case is refused as its decider by the engine (`workflow.routed_by`), whoever prepared it;
- a return is not a decision: the case stays open and goes back to the person who routed it;
- the ledger is the only record of routes, returns and attachments."""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import ledger
from app.core.ledger import LedgerEvent
from app.core.roles import Permission, can
from app.domain.documents import Document
from app.domain.monitoring import WorkItem
from app.domain.org import User
from app.domain.workflow import ATTACHED, RETURNED, ROUTED, decision_refusal

ROUTING_ACTIONS = (ROUTED, RETURNED, ATTACHED)
MAX_TEXT = 4000
MAX_NOTE = 500


def _require_open(item: WorkItem) -> None:
    if item.status != "open":
        raise ValueError("This case has already been decided.")


def may_receive(db: Session, person: User, item: WorkItem) -> bool:
    return bool(person.is_active) and decision_refusal(db, item, user_id=person.id, user_role=person.role) is None


def latest_route(db: Session, item: WorkItem) -> LedgerEvent | None:
    return db.execute(select(LedgerEvent).where(
        LedgerEvent.entity_type == "work_item", LedgerEvent.entity_id == str(item.id), LedgerEvent.action == ROUTED)
        .order_by(LedgerEvent.seq.desc()).limit(1)).scalar_one_or_none()


def route_work_item(db: Session, item: WorkItem, *, user: User, to_user_id: uuid.UUID, view: str) -> WorkItem:
    _require_open(item)
    if not can(user.role, Permission.MANAGE_ACTIONS):
        raise PermissionError("Your role cannot route cases (manage_actions).")
    if item.assigned_to is not None and item.assigned_to != user.id:
        raise ValueError("This case is with someone else; only they can send it on.")
    view = (view or "").strip()
    if not view:
        raise ValueError("Routing a case needs your view: what you found and what you recommend.")
    if len(view) > MAX_TEXT:
        raise ValueError(f"Your view is at most {MAX_TEXT} characters.")
    to = db.get(User, to_user_id)
    if to is None or not to.is_active:
        raise ValueError("No such person.")
    if to.id == user.id:
        raise ValueError("A case is routed to someone else.")
    if not may_receive(db, to, item):
        raise ValueError(f"{to.name} cannot decide this case; it needs {item.required_permission}.")
    previous = item.assigned_to
    item.assigned_to = to.id
    if item.prepared_by_id is None:
        item.prepared_by_id = str(user.id)
    item.requires_second_person = True
    ledger.record(db, actor_type="user", actor_id=user.id, action=ROUTED, entity_type="work_item",
                  entity_id=item.id, payload={"borrower_id": item.borrower_id, "assigned_to": to.id,
                                              "previous_assigned_to": previous, "view": view})
    db.flush()
    return item


def return_work_item(db: Session, item: WorkItem, *, user: User, reason: str) -> WorkItem:
    _require_open(item)
    if item.assigned_to != user.id:
        raise PermissionError("Only the person a case is with can return it.")
    route = latest_route(db, item)
    if route is None or str((route.payload or {}).get("assigned_to")) != str(user.id):
        raise ValueError("This case was not routed to you, so there is no one to return it to.")
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("Returning a case needs a reason: what is missing, or what you want done.")
    if len(reason) > MAX_TEXT:
        raise ValueError(f"A reason is at most {MAX_TEXT} characters.")
    router = uuid.UUID(route.actor_id)
    if router == user.id:
        raise ValueError("You routed this case yourself; there is no one to return it to.")
    item.assigned_to = router
    ledger.record(db, actor_type="user", actor_id=user.id, action=RETURNED, entity_type="work_item",
                  entity_id=item.id, payload={"borrower_id": item.borrower_id, "returned_to": router,
                                              "reason": reason})
    db.flush()
    return item


def attached_ids(db: Session, item: WorkItem) -> set[str]:
    return {str(v) for v in db.execute(select(LedgerEvent.payload["document_id"].astext).where(
        LedgerEvent.entity_type == "work_item", LedgerEvent.entity_id == str(item.id),
        LedgerEvent.action == ATTACHED)).scalars()}


def attach_evidence(db: Session, item: WorkItem, *, user: User, document_id: uuid.UUID, note: str = "") -> WorkItem:
    _require_open(item)
    with_them = item.assigned_to == user.id
    unowned = item.assigned_to is None and can(user.role, Permission.MANAGE_ACTIONS)
    if not (with_them or unowned):
        raise PermissionError("Only the person a case is with can add evidence to it.")
    doc = db.get(Document, document_id)
    if doc is None or doc.borrower_id != item.borrower_id:
        raise ValueError("That document is not on this client's file.")
    if str(doc.id) in attached_ids(db, item):
        raise ValueError("That document is already attached to this case.")
    ledger.record(db, actor_type="user", actor_id=user.id, action=ATTACHED, entity_type="work_item",
                  entity_id=item.id, payload={"borrower_id": item.borrower_id, "document_id": doc.id,
                                              "note": (note or "").strip()[:MAX_NOTE]})
    db.flush()
    return item
