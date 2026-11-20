from datetime import date, timedelta

from app.domain import workflow
from app.domain.work_items import raise_item
from app.squad.briefing import build_briefing

from .conftest import sign_in


def _breach(db, borrower, title="Cash below minimum"):
    return raise_item(db, borrower_id=borrower.id, item_type="covenant.breach", title=title, severity="critical",
                      question="Is this a breach?", allowed_decisions=["waiver_requested", "not_a_breach"],
                      required_permission="decide_breach")


def _review(db, borrower, title="Confirm revenue"):
    return raise_item(db, borrower_id=borrower.id, item_type="funding_slipped", title=title,
                      question="Should the runway outlook be reviewed?", allowed_decisions=["reviewed", "escalate_to_committee"])


def test_an_empty_book_says_nothing_needs_you(db, world):
    b = build_briefing(db, world["analyst"])
    assert b["needs_you"] == 0 and b["items"] == [] and b["open_clients"] == []


def test_the_count_equals_the_actionable_items_listed(db, world):
    _review(db, world["borrower"])
    _review(db, world["other"], title="Second")
    b = build_briefing(db, world["analyst"])
    assert b["needs_you"] == sum(1 for i in b["items"] if i["needs_you"]) == 2
    assert {c["code"] for c in b["open_clients"]} == {"QFL", "ZZZ"}


def test_the_analyst_cannot_act_on_a_breach_the_officer_can(db, world):
    _breach(db, world["borrower"])
    analyst = build_briefing(db, world["analyst"])
    officer = build_briefing(db, world["officer"])
    assert analyst["needs_you"] == 0 and officer["needs_you"] == 1
    assert officer["items"][0]["kind"] == "breach" and officer["items"][0]["state"] == "waiting for you"


def test_ordering_is_by_consequence_breach_before_review(db, world):
    _review(db, world["borrower"])
    _breach(db, world["other"])
    kinds = [i["kind"] for i in build_briefing(db, world["officer"])["items"]]
    assert kinds.index("breach") < kinds.index("review")


def test_an_item_with_the_officer_reads_with_her_to_the_analyst_who_prepared_it(db, world):
    item = _breach(db, world["borrower"])
    item.prepared_by_id = str(world["analyst"].id)
    item.assigned_to = world["officer"].id
    db.flush()
    mine = [i for i in build_briefing(db, world["analyst"])["items"] if i["work_item_id"] == str(item.id)]
    assert mine and mine[0]["state"] == "with Helen Strand" and mine[0]["needs_you"] is False


def test_a_recent_decision_is_listed_with_who_decided_and_does_not_count(db, world):
    item = _review(db, world["borrower"])
    workflow.decide_work_item(db, item, user_id=world["analyst"].id, user_role="analyst", decision="reviewed")
    b = build_briefing(db, world["analyst"])
    assert b["needs_you"] == 0
    assert b["items"][0]["kind"] == "decided" and b["items"][0]["state"] == "reviewed by Priya Raman"


def test_a_decision_older_than_two_days_drops_off(db, world):
    item = _review(db, world["borrower"])
    workflow.decide_work_item(db, item, user_id=world["analyst"].id, user_role="analyst", decision="reviewed")
    item.decided_at = item.decided_at - timedelta(days=3)
    db.flush()
    assert build_briefing(db, world["analyst"])["items"] == []


def test_briefing_endpoint_follows_the_signed_in_user(db, client, world):
    _breach(db, world["borrower"])
    db.commit()
    sign_in(client, "helen.strand")
    assert client.get("/api/v1/me/briefing").json()["needs_you"] == 1
    sign_in(client, "priya.raman")
    assert client.get("/api/v1/me/briefing").json()["needs_you"] == 0
    assert isinstance(date.fromisoformat(client.get("/api/v1/me/briefing").json()["as_of"]), date)


def _facility(db, borrower):
    from decimal import Decimal

    from app.domain.credit import Facility
    f = Facility(borrower_id=borrower.id, code="QFL-TL", name="Term loan", facility_type="term_loan",
                 commitment=Decimal("1000000"))
    db.add(f)
    db.flush()
    return f


def test_an_overdue_report_is_listed_for_all_and_counts_only_for_deciders(db, world):
    from app.core import clock
    from app.domain.terms import ReportingObligation
    f = _facility(db, world["borrower"])
    today = clock.today(db)
    db.add(ReportingObligation(borrower_id=world["borrower"].id, facility_id=f.id, requirement_id="q",
                               document_type="quarterly_statements", period_end=today - timedelta(days=60),
                               due_date=today - timedelta(days=5), status="overdue"))
    db.flush()
    analyst = build_briefing(db, world["analyst"])
    assert [i["kind"] for i in analyst["items"]] == ["overdue_report"]
    assert analyst["items"][0]["state"] == "5 days overdue" and analyst["needs_you"] == 1
    assert build_briefing(db, world["admin"])["needs_you"] == 0
    assert len(build_briefing(db, world["admin"])["items"]) == 1


def test_one_signal_per_borrower_the_most_severe(db, world):
    from app.core import clock
    from app.domain.monitoring import Signal
    today = clock.today(db)
    for rule, sev in (("dso_increase", "low"), ("covenant_headroom_low", "high"), ("revenue_ttm_decline", "medium")):
        db.add(Signal(borrower_id=world["borrower"].id, period_end=today, rule_id=rule, rule_version="1",
                      severity=sev, status="open"))
    db.flush()
    signals = [i for i in build_briefing(db, world["analyst"])["items"] if i["kind"] == "signal"]
    assert len(signals) == 1 and signals[0]["severity"] == "high"
    assert signals[0]["title"] == "Signal: Covenant cushion below the policy floor"


def test_upcoming_funding_within_fourteen_days_is_listed_and_does_not_count(db, world):
    from decimal import Decimal

    from app.core import clock
    from app.domain.funding import FundingEvent
    today = clock.today(db)
    for days in (5, 40):
        db.add(FundingEvent(borrower_id=world["borrower"].id, kind="equity_round", amount=Decimal("1000000"),
                            expected_close=today + timedelta(days=days), status="expected"))
    db.flush()
    b = build_briefing(db, world["analyst"])
    assert [i["kind"] for i in b["items"]] == ["funding"] and b["needs_you"] == 0


def test_a_slipped_funding_item_counts_for_analyst_and_officer(db, world):
    raise_item(db, borrower_id=world["borrower"].id, item_type="funding_slipped", title="Round slipped",
               question="Ask for a new timeline?", allowed_decisions=["ask_for_new_timeline", "note_and_watch"])
    assert build_briefing(db, world["analyst"])["needs_you"] == 1
    assert build_briefing(db, world["officer"])["needs_you"] == 1


def test_overnight_keeps_recent_completed_runs_with_text_only(db, world):
    from datetime import UTC, datetime

    from app.domain.agents import AgentRun
    now = datetime.now(UTC)

    def run(name, finished, status="completed", out=None):
        db.add(AgentRun(agent_name=name, agent_version="1", model="m", task="t", borrower_id=world["borrower"].id,
                        status=status, finished_at=finished, output=out if out is not None else {"narrative": f"{name} text"}))
    run("early_warning", now - timedelta(hours=2))
    run("old_agent", now - timedelta(hours=30))
    run("copilot", now - timedelta(hours=1))
    run("failed_agent", now - timedelta(hours=1), status="failed")
    run("silent_agent", now - timedelta(hours=1), out={})
    db.flush()
    overnight = build_briefing(db, world["analyst"])["overnight"]
    assert [o["agent_name"] for o in overnight] == ["early_warning"]


def test_a_second_person_item_prepared_by_me_is_not_mine_to_decide(db, world):
    item = _breach(db, world["borrower"])
    item.requires_second_person = True
    item.prepared_by_id = str(world["officer"].id)
    db.flush()
    mine = build_briefing(db, world["officer"])
    assert mine["needs_you"] == 0 and mine["items"][0]["state"] == "with a second person"


def test_an_unknown_required_permission_does_not_break_the_briefing(db, world):
    item = _review(db, world["borrower"])
    item.required_permission = "no_such_permission"
    db.flush()
    assert build_briefing(db, world["analyst"])["needs_you"] == 0
