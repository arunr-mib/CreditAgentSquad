"""The worker pass and the operator commands."""
from datetime import date

from app import cli, worker
from app.core import clock, ledger
from app.domain import workflow
from app.domain.credit import Borrower
from app.domain.monitoring import STAGES


def test_one_pass_wakes_a_waiting_cycle_and_runs_its_jobs(db, monkeypatch):
    calls = []

    def waiting_then_done(db, cycle, st):
        calls.append(st.stage)
        return "waiting" if calls.count("awaiting_package") < 2 and st.stage == "awaiting_package" else "done"

    monkeypatch.setattr(workflow, "STAGE_HANDLERS", {s: waiting_then_done for s in STAGES})
    monkeypatch.setattr(db, "commit", db.flush)
    borrower = Borrower(code="W-9", name="Worker Borrower")
    db.add(borrower)
    db.flush()
    clock.set_today(db, date(2026, 11, 17))
    cycle = workflow.open_cycle(db, borrower_id=borrower.id, period_end=date(2026, 9, 30), months=9)
    workflow.advance(db, cycle)
    first = worker.run_once(db)
    assert first["jobs_run"] == 1 and cycle.stage == "awaiting_package" and cycle.status == "open"
    second = worker.run_once(db)  # the tick wakes the waiting stage; this time the package is there
    assert second["cycles_woken"] == 1 and cycle.status == "closed"


def test_verify_ledger_command_reports_the_chain(db, capsys):
    ledger.record(db, actor_type="system", actor_id="t", action="t.one", entity_type="x", entity_id="1")
    assert cli.verify_ledger(db) == 0 and "chain intact" in capsys.readouterr().out
    assert cli.main(["nonsense"]) == 2


def test_a_tick_past_an_expected_close_raises_the_funding_item_once(db, monkeypatch):
    from decimal import Decimal

    from app.domain.funding import FundingEvent
    from app.domain.monitoring import WorkItem
    from sqlalchemy import select

    monkeypatch.setattr(db, "commit", db.flush)
    borrower = Borrower(code="W-10", name="Funding Borrower", template_id="vc-1")
    db.add(borrower)
    db.flush()
    db.add(FundingEvent(borrower_id=borrower.id, kind="equity_round", amount=Decimal("5000000"),
                        expected_close=date(2026, 11, 20)))
    db.flush()
    clock.set_today(db, date(2026, 11, 20))
    assert worker.run_once(db)["funding_slipped"] == 0  # the close date itself has not passed
    clock.set_today(db, date(2026, 11, 21))
    assert worker.run_once(db)["funding_slipped"] == 1
    assert worker.run_once(db)["funding_slipped"] == 0
    items = db.execute(select(WorkItem).where(WorkItem.item_type == "funding_slipped")).scalars().all()
    assert len(items) == 1 and items[0].borrower_id == borrower.id


def test_a_failing_funding_check_does_not_stop_the_tick(db, monkeypatch):
    from app.domain import funding

    def broken(db, today):
        db.add(Borrower(code="PARTIAL", name="Written before the failure"))
        db.flush()
        raise RuntimeError("funding check broke")

    ticked = []
    monkeypatch.setattr(funding, "check_funding_events", broken)
    monkeypatch.setattr(workflow, "tick", lambda db: ticked.append(1) or 0)
    monkeypatch.setattr(db, "commit", db.flush)
    result = worker.run_once(db)
    assert ticked == [1] and result["funding_slipped"] == 0
    from sqlalchemy import select
    assert db.execute(select(Borrower).where(Borrower.code == "PARTIAL")).first() is None  # nothing partial
