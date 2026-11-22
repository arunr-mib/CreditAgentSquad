"""One case as a person sees it: the question, the router's view, what happened to it, and what this person may do
next. Every "may" is the engine's predicate (`workflow.decision_refusal`) read for this viewer; nothing here decides
who may act. Attachments are read from the ledger, the only record of them."""
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ledger import LedgerEvent
from app.core.roles import APPROVER_PERMISSIONS, Permission, can
from app.domain import gathering, routing, workflow
from app.domain.credit import Borrower
from app.domain.documents import Document
from app.domain.monitoring import WorkItem
from app.domain.org import User
from app.domain.routing import ROUTING_ACTIONS, may_receive
from app.domain.work_items import offered
from app.squad import rules
from app.squad.words import DECISION_WORDS, decision_words

CANDIDATES = 10
SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _history(db: Session, item_ids: list[str], names: dict[str, str]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {i: [] for i in item_ids}
    if not item_ids:
        return out
    query = select(LedgerEvent).where(LedgerEvent.entity_type == "work_item", LedgerEvent.entity_id.in_(item_ids),
                                      LedgerEvent.action.in_(ROUTING_ACTIONS)).order_by(LedgerEvent.seq)
    for e in db.execute(query).scalars():
        p = e.payload or {}
        to = p.get("assigned_to") or p.get("returned_to")
        out[e.entity_id].append({
            "kind": e.action.split(".", 1)[1], "seq": e.seq, "at": e.ts.isoformat(),
            "by": "Squad" if e.actor_type != "user" else names.get(e.actor_id, e.actor_id), "by_id": e.actor_id,
            "to": names.get(str(to)) if to else None, "to_id": str(to) if to else None,
            "text": p.get("view") or p.get("reason") or p.get("note") or "", "document_id": p.get("document_id")})
    return out


def _latest_route(history: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((h for h in reversed(history) if h["kind"] == "routed"), None)


def build_case(db: Session, item: WorkItem, viewer: User) -> dict[str, Any]:
    borrower = db.get(Borrower, item.borrower_id)
    people = list(db.execute(select(User).order_by(User.name)).scalars())
    names = {str(u.id): u.name for u in people}
    history = _history(db, [str(item.id)], names)[str(item.id)]
    route = _latest_route(history)
    is_open = item.status == "open"
    acts = is_open and rules.can_act(viewer, item, borrower)
    decisions = [{"id": d, "needs_reason": workflow.needs_reason(item.item_type, d),
                  "label": DECISION_WORDS.get(d, {}).get("label") or d.replace("_", " ").capitalize(),
                  "hint": DECISION_WORDS.get(d, {}).get("hint", ""),
                  "permitted": bool(acts and workflow.decision_refusal(
                      db, item, user_id=viewer.id, user_role=viewer.role, decision=d) is None)}
                 for d in offered(item.item_type, item.allowed_decisions)]
    manages = can(viewer.role, Permission.MANAGE_ACTIONS)
    route_to = [{"id": str(u.id), "name": u.name, "title": u.title} for u in people
                if u.id != viewer.id and may_receive(db, u, item)] if is_open else []
    owns = workflow.owner_refusal(db, item, user_id=viewer.id, user_role=viewer.role) is None
    holds = bool(is_open and owns and item.assigned_to in (None, viewer.id))
    waiting_for_match = bool(holds and routing.open_match_questions(db, item))
    may_route = bool(holds and manages and route_to and not waiting_for_match)
    may_return = bool(is_open and route and item.assigned_to == viewer.id
                      and route["to_id"] == str(viewer.id) and route["by_id"] != str(viewer.id))
    may_attach = bool(holds and (item.assigned_to == viewer.id or manages))
    may_repair = bool(holds and rules.holds_permission(viewer, item))
    docs = list(db.execute(select(Document).where(Document.borrower_id == item.borrower_id)
                           .order_by(Document.created_at.desc())).scalars())
    titles = {str(d.id): d.title for d in docs}
    attached = [{"document_id": h["document_id"], "title": titles.get(str(h["document_id"]), "A document"),
                 "by": h["by"], "note": h["text"]} for h in history if h["kind"] == "evidence_attached"]
    taken = {a["document_id"] for a in attached}
    candidates = [{"document_id": str(d.id), "title": d.title, "doc_type": d.doc_type, "pages": d.page_count}
                  for d in docs if d.status != "rejected" and str(d.id) not in taken][:CANDIDATES] if may_attach else []
    return {
        "work_item_id": str(item.id),
        "borrower": {"id": str(borrower.id), "code": borrower.code, "name": borrower.name},
        "item_type": item.item_type, "title": item.title, "question": item.question, "severity": item.severity,
        "status": item.status, "due_date": item.due_date.isoformat() if item.due_date else None,
        "decision": item.decision, "decision_words": decision_words(item.decision) if item.decision else None,
        "decision_reason": item.decision_reason or "",
        "decided_by": names.get(str(item.decided_by)) if item.decided_by else None,
        "requires_second_person": bool(item.requires_second_person),
        "with": names.get(str(item.assigned_to)) if item.assigned_to else None,
        "state_words": ("Confirm which document first" if waiting_for_match
                        else rules.state_words(item, names, borrower) if is_open else ""),
        "needs_you": bool(is_open and rules.needs(viewer, item, borrower)),
        "view": {"text": route["text"], "by": route["by"], "at": route["at"]} if route else None,
        "needs": gathering.need_states(db, item) if is_open else [],
        "history": history, "attached": attached, "candidates": candidates,
        "decisions": decisions, "route_to": route_to,
        "may_route": may_route, "may_return": may_return, "may_attach": may_attach, "may_repair": may_repair,
        "route_blocked_words": "Confirm which document first" if waiting_for_match else None,
    }


def build_approvals(db: Session, user: User) -> list[dict[str, Any]]:
    """Decisions waiting for this person: open cases they may decide that were routed to them, or that need an
    approver's permission (`APPROVER_PERMISSIONS`). Routed cases (with a view) first, then severity and due date."""
    borrowers = {b.id: b for b in db.execute(select(Borrower)).scalars()}
    names = {str(u.id): u.name for u in db.execute(select(User)).scalars()}
    items = [w for w in db.execute(select(WorkItem).where(WorkItem.status == "open")).scalars()
             if w.borrower_id in borrowers and rules.yours(user, w, borrowers[w.borrower_id])]
    history = _history(db, [str(w.id) for w in items], names)
    rows = []
    for w in items:
        h = history[str(w.id)]
        route = _latest_route(h)
        routed_here = route is not None and route["to_id"] == str(user.id)
        if not (routed_here or w.required_permission in APPROVER_PERMISSIONS):
            continue
        b = borrowers[w.borrower_id]
        rows.append({"work_item_id": str(w.id), "borrower_id": str(b.id), "borrower_code": b.code,
                     "borrower_name": b.name, "title": w.title, "severity": w.severity,
                     "due_date": w.due_date.isoformat() if w.due_date else None,
                     "view": route["text"] if route else None, "routed_by": route["by"] if route else None,
                     "routed_at": route["at"] if route else None,
                     "returns": sum(1 for e in h if e["kind"] == "returned")})
    rows.sort(key=lambda r: (r["view"] is None, SEVERITY_RANK.get(r["severity"], 9), r["due_date"] or "9999-12-31"))
    return rows
