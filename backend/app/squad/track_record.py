"""How well each task has gone for one client, counted from the record: figures an agent read, and
how many a person later corrected. No constant, no estimate."""
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ledger import LedgerEvent
from app.domain.agents import AgentRun
from app.domain.facts import USABLE_STATUSES, Fact
from app.squad.words import agent_words, task_words


def track_record(db: Session, borrower_id: uuid.UUID) -> list[dict[str, Any]]:
    """Per task: `right` = figures confirmed by a person or that passed every check, and still stand;
    `corrected` = figures a person superseded or rejected; `unreviewed` = still proposed.
    checked = right + corrected + unreviewed. A figure superseded by anything but a person is not counted."""
    rows = db.execute(select(Fact, AgentRun).join(AgentRun, AgentRun.id == Fact.agent_run_id)
                      .where(Fact.borrower_id == borrower_id, Fact.kind == "extracted")).all()
    if not rows:
        return []
    events = {}
    for e in db.execute(select(LedgerEvent).where(
            LedgerEvent.action.in_(["fact.superseded", "fact.rejected"]), LedgerEvent.actor_type == "user",
            LedgerEvent.entity_id.in_([str(f.id) for f, _ in rows]))).scalars():
        events.setdefault(e.entity_id, []).append(e)
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for fact, run in rows:
        row = out.setdefault((run.agent_name, run.task), {
            "task": run.task, "agent_name": run.agent_name, "right": 0, "corrected": 0, "unreviewed": 0,
            "last_correction_at": None, "since": fact.created_at})
        row["since"] = min(row["since"], fact.created_at)
        if fact.status in USABLE_STATUSES:
            row["right"] += 1
        elif fact.status == "proposed":
            row["unreviewed"] += 1
        elif fact.status in ("superseded", "rejected"):
            by_person = [e for e in events.get(str(fact.id), []) if e.action == f"fact.{fact.status}"]
            if by_person:
                row["corrected"] += 1
                when = max(e.ts for e in by_person)
                row["last_correction_at"] = max(row["last_correction_at"] or when, when)
    result = []
    for r in out.values():
        r["agent_label"], r["task_label"] = agent_words(r["agent_name"]), task_words(r["task"])
        r["checked"] = r["right"] + r["corrected"] + r["unreviewed"]
        r["since"] = r["since"].isoformat()
        r["last_correction_at"] = r["last_correction_at"].isoformat() if r["last_correction_at"] else None
        if r["checked"]:
            result.append(r)
    return result
