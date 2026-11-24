"""Raise exceptions for people: one specific question, the evidence, and the decisions allowed."""
import uuid
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock, ledger
from app.domain.monitoring import WorkItem

SEVERITIES = ("low", "medium", "high", "critical")

# How long a person has to decide an item, in business days (Monday to Friday) from the day it is
# raised on the demonstration clock. The policy register reads this table; a person may set a
# different date when they assign the item.
DUE_BUSINESS_DAYS: dict[str, int] = {"critical": 2, "high": 5, "medium": 10, "low": 20}


def add_business_days(start: date, days: int) -> date:
    """`days` weekdays after `start`. No bank holidays are counted: the demonstration has none."""
    day = start
    while days > 0:
        day += timedelta(days=1)
        if day.weekday() < 5:
            days -= 1
    return day


def due_date_for(severity: str, raised_on: date) -> date:
    return add_business_days(raised_on, DUE_BUSINESS_DAYS[severity])

# Decisions an item type may not offer, because nothing in the product can carry them out: a
# person has no way to edit a collateral listing, and prior-period figures cannot yet be restated
# in one step. They are taken off here, whoever raises the item, so no offered decision does
# nothing. Remove an entry only together with the code that gives the decision its effect.
WITHDRAWN: dict[str, frozenset[str]] = {
    "bb.certificate_mismatch": frozenset({"listing_corrected"}),
    "spread.restatement": frozenset({"restated_update_prior"}),
}


def offered(item_type: str, decisions: list[str]) -> list[str]:
    """The decisions a person may take on an item of this type."""
    withdrawn = WITHDRAWN.get(item_type, frozenset())
    return [d for d in decisions if d not in withdrawn]


def raise_item(
    db: Session, *, borrower_id: uuid.UUID, item_type: str, title: str, question: str,
    allowed_decisions: list[str], severity: str = "medium", cycle_id: uuid.UUID | None = None,
    stage: str | None = None, facility_id: uuid.UUID | None = None, evidence: dict[str, Any] | None = None,
    recommendation: dict[str, Any] | None = None, guardrail_notes: list[Any] | None = None,
    blocks_stage: bool = True, requires_second_person: bool = False,
    required_permission: str = "decide_work_item", prepared_by_id: str | None = None,
    agent_run_id: uuid.UUID | None = None, dedupe_key: str | None = None,
    actor: tuple[str, str] = ("system", "workflow"), assigned_to: uuid.UUID | None = None,
) -> WorkItem:
    """Create a work item. With `dedupe_key`, an open item with the same key is returned instead."""
    if severity not in SEVERITIES:
        raise ValueError(f"unknown severity {severity!r}")
    if not question.strip().endswith("?"):
        raise ValueError("a work item asks one specific question")
    allowed_decisions = offered(item_type, allowed_decisions)
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
        required_permission=required_permission, prepared_by_id=prepared_by_id, agent_run_id=agent_run_id,
        assigned_to=assigned_to, due_date=due_date_for(severity, clock.today(db)))
    db.add(item)
    db.flush()
    ledger.record(db, actor_type=actor[0], actor_id=actor[1], action="work_item.raised",
                  entity_type="work_item", entity_id=item.id,
                  payload={"type": item_type, "severity": severity, "title": title, "cycle_id": cycle_id,
                           "due_date": item.due_date, **({"assigned_to": assigned_to} if assigned_to else {})})
    return item
