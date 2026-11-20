"""How well each task has gone for one client, counted from the record: figures an agent read, and
how many a person later corrected. No constant, no estimate."""
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ledger import LedgerEvent
from app.domain.agents import AgentRun
from app.domain.facts import Fact


def track_record(db: Session, borrower_id: uuid.UUID) -> list[dict[str, Any]]:
    rows = db.execute(select(Fact, AgentRun).join(AgentRun, AgentRun.id == Fact.agent_run_id)
                      .where(Fact.borrower_id == borrower_id, Fact.kind == "extracted")).all()
    if not rows:
        return []
    corrections = {e.entity_id: e for e in db.execute(
        select(LedgerEvent).where(LedgerEvent.action == "fact.superseded", LedgerEvent.actor_type == "user",
                                  LedgerEvent.entity_id.in_([str(f.id) for f, _ in rows]))).scalars()}
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for fact, run in rows:
        row = out.setdefault((run.agent_name, run.task), {"task": run.task, "agent_name": run.agent_name, "checked": 0,
                                                          "corrected": 0, "last_correction_at": None,
                                                          "since": fact.created_at.isoformat()})
        row["checked"] += 1
        row["since"] = min(row["since"], fact.created_at.isoformat())
        event = corrections.get(str(fact.id))
        if event is not None:
            row["corrected"] += 1
            when = event.ts.isoformat()
            row["last_correction_at"] = max(row["last_correction_at"] or when, when)
    return [{**r, "right": r["checked"] - r["corrected"]} for r in out.values()]
