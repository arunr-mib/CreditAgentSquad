"""Raise exceptions for people: one specific question, the evidence, and the decisions allowed."""
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import ledger
from app.domain.monitoring import WorkItem

SEVERITIES = ("low", "medium", "high", "critical")


def raise_item(
    db: Session, *, borrower_id: uuid.UUID, item_type: str, title: str, question: str,
    allowed_decisions: list[str], severity: str = "medium", cycle_id: uuid.UUID | None = None,
    stage: str | None = None, facility_id: uuid.UUID | None = None, evidence: dict[str, Any] | None = None,
    recommendation: dict[str, Any] | None = None, guardrail_notes: list[Any] | None = None,
    blocks_stage: bool = True, requires_second_person: bool = False,
    required_permission: str = "decide_work_item", prepared_by_id: str | None = None,
    agent_run_id: uuid.UUID | None = None, dedupe_key: str | None = None,
    actor: tuple[str, str] = ("system", "workflow"),
) -> WorkItem:
    """Create a work item. With `dedupe_key`, an open item with the same key is returned instead."""
    if severity not in SEVERITIES:
        raise ValueError(f"unknown severity {severity!r}")
    if not question.strip().endswith("?"):
        raise ValueError("a work item asks one specific question")
    if not allowed_decisions:
        raise ValueError("a work item needs at least one allowed decision")
    evidence = dict(evidence or {})
    if dedupe_key:
        evidence["dedupe_key"] = dedupe_key
        existing = db.execute(select(WorkItem).where(
            WorkItem.borrower_id == borrower_id, WorkItem.item_type == item_type, WorkItem.status == "open",
            WorkItem.evidence["dedupe_key"].astext == dedupe_key)).scalar_one_or_none()
        if existing is not None:
            return existing
    item = WorkItem(
        borrower_id=borrower_id, facility_id=facility_id, cycle_id=cycle_id, stage=stage, item_type=item_type,
        severity=severity, title=title, question=question, allowed_decisions=allowed_decisions,
        evidence=evidence, recommendation=recommendation, guardrail_notes=guardrail_notes or [],
        blocks_stage=blocks_stage, requires_second_person=requires_second_person,
        required_permission=required_permission, prepared_by_id=prepared_by_id, agent_run_id=agent_run_id)
    db.add(item)
    db.flush()
    ledger.record(db, actor_type=actor[0], actor_id=actor[1], action="work_item.raised",
                  entity_type="work_item", entity_id=item.id,
                  payload={"type": item_type, "severity": severity, "title": title, "cycle_id": cycle_id})
    return item
