"""A client's thread: the record, mapped to the message types the conversation shows (spec 6).
Nothing here is stored; the thread is rebuilt on every read so it cannot drift from the ledger."""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.serialize import plain
from app.core.ledger import LedgerEvent
from app.domain.agents import AgentRun
from app.domain.credit import Borrower
from app.domain.documents import Document
from app.domain.monitoring import WorkItem
from app.domain.org import User
from app.domain.work_items import offered

RANK = {"document": 0, "held": 0, "report": 1, "case": 2, "ask": 2, "draft": 3, "qa": 4, "handoff": 5, "decision": 6}
REPORT_TEXT_KEYS = ("narrative", "summary", "explanation")  # an agent's written output, with {{fact:…}} references


def _names(db: Session) -> dict[str, str]:
    return {str(u.id): u.name for u in db.execute(select(User)).scalars()}


def _iso(value: datetime | None) -> str:
    return value.isoformat() if value else ""


def _events(db: Session, action_prefix: str, ids: list[str] | None = None, entity_type: str | None = None):
    query = select(LedgerEvent).where(LedgerEvent.action.like(action_prefix + "%")).order_by(LedgerEvent.seq)
    if ids is not None:
        query = query.where(LedgerEvent.entity_id.in_(ids or ["-"]))
    if entity_type:
        query = query.where(LedgerEvent.entity_type == entity_type)
    return db.execute(query).scalars().all()


def drafts_messages(db: Session, borrower_id: uuid.UUID, names: dict[str, str]) -> list[dict[str, Any]]:
    """Replaced in Task 4 by the ledger-derived drafts."""
    return []


def build_thread(db: Session, borrower_id: uuid.UUID) -> dict[str, Any]:
    borrower = db.get(Borrower, borrower_id)
    if borrower is None:
        raise LookupError("borrower not found")
    names = _names(db)
    bid = str(borrower_id)
    messages: list[dict[str, Any]] = []

    docs = db.execute(select(Document).where(Document.borrower_id == borrower_id)).scalars().all()
    aside = {e.entity_id: e for e in _events(db, "document.set_aside", [str(d.id) for d in docs])}
    for d in docs:
        base = {"id": f"doc:{d.id}", "ts": _iso(d.created_at), "document_id": str(d.id), "title": d.title}
        if d.status == "rejected":
            event = aside.get(str(d.id))
            messages.append({**base, "type": "held", "reason": (event.payload or {}).get("reason", "") if event else ""})
        else:
            messages.append({**base, "type": "document", "doc_type": d.doc_type, "pages": d.page_count,
                             "period_end": plain(d.period_end)})

    items = db.execute(select(WorkItem).where(WorkItem.borrower_id == borrower_id)).scalars().all()
    item_ids = [str(i.id) for i in items]
    for i in items:
        if i.item_type == "question":
            options = (i.evidence or {}).get("options", [])
            chosen = next((o for o in options if o["id"] == i.decision), None)
            messages.append({"id": f"ask:{i.id}", "type": "ask", "ts": _iso(i.created_at), "work_item_id": str(i.id),
                             "title": i.title, "question": i.question, "options": options, "status": i.status,
                             "choice": chosen["label"] if chosen else None,
                             "chosen_by": names.get(str(i.decided_by)) if i.decided_by else None})
        else:
            messages.append({"id": f"case:{i.id}", "type": "case", "ts": _iso(i.created_at), "work_item_id": str(i.id),
                             "item_type": i.item_type, "title": i.title, "question": i.question,
                             "severity": i.severity, "status": i.status,
                             "allowed_decisions": offered(i.item_type, i.allowed_decisions)})

    for e in _events(db, "work_item.decided", item_ids):
        p = e.payload or {}
        messages.append({"id": f"decision:{e.seq}", "type": "decision", "ts": _iso(e.ts), "work_item_id": e.entity_id,
                         "decision": p.get("decision"), "reason": p.get("reason", ""),
                         "by": names.get(e.actor_id, e.actor_id), "by_id": e.actor_id})
    for e in _events(db, "work_item.assigned", item_ids):
        to = (e.payload or {}).get("assigned_to")
        messages.append({"id": f"handoff:{e.seq}", "type": "handoff", "ts": _iso(e.ts), "work_item_id": e.entity_id,
                         "assigned_to": names.get(str(to)) if to else None, "assigned_to_id": to,
                         "by": names.get(e.actor_id, e.actor_id)})

    for run in db.execute(select(AgentRun).where(AgentRun.borrower_id == borrower_id, AgentRun.status == "completed",
                                                 AgentRun.agent_name != "copilot")).scalars():
        out = run.output or {}
        text = next((out[k] for k in REPORT_TEXT_KEYS if isinstance(out.get(k), str) and out[k].strip()), None)
        if text:
            messages.append({"id": f"run:{run.id}", "type": "report", "ts": _iso(run.finished_at or run.created_at),
                             "agent_name": run.agent_name, "task": run.task, "text": text, "run_id": str(run.id)})

    for e in _events(db, "copilot.asked"):
        p = e.payload or {}
        if p.get("borrower_id") != bid:
            continue
        messages.append({"id": f"qa:{e.seq}", "type": "qa", "ts": _iso(e.ts), "question": p.get("question", ""),
                         "answer": p.get("answer_with_references", ""), "fact_ids": p.get("fact_ids", []),
                         "citations": p.get("citations", []), "status": p.get("status", "answered"),
                         "run_id": e.entity_id, "asked_by": names.get(e.actor_id, e.actor_id)})

    messages += drafts_messages(db, borrower_id, names)
    # Ledger instants are whole seconds while rows carry microseconds, so order by the second and then by
    # how a case unfolds (documents in, then the case, then who it was handed to, then the decision).
    messages.sort(key=lambda m: (datetime.fromisoformat(m["ts"]).replace(microsecond=0), RANK[m["type"]], m["id"]))
    head = db.execute(select(func.coalesce(func.max(LedgerEvent.seq), 0))).scalar_one()
    return {"borrower": {"id": bid, "code": borrower.code, "name": borrower.name, "template_id": borrower.template_id},
            "head_seq": int(head), "messages": messages}
