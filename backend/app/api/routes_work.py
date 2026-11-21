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
from app.core.roles import Permission, SecondPersonRequired, can
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
    return {**_item(item), "evidence": plain(_evidence(db, item)), "borrower_name": _names(db).get(item.borrower_id),
            "related_items": _related_items(db, item)}


# Open questions on the same borrower that can change a covenant or borrowing base result: the
# terms the test used, the figures it read, or a correction that moved an outcome.
_CHANGES_RESULT = {
    "terms.unapproved_amendment": "An amendment on file is not yet in the approved terms the test used",
    "terms.approval_needed": "The terms the test relies on are awaiting approval",
    "spread.value_unverified": "A figure the calculation may read is held",
    "spread.does_not_foot": "The statements the calculation reads do not foot",
    "spread.restatement": "A prior period was restated",
    "fact.correction_changed_outcome": "A correction changed an outcome",
    "reading.review": "A document reading awaits confirmation",
}
_RESULT_ITEMS = {"covenant.breach", "covenant.reported_mismatch", "covenant.reported_breach_unconfirmed",
                 "covenant.cannot_test", "bb.over_advance", "bb.certificate_mismatch"}


def _related_items(db: Session, item: WorkItem) -> list[dict]:
    if item.item_type not in _RESULT_ITEMS:
        return []
    query = select(WorkItem).where(WorkItem.borrower_id == item.borrower_id, WorkItem.id != item.id,
                                   WorkItem.status == "open", WorkItem.item_type.in_(tuple(_CHANGES_RESULT)))
    out = []
    for other in db.execute(query.order_by(WorkItem.created_at)).scalars():
        if item.facility_id and other.facility_id and other.facility_id != item.facility_id:
            continue
        out.append({**row(other, only=("id", "item_type", "title", "severity", "status")),
                    "relation": _CHANGES_RESULT[other.item_type]})
    return out


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
    runs = list(db.execute(query).scalars())
    borrowers = _borrowers(db)
    steps: dict[uuid.UUID, list[tuple[str, dict]]] = {r.id: [] for r in runs}
    if runs:
        for run_id, kind, detail in db.execute(select(AgentStep.run_id, AgentStep.kind, AgentStep.detail).where(
                AgentStep.run_id.in_(list(steps)))):
            steps[run_id].append((kind, detail or {}))
    return [{**row(r, exclude=("raw_output", "output", "scope")), **_run_extras(r, borrowers, steps[r.id])}
            for r in runs]


def _borrowers(db: Session) -> dict[uuid.UUID, tuple[str, str]]:
    return {b.id: (b.name, b.code) for b in db.execute(select(Borrower)).scalars()}


def _run_extras(run: AgentRun, borrowers: dict[uuid.UUID, tuple[str, str]],
                steps: list[tuple[str, dict]]) -> dict:
    """What a run's row does not carry, or carries in a form a person should not read: whom it is
    about, how long it took, its scope, its steps and its tokens. `steps` is (kind, detail) for
    each step stored for the run.

    The duration is worked out from the stored start and finish, so the workspace does no
    arithmetic on timestamps; it is null until the run has finished. The scope lists only what
    code set. `steps_count` is the number of steps stored, the ones the run's page lists;
    `tool_calls` is the stored count the step cap is measured against. Tokens are summed from
    the usage each model step stored, so `input_tokens` is every input token the model read:
    uncached, written to the prompt cache and read from it, with the last two also given apart.
    A run whose steps stored no usage falls back to its own totals, and then how many tokens
    were written to the cache is not known: null, never zero."""
    name, code = borrowers.get(run.borrower_id, (None, None))
    duration = None
    if run.finished_at is not None and run.created_at is not None:
        duration = max(0, round((run.finished_at - run.created_at).total_seconds() * 1000))
    usage = [d["usage"] for kind, d in steps if kind == "model" and isinstance(d.get("usage"), dict)]
    if usage:
        def total(key: str) -> int:
            return sum(int(u.get(key) or 0) for u in usage)

        cache_read, cache_creation = total("cache_read_input_tokens"), total("cache_creation_input_tokens")
        tokens = {"input_tokens": total("input_tokens") + cache_creation + cache_read,
                  "output_tokens": total("output_tokens"), "cache_read_tokens": cache_read,
                  "cache_creation_tokens": cache_creation}
    else:
        # the stored input total already includes tokens written to the cache, not those read from it
        tokens = {"input_tokens": (run.input_tokens or 0) + (run.cache_read_tokens or 0),
                  "output_tokens": run.output_tokens, "cache_read_tokens": run.cache_read_tokens,
                  "cache_creation_tokens": None}
    scope = {k: v for k, v in (run.scope or {}).items() if v is not None and v != [] and v != ""}
    return {"borrower_name": name, "borrower_code": code, "duration_ms": duration, "scope": scope,
            "steps_count": len(steps), "tool_calls": run.steps_count, **tokens}


@router.get("/agent-runs/{run_id}")
def get_agent_run(run_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    run = db.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(404, "Agent run not found.")
    steps = list(db.execute(select(AgentStep).where(AgentStep.run_id == run.id).order_by(AgentStep.n)).scalars())
    return {**row(run), **_run_extras(run, _borrowers(db), [(s.kind, s.detail or {}) for s in steps]),
            "steps": [row(s) for s in steps]}


@router.get("/agents")
def list_agents(db: Session = Depends(get_db), _: User = Depends(current_user)) -> list[dict]:
    """The agent inventory: every registered agent version with its model and prompt hash."""
    counts = dict(db.execute(select(AgentRun.agent_name, func.count()).group_by(AgentRun.agent_name)).all())
    specs = db.execute(select(AgentSpecRecord).order_by(AgentSpecRecord.name, AgentSpecRecord.created_at.desc())).scalars()
    return [{**row(s), "runs": counts.get(s.name, 0)} for s in specs]


@router.get("/ledger")
def list_ledger(entity_type: str | None = None, entity_id: str | None = None, action: str | None = None,
                before_seq: int | None = Query(default=None, ge=1, le=2**63 - 1),
                after_seq: int | None = Query(default=None, ge=0, le=2**63 - 1), limit: int = 100,
                db: Session = Depends(get_db),
                _: User = Depends(current_user)) -> list[dict]:
    """Newest first. With `after_seq` (the polling cursor) only events after it, oldest first."""
    query = select(LedgerEvent)
    if entity_type:
        query = query.where(LedgerEvent.entity_type == entity_type)
    if entity_id:
        query = query.where(LedgerEvent.entity_id == entity_id)
    if action:
        query = query.where(LedgerEvent.action.like(action + "%"))
    if before_seq:
        query = query.where(LedgerEvent.seq < before_seq)
    if after_seq is not None:
        query = query.where(LedgerEvent.seq > after_seq).order_by(LedgerEvent.seq.asc())
    else:
        query = query.order_by(LedgerEvent.seq.desc())
    query = query.limit(max(1, min(limit, 500)))
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
    if workflow.latest_hand_off(db, item) is not None and item.assigned_to != user.id:
        raise HTTPException(409, "This case was sent for a decision and is with someone else; use Return or Route "
                                 "in its thread instead of assigning it.")
    if body.assigned_to is not None:
        assignee = db.get(User, body.assigned_to)
        if assignee is None or not assignee.is_active:
            raise HTTPException(422, "No such person.")
        if not can(assignee.role, Permission(item.required_permission)):
            raise HTTPException(422, f"{assignee.name} cannot decide this item; it needs {item.required_permission}.")
    payload: dict = {"assigned_to": body.assigned_to, "previous_assigned_to": item.assigned_to}
    item.assigned_to = body.assigned_to
    if "due_date" in body.model_fields_set:
        # a due date is only changed when one is sent, and the old one stays on the ledger
        payload.update(due_date=body.due_date, previous_due_date=item.due_date)
        item.due_date = body.due_date
    ledger.record(db, actor_type="user", actor_id=user.id, action="work_item.assigned", entity_type="work_item",
                  entity_id=item.id, payload=payload)
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
