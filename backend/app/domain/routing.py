"""Routing a case to a person who may decide it, with the router's view; returning it with a reason; attaching what
was asked for. Engine rules, beside `decide_work_item`:
- who may receive a case is who may decide it (`workflow.decision_refusal`);
- who may route a case or attach to it follows the engine's ownership rule (`workflow.owner_refusal`): an analyst
  acts only on her own clients' cases or a case with her;
- a person who routes a case is refused as its decider by the engine (`workflow.routed_by`), whoever prepared it;
- a return is not a decision: the case stays open and goes back to the person who routed it;
- the ledger is the only record of routes, returns and attachments."""
import uuid
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import ledger
from app.core.ledger import LedgerEvent
from app.core.roles import Permission, can
from app.domain.documents import DOCUMENT_TYPES, Document
from app.domain.monitoring import WorkItem
from app.domain.org import User
from app.domain.workflow import ATTACHED, RETURNED, ROUTED, decision_refusal, owner_refusal

ROUTING_ACTIONS = (ROUTED, RETURNED, ATTACHED)
MAX_TEXT = 4000
MAX_NOTE = 500
MAX_NEEDS = 5
MATCH_TOPIC = "evidence_match"
# the types a document can have (what Intake files), minus "other": a need for "other" would match anything
NEEDABLE_TYPES = tuple(t for t in DOCUMENT_TYPES if t != "other")


class RouteBlocked(Exception):
    """A case cannot be sent back yet because Squad is waiting for a person to confirm something (API 409)."""


def clean_needs(needs: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """What the officer asked for, checked and numbered: each a known document type and a month end."""
    needs = list(needs or [])
    if len(needs) > MAX_NEEDS:
        raise ValueError(f"A return can ask for at most {MAX_NEEDS} documents.")
    out: list[dict[str, Any]] = []
    for need in needs:
        doc_type, period = need.get("doc_type"), need.get("period_end")
        if doc_type not in NEEDABLE_TYPES:
            raise ValueError(f"{doc_type!r} is not a document type Squad knows; choose one from the list.")
        if isinstance(period, str):
            try:
                period = date.fromisoformat(period)
            except ValueError:
                raise ValueError("A period is a date, the last day of a month.") from None
        if not isinstance(period, date) or (period + timedelta(days=1)).day != 1:
            raise ValueError("A period is a month end: the last day of a month.")
        if any(o["doc_type"] == doc_type and o["period_end"] == period.isoformat() for o in out):
            raise ValueError("The same document is asked for twice.")
        out.append({"index": len(out), "doc_type": doc_type, "period_end": period.isoformat()})
    return out


def open_match_questions(db: Session, item: WorkItem) -> list[WorkItem]:
    """Squad's open questions about which document is what this case asked for."""
    return [q for q in db.execute(select(WorkItem).where(
        WorkItem.borrower_id == item.borrower_id, WorkItem.item_type == "question", WorkItem.status == "open")).scalars()
        if (q.evidence or {}).get("topic") == MATCH_TOPIC and (q.evidence or {}).get("case_id") == str(item.id)]


def _require_open(item: WorkItem) -> None:
    if item.status != "open":
        raise ValueError("This case has already been decided.")


def may_receive(db: Session, person: User, item: WorkItem) -> bool:
    return bool(person.is_active) and decision_refusal(db, item, user_id=person.id, user_role=person.role,
                                                                    receiving=True) is None


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
    owned = owner_refusal(db, item, user_id=user.id, user_role=user.role)
    if owned is not None:
        raise owned
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
    if open_match_questions(db, item):
        raise RouteBlocked("Squad found more than one document that could be what was asked for — confirm which "
                           "before sending the case back.")
    previous = item.assigned_to
    earlier = {"previous_prepared_by_id": item.prepared_by_id,
               "previous_requires_second_person": bool(item.requires_second_person)}
    item.assigned_to = to.id
    if item.prepared_by_id is None:
        item.prepared_by_id = str(user.id)
    item.requires_second_person = True
    ledger.record(db, actor_type="user", actor_id=user.id, action=ROUTED, entity_type="work_item",
                  entity_id=item.id, payload={"borrower_id": item.borrower_id, "assigned_to": to.id,
                                              "previous_assigned_to": previous, "view": view,
                                              **earlier})
    db.flush()
    return item


def return_work_item(db: Session, item: WorkItem, *, user: User, reason: str,
                     needs: list[dict[str, Any]] | None = None) -> WorkItem:
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
    wanted = clean_needs(needs)
    item.assigned_to = router
    ledger.record(db, actor_type="user", actor_id=user.id, action=RETURNED, entity_type="work_item",
                  entity_id=item.id, payload={"borrower_id": item.borrower_id, "returned_to": router,
                                              "reason": reason, "needs": wanted})
    db.flush()
    if wanted:  # code gathers what was asked: matches attach, gaps are drafted, doubts are asked
        from app.domain import gathering

        gathering.gather_safely(db, item)  # never fails the return
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
    owned = owner_refusal(db, item, user_id=user.id, user_role=user.role)
    if owned is not None:
        raise owned
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
