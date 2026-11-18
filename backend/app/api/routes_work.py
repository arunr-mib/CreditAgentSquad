"""Work items and decisions, cycles, the calendar, agent runs, signals, the ledger and the clock."""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.llm import client_for, model_status
from app.api.deps import current_user, require
from app.api.serialize import plain, row
from app.core import clock, ledger
from app.core.db import get_db
from app.core.ledger import LedgerEvent
from app.core.roles import Permission, SecondPersonRequired
from app.domain import calendar, stages, workflow
from app.domain.agents import AgentRun, AgentSpecRecord, AgentStep
from app.domain.credit import Borrower
from app.domain.documents import Document
from app.domain.monitoring import Cycle, Signal, WorkItem
from app.domain.org import User
from app.domain.terms import ReportingObligation
from app.domain.terms_service import TermsRefused
from app.domain.work_items import offered

router = APIRouter(tags=["work"])
_SEVERITY = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _names(db: Session) -> dict[uuid.UUID, str]:
    return {b.id: b.name for b in db.execute(select(Borrower)).scalars()}


@router.get("/work-items")
def list_work_items(
    status: str = "open", item_type: str | None = None, borrower_id: uuid.UUID | None = None,
    db: Session = Depends(get_db), _: User = Depends(current_user),
) -> list[dict]:
    """The work queue, most severe first, then by due date and age."""
    query = select(WorkItem)
    if status != "all":
        query = query.where(WorkItem.status == status)
    if item_type:
        query = query.where(WorkItem.item_type == item_type)
    if borrower_id:
        query = query.where(WorkItem.borrower_id == borrower_id)
    names = _names(db)
    items = sorted(db.execute(query).scalars(),
                   key=lambda w: (_SEVERITY.get(w.severity, 9), w.due_date or date.max, w.created_at))
    return [{**_item(w, exclude=("evidence", "recommendation", "guardrail_notes")),
             "borrower_name": names.get(w.borrower_id)} for w in items]


def _item(item: WorkItem, exclude: tuple[str, ...] = ()) -> dict:
    """A work item as shown to a person: only the decisions that can still be taken."""
    return {**row(item, exclude=exclude), "allowed_decisions": offered(item.item_type, item.allowed_decisions)}


@router.get("/work-items/{item_id}")
def get_work_item(item_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    item = db.get(WorkItem, item_id)
    if item is None:
        raise HTTPException(404, "Work item not found.")
    return {**_item(item), "evidence": plain(_evidence(db, item)), "borrower_name": _names(db).get(item.borrower_id)}


def _evidence(db: Session, item: WorkItem) -> dict | None:
    """The item's evidence as stored. For a held spread, each held figure whose row label names
    another line also says which (`reads_as`: that line's key, and the value the printed figure
    has when filed under it). Worked out on reading; the stored evidence is not changed."""
    evidence = item.evidence
    cells = evidence.get("cells") if isinstance(evidence, dict) else None
    if item.item_type != "spread.value_unverified" or item.stage != "spreading" or not isinstance(cells, list):
        return evidence
    from app.agents import spreading  # imported here: it imports the workflow

    return {**evidence, "cells": [{**cell, "reads_as": spreading.line_the_label_names(db, cell)}
                                  if isinstance(cell, dict) else cell for cell in cells]}


class DecisionIn(BaseModel):
    decision: str
    reason: str = ""


@router.post("/work-items/{item_id}/decide")
def decide(item_id: uuid.UUID, body: DecisionIn, db: Session = Depends(get_db),
           user: User = Depends(current_user)) -> dict:
    item = db.get(WorkItem, item_id)
    if item is None:
        raise HTTPException(404, "Work item not found.")
    try:
        workflow.decide_work_item(db, item, user_id=user.id, user_role=user.role, decision=body.decision,
                                  reason=body.reason)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except SecondPersonRequired as exc:
        raise HTTPException(409, str(exc)) from exc
    except (ValueError, TermsRefused) as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return _item(item)


@router.get("/cycles")
def list_cycles(period_end: date | None = None, borrower_id: uuid.UUID | None = None,
                db: Session = Depends(get_db), _: User = Depends(current_user)) -> list[dict]:
    query = select(Cycle).order_by(Cycle.period_end.desc())
    if period_end:
        query = query.where(Cycle.period_end == period_end)
    if borrower_id:
        query = query.where(Cycle.borrower_id == borrower_id)
    names = _names(db)
    return [{**row(c), "borrower_name": names.get(c.borrower_id)} for c in db.execute(query).scalars()]


@router.get("/cycles/{cycle_id}")
def get_cycle(cycle_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    cycle = db.get(Cycle, cycle_id)
    if cycle is None:
        raise HTTPException(404, "Cycle not found.")
    open_by_stage = dict(db.execute(select(WorkItem.stage, func.count()).where(
        WorkItem.cycle_id == cycle.id, WorkItem.status == "open").group_by(WorkItem.stage)).all())
    return {**row(cycle), "borrower_name": _names(db).get(cycle.borrower_id),
            "stages": [{**row(s), "open_work_items": open_by_stage.get(s.stage, 0)} for s in workflow.stages(db, cycle)]}


@router.post("/cycles/{cycle_id}/run")
def run_cycle(cycle_id: uuid.UUID, db: Session = Depends(get_db),
              user: User = Depends(require(Permission.RUN_AGENTS))) -> dict:
    """Run the cycle's next stage now, in this request. For a deployment with no background
    worker, and for a person who wants to watch one stage at a time."""
    cycle = db.get(Cycle, cycle_id)
    if cycle is None:
        raise HTTPException(404, "Cycle not found.")
    if cycle.status == "closed":
        raise HTTPException(409, "The cycle is closed.")
    status = model_status()
    if stages.LLM_FACTORY is client_for and not status["connected"]:
        # every stage may call an agent; without a model the stage would fail and raise an item
        raise HTTPException(409, f"Nothing was run. {status['reason']} The stages call agents, and an agent "
                                 "needs a model to answer.")
    result = workflow.run_cycle_now(db, cycle, user_id=user.id)
    db.commit()
    return result


@router.get("/agents/status")
def agents_status(_: User = Depends(current_user)) -> dict:
    """Whether agents can run here: is a model connected, and in which mode."""
    status = model_status()
    return {"model_connected": status["connected"], "mode": status["mode"], "model": status["model"],
            "reason": status["reason"]}


@router.get("/calendar")
def get_calendar(start: date | None = None, end: date | None = None, db: Session = Depends(get_db),
                 _: User = Depends(current_user)) -> dict:
    as_of = clock.today(db)
    query = select(ReportingObligation).order_by(ReportingObligation.due_date)
    if start:
        query = query.where(ReportingObligation.due_date >= start)
    if end:
        query = query.where(ReportingObligation.due_date <= end)
    names = _names(db)
    rows = []
    for ob in db.execute(query).scalars():
        late = None
        if ob.status == "overdue":
            late = (as_of - ob.due_date).days
        elif ob.status == "received" and ob.received_date and ob.received_date > ob.due_date:
            late = (ob.received_date - ob.due_date).days
        rows.append({**row(ob), "borrower_name": names.get(ob.borrower_id), "days_late": late})
    return {"as_of": as_of.isoformat(), "obligations": rows}


@router.get("/signals")
def list_signals(status: str = "open", borrower_id: uuid.UUID | None = None, db: Session = Depends(get_db),
                 _: User = Depends(current_user)) -> list[dict]:
    query = select(Signal)
    if status != "all":
        query = query.where(Signal.status == status)
    if borrower_id:
        query = query.where(Signal.borrower_id == borrower_id)
    names = _names(db)
    signals = sorted(db.execute(query).scalars(),
                     key=lambda s: (_SEVERITY.get(s.severity, 9), s.rank or 999, s.created_at))
    return [{**row(s), "borrower_name": names.get(s.borrower_id)} for s in signals]


@router.get("/agent-runs")
def list_agent_runs(borrower_id: uuid.UUID | None = None, cycle_id: uuid.UUID | None = None, limit: int = 100,
                    db: Session = Depends(get_db), _: User = Depends(current_user)) -> list[dict]:
    query = select(AgentRun).order_by(AgentRun.created_at.desc()).limit(max(1, min(limit, 500)))
    if borrower_id:
        query = query.where(AgentRun.borrower_id == borrower_id)
    if cycle_id:
        query = query.where(AgentRun.cycle_id == cycle_id)
    borrowers = _borrowers(db)
    return [{**row(r, exclude=("raw_output", "output", "scope")), **_run_extras(r, borrowers)}
            for r in db.execute(query).scalars()]


def _borrowers(db: Session) -> dict[uuid.UUID, tuple[str, str]]:
    return {b.id: (b.name, b.code) for b in db.execute(select(Borrower)).scalars()}


def _run_extras(run: AgentRun, borrowers: dict[uuid.UUID, tuple[str, str]]) -> dict:
    """What a run's row does not carry: whom it is about, and how long it took. The duration is
    worked out here, from the stored start and finish, so the workspace does no arithmetic on
    timestamps. It is null until the run has finished."""
    name, code = borrowers.get(run.borrower_id, (None, None))
    duration = None
    if run.finished_at is not None and run.created_at is not None:
        duration = max(0, round((run.finished_at - run.created_at).total_seconds() * 1000))
    return {"borrower_name": name, "borrower_code": code, "duration_ms": duration}


@router.get("/agent-runs/{run_id}")
def get_agent_run(run_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    run = db.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(404, "Agent run not found.")
    steps = db.execute(select(AgentStep).where(AgentStep.run_id == run.id).order_by(AgentStep.n)).scalars()
    return {**row(run), **_run_extras(run, _borrowers(db)), "steps": [row(s) for s in steps]}


@router.get("/agents")
def list_agents(db: Session = Depends(get_db), _: User = Depends(current_user)) -> list[dict]:
    """The agent inventory: every registered agent version with its model and prompt hash."""
    counts = dict(db.execute(select(AgentRun.agent_name, func.count()).group_by(AgentRun.agent_name)).all())
    specs = db.execute(select(AgentSpecRecord).order_by(AgentSpecRecord.name, AgentSpecRecord.created_at.desc())).scalars()
    return [{**row(s), "runs": counts.get(s.name, 0)} for s in specs]


@router.get("/ledger")
def list_ledger(entity_type: str | None = None, entity_id: str | None = None, action: str | None = None,
                before_seq: int | None = Query(default=None, ge=1, le=2**63 - 1), limit: int = 100,
                db: Session = Depends(get_db),
                _: User = Depends(current_user)) -> list[dict]:
    query = select(LedgerEvent).order_by(LedgerEvent.seq.desc()).limit(max(1, min(limit, 500)))
    if entity_type:
        query = query.where(LedgerEvent.entity_type == entity_type)
    if entity_id:
        query = query.where(LedgerEvent.entity_id == entity_id)
    if action:
        query = query.where(LedgerEvent.action.like(action + "%"))
    if before_seq:
        query = query.where(LedgerEvent.seq < before_seq)
    return [row(e) for e in db.execute(query).scalars()]


@router.get("/ledger/verify")
def verify_ledger(db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    """Recompute the chain. `head` is the value to keep outside the database: a chain rewritten
    by a database owner verifies against itself, and only a stored head shows the change."""
    ok, count, problem = ledger.verify_chain(db)
    head = ledger.head(db)
    return {"ok": ok, "events_checked": count, "problem": problem,
            "head": {"seq": head[0], "hash": head[1]} if head else None,
            "append_only_for_this_role": ledger.guard_status(db)["append_only_for_this_role"]}


class ClockIn(BaseModel):
    today: date


@router.get("/clock")
def get_clock(db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    """The working date, and how fresh the book is against it: the newest document received on or
    before that date, and the days between the two."""
    today = clock.today(db)
    latest = db.execute(select(func.max(Document.received_date)).where(Document.received_date <= today)).scalar()
    return {"today": today.isoformat(),
            "latest_document_received": latest.isoformat() if latest else None,
            "days_since_latest_document": (today - latest).days if latest else None}


@router.post("/clock")
def set_clock(body: ClockIn, db: Session = Depends(get_db),
              user: User = Depends(require(Permission.ADVANCE_CLOCK))) -> dict:
    clock.set_today(db, body.today, actor=("user", str(user.id)))
    changed = calendar.refresh_statuses(db, body.today)
    db.commit()
    return {"today": body.today.isoformat(), "obligations_now_overdue": changed}


class AssignIn(BaseModel):
    assigned_to: uuid.UUID | None = None
    due_date: date | None = None


@router.post("/work-items/{item_id}/assign")
def assign_work_item(item_id: uuid.UUID, body: AssignIn, db: Session = Depends(get_db),
                     user: User = Depends(require(Permission.MANAGE_ACTIONS))) -> dict:
    """Give an open item an owner and a due date."""
    item = db.get(WorkItem, item_id)
    if item is None:
        raise HTTPException(404, "Work item not found.")
    if item.status != "open":
        raise HTTPException(422, "This item has already been decided.")
    if body.assigned_to is not None and db.get(User, body.assigned_to) is None:
        raise HTTPException(422, "No such person.")
    item.assigned_to, item.due_date = body.assigned_to, body.due_date
    ledger.record(db, actor_type="user", actor_id=user.id, action="work_item.assigned", entity_type="work_item",
                  entity_id=item.id, payload={"assigned_to": body.assigned_to, "due_date": body.due_date})
    db.commit()
    return row(item)


class AcknowledgeIn(BaseModel):
    note: str = ""


@router.post("/signals/{signal_id}/acknowledge")
def acknowledge_signal(signal_id: uuid.UUID, body: AcknowledgeIn, db: Session = Depends(get_db),
                       user: User = Depends(require(Permission.DECIDE_WORK_ITEM))) -> dict:
    from datetime import UTC, datetime

    signal = db.get(Signal, signal_id)
    if signal is None:
        raise HTTPException(404, "Signal not found.")
    if signal.status != "open":
        raise HTTPException(422, "This signal has already been acknowledged.")
    signal.status, signal.acknowledged_by, signal.acknowledged_at = "acknowledged", user.id, datetime.now(UTC)
    ledger.record(db, actor_type="user", actor_id=user.id, action="signal.acknowledged", entity_type="signal",
                  entity_id=signal.id, payload={"rule": signal.rule_id, "note": body.note})
    db.commit()
    return row(signal)
