"""The monitoring cycle as code: stages, a job queue on Postgres, and the rule that a stage
waits while it has open work items that block it. Agents never decide what stage comes next."""
import uuid
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core import ledger
from app.domain.monitoring import STAGES, Cycle, CycleStage, Job, WorkItem

# A stage handler does the stage's work and returns "done", "needs_person" or "skipped".
StageHandler = Callable[[Session, Cycle, CycleStage], str]
STAGE_HANDLERS: dict[str, StageHandler] = {}
JOB_HANDLERS: dict[str, Callable[[Session, Job], None]] = {}
# item type -> function(db, item, user, decision, reason) that carries out a decision. If it
# raises, the decision is refused and nothing is recorded.
DECISION_HOOKS: dict[str, Callable[..., None]] = {}


def stage_handler(stage: str):
    def register(fn: StageHandler) -> StageHandler:
        STAGE_HANDLERS[stage] = fn
        return fn
    return register


def now() -> datetime:
    return datetime.now(UTC)


def open_cycle(
    db: Session, *, borrower_id: uuid.UUID, period_end: date, months: int, cycle_type: str = "quarterly",
    origin: str = "live", due_date: date | None = None, actor: tuple[str, str] = ("system", "workflow"),
) -> Cycle:
    existing = db.execute(select(Cycle).where(
        Cycle.borrower_id == borrower_id, Cycle.period_end == period_end, Cycle.cycle_type == cycle_type
    )).scalar_one_or_none()
    if existing is not None:
        return existing
    cycle = Cycle(borrower_id=borrower_id, period_end=period_end, months=months, cycle_type=cycle_type,
                  origin=origin, due_date=due_date, stage=STAGES[0])
    db.add(cycle)
    db.flush()
    for position, stage in enumerate(STAGES):
        db.add(CycleStage(cycle_id=cycle.id, stage=stage, position=position))
    ledger.record(db, actor_type=actor[0], actor_id=actor[1], action="cycle.opened", entity_type="cycle",
                  entity_id=cycle.id, payload={"borrower_id": borrower_id, "period_end": period_end,
                                               "type": cycle_type, "origin": origin})
    db.flush()
    return cycle


def stages(db: Session, cycle: Cycle) -> list[CycleStage]:
    return list(db.execute(select(CycleStage).where(CycleStage.cycle_id == cycle.id)
                           .order_by(CycleStage.position)).scalars())


def open_blocking_items(db: Session, cycle: Cycle, stage: str) -> int:
    return len(db.execute(select(WorkItem.id).where(
        WorkItem.cycle_id == cycle.id, WorkItem.stage == stage, WorkItem.status == "open",
        WorkItem.blocks_stage.is_(True))).all())


def enqueue(db: Session, kind: str, payload: dict[str, Any] | None = None, *,
            cycle_id: uuid.UUID | None = None, run_after: datetime | None = None) -> Job:
    job = Job(kind=kind, payload=payload or {}, cycle_id=cycle_id, run_after=run_after)
    db.add(job)
    db.flush()
    return job


def _set_stage(db: Session, cycle: Cycle, st: CycleStage, status: str, detail: dict[str, Any] | None = None) -> None:
    previous = st.status
    st.status = status
    if status == "running" and st.started_at is None:
        st.started_at = now()
    if status in ("done", "skipped", "failed"):
        st.finished_at = now()
    if detail:
        st.detail = {**st.detail, **detail}
    ledger.record(db, actor_type="system", actor_id="workflow", action="cycle.stage_changed",
                  entity_type="cycle", entity_id=cycle.id,
                  payload={"stage": st.stage, "from": previous, "to": status, **(detail or {})})


def advance(db: Session, cycle: Cycle) -> str:
    """Move the cycle as far as it can go right now. Returns the stage it rests on.

    - a pending stage is queued and marked running;
    - a stage waiting for a person completes once its blocking work items are all decided;
    - when every stage is done or skipped, the cycle closes.
    """
    if cycle.status == "closed":
        return cycle.stage
    for st in stages(db, cycle):
        if st.status in ("done", "skipped"):
            continue
        cycle.stage = st.stage
        if st.status == "pending":
            _set_stage(db, cycle, st, "running")
            enqueue(db, "cycle.stage", {"stage": st.stage}, cycle_id=cycle.id)
            db.flush()
            return st.stage
        if st.status == "needs_person":
            if open_blocking_items(db, cycle, st.stage) == 0:
                _set_stage(db, cycle, st, "done", {"released_by": "decisions"})
                continue
            return st.stage
        return st.stage  # running or failed: nothing to do here
    cycle.status = "closed"
    cycle.stage = "closed"
    cycle.closed_at = now()
    ledger.record(db, actor_type="system", actor_id="workflow", action="cycle.closed", entity_type="cycle",
                  entity_id=cycle.id, payload={})
    db.flush()
    return "closed"


def run_stage(db: Session, cycle: Cycle, stage: str) -> str:
    """Run one stage's handler and record the result. A handler error fails the stage, never
    the cycle silently."""
    st = next(s for s in stages(db, cycle) if s.stage == stage)
    handler = STAGE_HANDLERS.get(stage)
    if handler is None:
        _set_stage(db, cycle, st, "skipped", {"reason": "no handler"})
        return "skipped"
    try:
        with db.begin_nested():
            result = handler(db, cycle, st)
    except Exception as exc:  # noqa: BLE001
        _set_stage(db, cycle, st, "failed", {"error": f"{type(exc).__name__}: {exc}"[:500]})
        db.flush()
        return "failed"
    if result == "waiting":
        # nothing to do yet (for example the package has not arrived): the stage goes back to
        # pending and is tried again on the next tick
        st.status = "pending"
        st.detail = {**st.detail, "waiting_since": st.detail.get("waiting_since") or now().isoformat()}
        db.flush()
        return "waiting"
    if result not in ("done", "needs_person", "skipped"):
        raise ValueError(f"stage handler for {stage} returned {result!r}")
    if result == "done" and open_blocking_items(db, cycle, stage) > 0:
        result = "needs_person"  # a handler cannot wave through its own open exceptions
    _set_stage(db, cycle, st, result)
    db.flush()
    return result


def _job_cycle_stage(db: Session, job: Job) -> None:
    cycle = db.get(Cycle, job.cycle_id)
    if cycle is None:
        raise ValueError("cycle not found")
    if run_stage(db, cycle, job.payload["stage"]) != "waiting":
        advance(db, cycle)


JOB_HANDLERS["cycle.stage"] = _job_cycle_stage


def tick(db: Session) -> int:
    """Try to move every open cycle. Called on a schedule, after an upload and when the clock moves."""
    moved = 0
    for cycle in db.execute(select(Cycle).where(Cycle.status == "open")).scalars():
        queued = db.execute(select(Job.id).where(Job.cycle_id == cycle.id, Job.status.in_(("queued", "running")))).first()
        if queued is None:
            advance(db, cycle)
            moved += 1
    return moved


def claim_job(db: Session) -> Job | None:
    row = db.execute(text(
        "SELECT id FROM jobs WHERE status = 'queued' AND (run_after IS NULL OR run_after <= now()) "
        "ORDER BY created_at, id LIMIT 1 FOR UPDATE SKIP LOCKED")).first()
    if row is None:
        return None
    job = db.get(Job, row.id)
    job.status = "running"
    job.attempts += 1
    job.started_at = now()
    db.flush()
    return job


def run_next_job(db: Session) -> Job | None:
    """Claim and run one job. Returns it, or None when the queue is empty."""
    job = claim_job(db)
    if job is None:
        return None
    handler = JOB_HANDLERS.get(job.kind)
    try:
        if handler is None:
            raise ValueError(f"no handler for job kind {job.kind!r}")
        with db.begin_nested():
            handler(db, job)
        job.status = "done"
    except Exception as exc:  # noqa: BLE001
        job.error = f"{type(exc).__name__}: {exc}"[:1000]
        job.status = "queued" if job.attempts < job.max_attempts else "failed"
    job.finished_at = now()
    db.flush()
    return job


def drain(db: Session, limit: int = 1000) -> int:
    """Run jobs until the queue is empty. Returns how many ran."""
    count = 0
    while count < limit and run_next_job(db) is not None:
        count += 1
    return count


def decide_work_item(
    db: Session, item: WorkItem, *, user_id: uuid.UUID, user_role: str, decision: str, reason: str = "",
) -> WorkItem:
    """Record a person's decision on an exception, then let the cycle move on."""
    from app.core.roles import Permission, can, require_second_person

    if item.status != "open":
        raise ValueError("this item has already been decided")
    if decision not in item.allowed_decisions:
        raise ValueError(f"{decision!r} is not one of the allowed decisions: {item.allowed_decisions}")
    if not can(user_role, Permission(item.required_permission)):
        raise PermissionError(f"your role cannot decide this item ({item.required_permission})")
    if item.requires_second_person:
        require_second_person(item.prepared_by_id, user_id)
    hook = DECISION_HOOKS.get(item.item_type)
    if hook is not None:
        from app.domain.org import User

        with db.begin_nested():
            hook(db, item, db.get(User, user_id), decision, reason)
    item.status = "decided"
    item.decision = decision
    item.decision_reason = reason
    item.decided_by = user_id
    item.decided_at = now()
    ledger.record(db, actor_type="user", actor_id=user_id, action="work_item.decided",
                  entity_type="work_item", entity_id=item.id,
                  payload={"type": item.item_type, "decision": decision, "reason": reason})
    db.flush()
    if item.cycle_id is not None:
        cycle = db.get(Cycle, item.cycle_id)
        if cycle is not None:
            advance(db, cycle)
    return item
