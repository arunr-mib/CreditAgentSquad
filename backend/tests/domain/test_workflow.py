import uuid
from datetime import date

import pytest
from app.core.roles import SecondPersonRequired
from app.domain import workflow
from app.domain.credit import Borrower
from app.domain.monitoring import STAGES, Job, WorkItem
from app.domain.org import User
from sqlalchemy import select


@pytest.fixture()
def borrower(db):
    b = Borrower(code="W-001", name="Workflow Borrower")
    db.add(b)
    db.flush()
    return b


@pytest.fixture()
def handlers(monkeypatch):
    table = {}
    monkeypatch.setattr(workflow, "STAGE_HANDLERS", table)
    return table


def user(db, role):
    u = User(email=f"{uuid.uuid4().hex}@x.example", name=role, role=role, password_hash="x")
    db.add(u)
    db.flush()
    return u


def test_cycle_runs_to_close_when_no_stage_needs_a_person(db, borrower, handlers):
    for s in STAGES:
        handlers[s] = lambda db, cycle, st: "done"
    handlers["borrowing_base"] = lambda db, cycle, st: "skipped"
    cycle = workflow.open_cycle(db, borrower_id=borrower.id, period_end=date(2026, 9, 30), months=9)
    assert workflow.open_cycle(db, borrower_id=borrower.id, period_end=date(2026, 9, 30), months=9).id == cycle.id
    workflow.advance(db, cycle)
    ran = workflow.drain(db)
    assert ran == len(STAGES) and cycle.status == "closed"
    statuses = {s.stage: s.status for s in workflow.stages(db, cycle)}
    assert statuses["borrowing_base"] == "skipped" and statuses["spreading"] == "done"


def test_stage_waits_for_a_person_and_resumes_on_decision(db, borrower, handlers):
    def spreading(db, cycle, st):
        db.add(WorkItem(borrower_id=cycle.borrower_id, cycle_id=cycle.id, stage="spreading",
                        item_type="test.blocking_item", title="Balance sheet does not foot",
                        question="Total assets differ from the stated total. Which is right?",
                        allowed_decisions=["accept_stated", "correct_line"], required_permission="confirm_spread"))
        db.flush()
        return "done"  # the handler says done, but it left a blocking item open

    for s in STAGES:
        handlers[s] = lambda db, cycle, st: "done"
    handlers["spreading"] = spreading
    cycle = workflow.open_cycle(db, borrower_id=borrower.id, period_end=date(2026, 9, 30), months=9)
    workflow.advance(db, cycle)
    workflow.drain(db)
    assert cycle.stage == "spreading" and cycle.status == "open"
    item = db.execute(select(WorkItem)).scalar_one()

    officer, analyst = user(db, "credit_officer"), user(db, "analyst")
    with pytest.raises(PermissionError):
        workflow.decide_work_item(db, item, user_id=officer.id, user_role=officer.role, decision="accept_stated")
    with pytest.raises(ValueError):
        workflow.decide_work_item(db, item, user_id=analyst.id, user_role=analyst.role, decision="ignore")
    workflow.decide_work_item(db, item, user_id=analyst.id, user_role=analyst.role, decision="correct_line",
                              reason="Inventory line was missed.")
    workflow.drain(db)
    assert cycle.status == "closed" and item.status == "decided"
    with pytest.raises(ValueError):
        workflow.decide_work_item(db, item, user_id=analyst.id, user_role=analyst.role, decision="correct_line")


def test_second_person_rule_is_enforced_on_decisions(db, borrower):
    admin_a, admin_b = user(db, "credit_admin"), user(db, "credit_admin")
    item = WorkItem(borrower_id=borrower.id, item_type="test.second_person", title="Approve commentary",
                    question="Approve the commentary?", allowed_decisions=["approve", "reject"],
                    required_permission="approve_terms", requires_second_person=True,
                    prepared_by_id=str(admin_a.id))
    db.add(item)
    db.flush()
    with pytest.raises(SecondPersonRequired):
        workflow.decide_work_item(db, item, user_id=admin_a.id, user_role=admin_a.role, decision="approve")
    workflow.decide_work_item(db, item, user_id=admin_b.id, user_role=admin_b.role, decision="approve")
    assert item.status == "decided" and item.decided_by == admin_b.id


def test_a_failing_handler_fails_the_stage_and_stops_the_cycle(db, borrower, handlers):
    def boom(db, cycle, st):
        raise RuntimeError("extraction service unavailable")

    for s in STAGES:
        handlers[s] = lambda db, cycle, st: "done"
    handlers["intake"] = boom
    cycle = workflow.open_cycle(db, borrower_id=borrower.id, period_end=date(2026, 9, 30), months=9)
    workflow.advance(db, cycle)
    workflow.drain(db)
    statuses = {s.stage: s.status for s in workflow.stages(db, cycle)}
    assert statuses["intake"] == "failed" and statuses["spreading"] == "pending" and cycle.status == "open"
    assert "unavailable" in next(s for s in workflow.stages(db, cycle) if s.stage == "intake").detail["error"]


def test_unknown_job_kind_fails_after_its_attempts(db):
    workflow.enqueue(db, "does.not.exist")
    workflow.drain(db)
    job = db.execute(select(Job)).scalar_one()
    assert job.status == "failed" and job.attempts == 2 and "no handler" in job.error


def test_a_person_can_move_one_cycle_one_stage_at_a_time(db, borrower, handlers):
    from app.core.ledger import LedgerEvent

    for s in STAGES:
        handlers[s] = lambda db, cycle, st: "done"
    other = Borrower(code="W-002", name="Another Borrower")
    db.add(other)
    db.flush()
    cycle = workflow.open_cycle(db, borrower_id=borrower.id, period_end=date(2026, 9, 30), months=9)
    untouched = workflow.open_cycle(db, borrower_id=other.id, period_end=date(2026, 9, 30), months=9)
    workflow.advance(db, untouched)  # its first stage is queued and must stay queued
    analyst = user(db, "analyst")

    first = workflow.run_cycle_now(db, cycle, user_id=analyst.id)
    assert first["ran"] == [{"stage": STAGES[0], "result": "done", "error": None}]
    # the next stage is queued, not run: one press, one stage
    assert first["stage"] == STAGES[1] and first["stage_status"] == "running"
    second = workflow.run_cycle_now(db, cycle, user_id=analyst.id)
    assert [r["stage"] for r in second["ran"]] == [STAGES[1]]
    # the other cycle's job was not taken
    waiting = db.execute(select(Job).where(Job.cycle_id == untouched.id)).scalars().all()
    assert [j.status for j in waiting] == ["queued"]
    # each request is on the ledger in the person's name
    asked = db.execute(select(LedgerEvent).where(LedgerEvent.action == "cycle.run_requested")).scalars().all()
    assert len(asked) == 2 and {e.actor_id for e in asked} == {str(analyst.id)}

    for _ in range(len(STAGES)):
        if cycle.status == "closed":
            break
        workflow.run_cycle_now(db, cycle, user_id=analyst.id)
    assert cycle.status == "closed"
    with pytest.raises(ValueError, match="closed"):
        workflow.run_cycle_now(db, cycle, user_id=analyst.id)


def test_running_a_cycle_now_stops_where_a_person_is_needed(db, borrower, handlers):
    def intake(db, cycle, st):
        db.add(WorkItem(borrower_id=cycle.borrower_id, cycle_id=cycle.id, stage=STAGES[0],
                        item_type="test.blocking_item", title="A document could not be filed",
                        question="What is this document?", allowed_decisions=["classified_by_hand"],
                        required_permission="upload_document"))
        db.flush()
        return "done"

    for s in STAGES:
        handlers[s] = lambda db, cycle, st: "done"
    handlers[STAGES[0]] = intake
    cycle = workflow.open_cycle(db, borrower_id=borrower.id, period_end=date(2026, 9, 30), months=9)
    result = workflow.run_cycle_now(db, cycle, user_id=user(db, "analyst").id)
    assert result["ran"][0]["result"] == "needs_person" and result["open_blocking_items"] == 1
    again = workflow.run_cycle_now(db, cycle, user_id=user(db, "analyst").id)
    assert again["ran"] == [] and again["stage"] == STAGES[0]  # nothing runs until the person decides
