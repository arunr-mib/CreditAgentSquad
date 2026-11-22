"""The monitoring cycle as code: stages, a job queue on Postgres, and the rule that a stage
waits while it has open work items that block it. Agents never decide what stage comes next."""
import uuid
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core import ledger
from app.domain import work_items
from app.domain.monitoring import STAGES, Cycle, CycleStage, Job, WorkItem

# A stage handler does the stage's work and returns "done", "needs_person" or "skipped".
StageHandler = Callable[[Session, Cycle, CycleStage], str]
STAGE_HANDLERS: dict[str, StageHandler] = {}
JOB_HANDLERS: dict[str, Callable[[Session, Job], None]] = {}
# item type -> function(db, item, user, decision, reason) that carries out a decision. If it
# raises, the decision is refused and nothing is recorded.
DECISION_HOOKS: dict[str, Callable[..., None]] = {}
STAGE_FAILED = "cycle.stage_failed"
# A rule about who may take one decision on one kind of item that the decision hook enforces too (for example, whoever last
# edited commentary cannot approve it). `decision_refusal` asks it so a screen is never offered what the hook would refuse.
DECISION_PRECHECKS: dict[str, Callable[..., Exception | None]] = {}


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


def set_stage(db: Session, cycle: Cycle, st: CycleStage, status: str, detail: dict[str, Any] | None = None, *,
              actor: tuple[str, str] = ("system", "workflow")) -> None:
    """The one place a stage's status changes, so every change is on the ledger with who made it."""
    previous = st.status
    if previous == status and not detail:
        return
    st.status = status
    if status == "running" and st.started_at is None:
        st.started_at = now()
    if status in ("done", "skipped", "failed"):
        st.finished_at = now()
    if status == "pending":
        st.finished_at = None
    if detail:
        st.detail = {**st.detail, **detail}
    ledger.record(db, actor_type=actor[0], actor_id=actor[1], action="cycle.stage_changed",
                  entity_type="cycle", entity_id=cycle.id,
                  payload={"stage": st.stage, "from": previous, "to": status, **(detail or {})})


def fail_stage(db: Session, cycle: Cycle, st: CycleStage, error: str) -> WorkItem:
    """A stage that stops on an error never waits in silence: the failure goes on the ledger and
    one blocking item asks a person to run the stage again or escalate it."""
    set_stage(db, cycle, st, "failed", {"error": error[:500]})
    name = st.stage.replace("_", " ")
    item = work_items.raise_item(
        db, borrower_id=cycle.borrower_id, cycle_id=cycle.id, stage=st.stage, item_type=STAGE_FAILED,
        severity="high",
        title=f"The {name} stage stopped on an error for the period ended {cycle.period_end:%B %-d, %Y}",
        question="This stage stopped on an error, so the cycle cannot continue. Run the stage again, or escalate "
                 "it to an administrator?",
        allowed_decisions=["retry", "escalate"], evidence={"stage": st.stage, "error": error[:2000]},
        dedupe_key=f"{STAGE_FAILED}:{cycle.id}:{st.stage}")
    db.flush()
    return item


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
            set_stage(db, cycle, st, "running")
            enqueue(db, "cycle.stage", {"stage": st.stage}, cycle_id=cycle.id)
            db.flush()
            return st.stage
        if st.status == "needs_person":
            if open_blocking_items(db, cycle, st.stage) == 0:
                set_stage(db, cycle, st, "done", {"released_by": "decisions"})
                continue
            return st.stage
        return st.stage  # running, or failed with an item open that asks a person to retry or escalate
    cycle.status = "closed"
    cycle.stage = "closed"
    cycle.closed_at = now()
    ledger.record(db, actor_type="system", actor_id="workflow", action="cycle.closed", entity_type="cycle",
                  entity_id=cycle.id, payload={})
    db.flush()
    return "closed"


def run_stage(db: Session, cycle: Cycle, stage: str) -> str:
    """Run one stage's handler and record the result. A handler error fails the stage and asks a
    person what to do; it never fails the cycle silently."""
    st = next(s for s in stages(db, cycle) if s.stage == stage)
    handler = STAGE_HANDLERS.get(stage)
    if handler is None:
        set_stage(db, cycle, st, "skipped", {"reason": "no handler"})
        return "skipped"
    try:
        with db.begin_nested():
            result = handler(db, cycle, st)
            if result not in ("done", "needs_person", "skipped", "waiting"):
                raise ValueError(f"stage handler for {stage} returned {result!r}")
    except Exception as exc:  # noqa: BLE001
        fail_stage(db, cycle, st, f"{type(exc).__name__}: {exc}")
        return "failed"
    if result == "waiting":
        # nothing to do yet (for example the package has not arrived): the stage goes back to
        # pending and is tried again on the next tick
        set_stage(db, cycle, st, "pending",
                  {"waiting_since": st.detail.get("waiting_since") or now().isoformat()})
        db.flush()
        return "waiting"
    if result == "done" and open_blocking_items(db, cycle, stage) > 0:
        result = "needs_person"  # a handler cannot wave through its own open exceptions
    set_stage(db, cycle, st, result)
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
    return _run_claimed(db, job)


def _run_claimed(db: Session, job: Job) -> Job:
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
        if job.status == "failed" and job.kind == "cycle.stage" and job.cycle_id is not None:
            _fail_abandoned_stage(db, job)
    job.finished_at = now()
    db.flush()
    return job


def _fail_abandoned_stage(db: Session, job: Job) -> None:
    """A stage job that gave up outside the handler had its work rolled back, which would leave
    the stage running with nothing queued. Fail the stage so a person is asked."""
    cycle = db.get(Cycle, job.cycle_id)
    if cycle is None:
        return
    for st in stages(db, cycle):
        if st.stage == job.payload.get("stage") and st.status == "running":
            fail_stage(db, cycle, st, job.error or "the stage's job failed")


def run_cycle_now(db: Session, cycle: Cycle, *, user_id: uuid.UUID, max_stages: int = 1) -> dict[str, Any]:
    """A person asks for this cycle to move now. Does what the background worker would do, for
    this cycle only and for at most `max_stages` stages, and says what happened. The request is
    on the ledger in the person's name; the stages themselves are recorded as they always are."""
    if cycle.status == "closed":
        raise ValueError("The cycle is closed.")
    ledger.record(db, actor_type="user", actor_id=user_id, action="cycle.run_requested", entity_type="cycle",
                  entity_id=cycle.id, payload={"stage": cycle.stage})
    advance(db, cycle)
    ran: list[dict[str, Any]] = []
    while len(ran) < max_stages:
        row = db.execute(text(
            "SELECT id FROM jobs WHERE status = 'queued' AND kind = 'cycle.stage' AND cycle_id = :cycle "
            "AND (run_after IS NULL OR run_after <= now()) ORDER BY created_at, id LIMIT 1 "
            "FOR UPDATE SKIP LOCKED"), {"cycle": cycle.id}).first()
        if row is None:
            break
        job = db.get(Job, row.id)
        job.status = "running"
        job.attempts += 1
        job.started_at = now()
        db.flush()
        _run_claimed(db, job)
        stage = job.payload.get("stage")
        st = next((s for s in stages(db, cycle) if s.stage == stage), None)
        ran.append({"stage": stage, "result": st.status if st else None, "error": job.error if job.status != "done" else None})
    db.flush()
    current = next((s for s in stages(db, cycle) if s.stage == cycle.stage), None)
    return {"ran": ran, "cycle_status": cycle.status, "stage": cycle.stage,
            "stage_status": current.status if current else None,
            "open_blocking_items": open_blocking_items(db, cycle, cycle.stage) if current else 0}


def drain(db: Session, limit: int = 1000) -> int:
    """Run jobs until the queue is empty. Returns how many ran."""
    count = 0
    while count < limit and run_next_job(db) is not None:
        count += 1
    return count


# Decisions that must carry a written reason: every response to a breach or an over-advance, and
# every decision that sets aside what code found. Enforced here, not only in the browser.
DECISIONS_NEEDING_REASON = frozenset({
    "waiver_requested", "reservation_of_rights", "escalate_to_committee", "not_a_breach", "paydown_required",
    "temporary_overadvance_approved", "certificate_correct", "extension_granted", "received_elsewhere",
    "rating_review_requested", "add_to_watch_list", "accept_as_reported",
    "restated_update_prior", "keep_prior", "amendment_not_applicable", "not_applicable", "return_for_rework",
    "reject", "reserve_rights", "escalate",
})
ITEM_TYPES_NEEDING_REASON = frozenset({
    "covenant.breach", "covenant.reported_mismatch", "covenant.reported_breach_unconfirmed", "bb.over_advance",
})


# Some decisions on an item need more than the item's own permission. A slipped funding round is
# decided by an analyst (ask for a timeline, note and watch), but reserving the bank's rights or
# escalating it is the same call as the equivalent breach response and needs `decide_breach`.
DECISION_PERMISSIONS: dict[tuple[str, str], str] = {
    ("funding_slipped", "reserve_rights"): "decide_breach",
    ("funding_slipped", "escalate"): "decide_breach",
}


def needs_reason(item_type: str, decision: str) -> bool:
    return decision in DECISIONS_NEEDING_REASON or item_type in ITEM_TYPES_NEEDING_REASON


ROUTED, RETURNED, ATTACHED = "work_item.routed", "work_item.returned", "work_item.evidence_attached"


def routed_by(db: Session, item: WorkItem) -> set[str]:
    """Everyone who has sent this item for a decision with their view. The ledger is the record."""
    from app.core.ledger import LedgerEvent

    return {str(a).lower() for a in db.execute(select(LedgerEvent.actor_id).where(
        LedgerEvent.entity_type == "work_item", LedgerEvent.entity_id == str(item.id),
        LedgerEvent.action == ROUTED)).scalars()}


def latest_hand_off(db: Session, item: WorkItem):
    """The latest routed-or-returned ledger event of this item (by sequence), or None if it was never routed."""
    from app.core.ledger import LedgerEvent

    return db.execute(select(LedgerEvent).where(
        LedgerEvent.entity_type == "work_item", LedgerEvent.entity_id == str(item.id),
        LedgerEvent.action.in_((ROUTED, RETURNED))).order_by(LedgerEvent.seq.desc()).limit(1)).scalar_one_or_none()


ANALYST = "analyst"


def analyst_owns_client(user_id, user_role: str, borrower) -> bool:
    """An analyst's clients are those whose analyst she is, and clients with no analyst yet. Owner question 9 records
    this as a default the owner may change (whether any analyst may cover any client)."""
    return user_role == ANALYST and borrower is not None and \
        (borrower.analyst_id is None or str(borrower.analyst_id) == str(user_id))


def owner_refusal(db: Session, item: WorkItem, *, user_id, user_role: str) -> PermissionError | None:
    """The engine's ownership rule: an analyst may act on a case (decide, route, attach) only when it is assigned or
    routed to her, or, when it is assigned to no one, when its client is hers (`analyst_owns_client`). Officers,
    portfolio managers and credit administration are not split by client. None means no refusal."""
    if user_role != ANALYST:
        return None
    from app.domain.credit import Borrower
    from app.domain.org import User

    if item.assigned_to is not None:
        if str(item.assigned_to) == str(user_id):
            return None
        holder = db.get(User, item.assigned_to)
        return PermissionError(f"This case is with {holder.name if holder else 'a colleague'}; only they can act on it.")
    borrower = db.get(Borrower, item.borrower_id) if item.borrower_id else None
    if borrower is None or analyst_owns_client(user_id, user_role, borrower):
        return None
    owner = db.get(User, borrower.analyst_id)
    return PermissionError(f"{borrower.name} is {owner.name if owner else 'another analyst'}'s client; only they, or "
                           "a person the case is sent to, can act on it.")


def decision_refusal(db: Session, item: WorkItem, *, user_id, user_role: str, decision: str | None = None,
                     reason: str | None = None, receiving: bool = False) -> Exception | None:
    """The engine's one answer to "may this person decide this item, and take this decision?". None means yes;
    otherwise the exception `decide_work_item` raises, checked in the order it always has been. Squad's read models
    call this to say what a person may do, so a screen and the engine cannot disagree. Pass `decision` to include the
    decision's own rules, and `reason` (even "") to include the reason rule. Once an item has been routed it also
    refuses a case sitting returned (it can be decided after it is routed again) and anyone but the person it is
    with (`receiving=True` skips these two: it asks whether a person could be sent the case). Last comes the ownership
    rule (`owner_refusal`, also skipped when receiving): an analyst decides only her own clients' cases or a case
    assigned or routed to her. An unknown required permission is a rule refusal (ValueError, 422), as it was before this predicate."""
    from app.core.roles import Permission, SecondPersonRequired, can, require_second_person

    if item.status != "open":
        return ValueError("this item has already been decided")
    allowed = work_items.offered(item.item_type, item.allowed_decisions)
    if decision is not None and decision not in allowed:
        return ValueError(f"{decision!r} is not one of the allowed decisions: {allowed}")
    try:
        needed = Permission(item.required_permission)
    except ValueError:
        return ValueError(f"no role can decide this item ({item.required_permission})")
    if not can(user_role, needed):
        return PermissionError(f"your role cannot decide this item ({item.required_permission})")
    extra = DECISION_PERMISSIONS.get((item.item_type, decision)) if decision is not None else None
    if extra is not None and not can(user_role, Permission(extra)):
        return PermissionError(f"your role cannot take the decision {decision!r} on this item ({extra})")
    if decision is not None and reason is not None and needs_reason(item.item_type, decision) and not reason.strip():
        return ValueError("this decision needs a reason")
    precheck = DECISION_PRECHECKS.get(item.item_type)
    if precheck is not None and decision is not None:
        refused = precheck(db, item, user_id, decision)
        if refused is not None:
            return refused
    if item.requires_second_person:
        try:
            require_second_person(item.prepared_by_id, user_id)
        except SecondPersonRequired as exc:
            return exc
    if str(user_id).lower() in {str(r).lower() for r in routed_by(db, item)}:
        return SecondPersonRequired("You sent this case for a decision with your view; a second person must decide it.")
    last = None if receiving else latest_hand_off(db, item)
    if last is not None:
        from app.domain.org import User

        holder = db.get(User, item.assigned_to) if item.assigned_to else None
        if last.action == RETURNED:  # a return stands until the case is routed again, whoever holds it
            sent_back = db.get(User, (last.payload or {}).get("returned_to"))
            return ValueError(f"This case was returned to {sent_back.name if sent_back else 'the analyst'}; it can be "
                              "decided once it is sent again.")
        if item.assigned_to is not None and str(item.assigned_to) != str(user_id):
            return ValueError(f"This case was sent to {holder.name if holder else 'someone else'}; only they can decide it.")
    if not receiving:  # a person being sent the case may be any who could decide it; once sent, it is theirs
        return owner_refusal(db, item, user_id=user_id, user_role=user_role)
    return None


def decide_work_item(
    db: Session, item: WorkItem, *, user_id: uuid.UUID, user_role: str, decision: str, reason: str = "",
) -> WorkItem:
    """Record a person's decision on an exception, then let the cycle move on."""
    refusal = decision_refusal(db, item, user_id=user_id, user_role=user_role, decision=decision, reason=reason or "")
    if refusal is not None:
        raise refusal
    reason = (reason or "").strip()
    # The decision is recorded first and its hook runs second, inside one savepoint. A hook that
    # refuses undoes the record. A hook that finds the problem still there raises a fresh item,
    # instead of being handed back the very item that is being closed.
    with db.begin_nested():
        item.status = "decided"
        item.decision = decision
        item.decision_reason = reason
        item.decided_by = user_id
        item.decided_at = now()
        ledger.record(db, actor_type="user", actor_id=user_id, action="work_item.decided",
                      entity_type="work_item", entity_id=item.id,
                      payload={"type": item.item_type, "decision": decision, "reason": reason})
        db.flush()
        hook = DECISION_HOOKS.get(item.item_type)
        if hook is not None:
            from app.domain.org import User

            hook(db, item, db.get(User, user_id), decision, reason)
        db.flush()
    if item.cycle_id is not None:
        cycle = db.get(Cycle, item.cycle_id)
        if cycle is not None:
            advance(db, cycle)
    return item


def on_stage_failed_decision(db: Session, item: WorkItem, user: Any, decision: str, reason: str) -> None:
    """`retry` puts the failed stage back in the queue. `escalate` keeps the cycle stopped and
    hands the question, with the reason, to an administrator."""
    from app.core.roles import Permission

    cycle = db.get(Cycle, item.cycle_id) if item.cycle_id else None
    st = next((s for s in stages(db, cycle) if s.stage == item.stage), None) if cycle is not None else None
    if st is None or st.status != "failed":
        raise ValueError("this stage is no longer stopped on an error")
    actor = ("user", str(user.id))
    if decision == "retry":
        set_stage(db, cycle, st, "pending", {"retried_by": str(user.id)}, actor=actor)
        return
    if not reason.strip():
        raise ValueError("escalating a failed stage needs a reason")
    work_items.raise_item(
        db, borrower_id=item.borrower_id, cycle_id=cycle.id, stage=st.stage, item_type=STAGE_FAILED,
        severity="critical", title=f"Escalated: {item.title}"[:240],
        question="This failed stage was escalated to an administrator. Has the cause been fixed, so the stage "
                 "can be run again?",
        allowed_decisions=["retry"], required_permission=Permission.MANAGE_USERS.value,  # administrators only
        evidence={**{k: v for k, v in item.evidence.items() if k != "dedupe_key"},
                  "escalated_by": str(user.id), "escalation_reason": reason, "escalated_from": str(item.id)},
        actor=actor, dedupe_key=f"{STAGE_FAILED}:{cycle.id}:{st.stage}")


DECISION_HOOKS[STAGE_FAILED] = on_stage_failed_decision
