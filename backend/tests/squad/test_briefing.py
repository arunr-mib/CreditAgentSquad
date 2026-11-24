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


def test_a_decision_reads_in_the_past_tense_and_a_question_by_the_option_chosen(db, world):
    breach = _breach(db, world["borrower"])
    workflow.decide_work_item(db, breach, user_id=world["officer"].id, user_role="credit_officer", decision="not_a_breach", reason="Cash was reclassified.")
    ask = raise_item(db, borrower_id=world["other"].id, item_type="question", title="Which?", question="ARR or MRR?",
                     allowed_decisions=["map_to_arr", "map_to_mrr"],
                     evidence={"options": [{"id": "map_to_arr", "label": "Map to ARR"}, {"id": "map_to_mrr", "label": "Map to MRR"}]})
    workflow.decide_work_item(db, ask, user_id=world["analyst"].id, user_role="analyst", decision="map_to_arr")
    states = {i["work_item_id"]: i["state"] for i in build_briefing(db, world["analyst"])["items"]}
    assert states[str(breach.id)] == "marked not a breach by Helen Strand"
    assert states[str(ask.id)] == "Map to ARR \u2014 chosen by Priya Raman"


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


def test_overdue_grammar_says_one_day(db, world):
    from app.core import clock
    from app.domain.terms import ReportingObligation
    f = _facility(db, world["borrower"])
    today = clock.today(db)
    db.add(ReportingObligation(borrower_id=world["borrower"].id, facility_id=f.id, requirement_id="q",
                               document_type="quarterly_statements", period_end=today - timedelta(days=60),
                               due_date=today - timedelta(days=1), status="overdue"))
    db.flush()
    assert build_briefing(db, world["analyst"])["items"][0]["state"] == "1 day overdue"


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


def test_one_signal_row_per_client_naming_every_signal_most_severe_first(db, world):
    from app.core import clock
    from app.domain.monitoring import Signal
    today = clock.today(db)
    for rule, sev in (("dso_increase", "low"), ("covenant_headroom_low", "high"), ("revenue_ttm_decline", "medium")):
        db.add(Signal(borrower_id=world["borrower"].id, period_end=today, rule_id=rule, rule_version="1",
                      severity=sev, status="open"))
    db.flush()
    signals = [i for i in build_briefing(db, world["analyst"])["items"] if i["kind"] == "signal"]
    assert len(signals) == 1 and signals[0]["severity"] == "high" and signals[0]["needs_you"] is False
    assert signals[0]["title"].startswith("Signals: Covenant cushion below the policy floor, ")
    assert signals[0]["title"].count(", ") == 2


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


def test_a_slipped_funding_item_counts_for_the_clients_analyst_and_on_an_unowned_client_for_the_officer(db, world):
    raise_item(db, borrower_id=world["borrower"].id, item_type="funding_slipped", title="Round slipped",
               question="Ask for a new timeline?", allowed_decisions=["ask_for_new_timeline", "note_and_watch"])
    assert build_briefing(db, world["analyst"])["needs_you"] == 1
    assert build_briefing(db, world["officer"])["needs_you"] == 0  # Priya's judgement: listed for the officer
    raise_item(db, borrower_id=_unowned(db).id, item_type="funding_slipped", title="Round slipped",
               question="Ask for a new timeline?", allowed_decisions=["ask_for_new_timeline", "note_and_watch"])
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


def _tomas(db):
    from app.domain.org import User
    from sqlalchemy import select
    return db.execute(select(User).where(User.email.like("tomas.keller@%"))).scalar_one()


def test_an_unassigned_item_counts_only_for_the_clients_analyst(db, world):
    tomas = _tomas(db)
    world["borrower"].analyst_id = world["analyst"].id
    item = _review(db, world["borrower"])
    db.flush()
    priya = build_briefing(db, world["analyst"])
    other = build_briefing(db, tomas)
    officer = build_briefing(db, world["officer"])
    assert priya["needs_you"] == 1 and priya["items"][0]["state"] == "waiting for you"
    mine = [i for i in other["items"] if i["work_item_id"] == str(item.id)]
    assert other["needs_you"] == 0 and mine and mine[0]["needs_you"] is False and mine[0]["state"] == "with Priya Raman"
    # final review I2: an analyst's judgement on her own client is listed for the officer, not counted for her
    assert officer["needs_you"] == 0 and [i["state"] for i in officer["items"]] == ["with Priya Raman"]


def _unowned(db):
    from app.domain.credit import Borrower
    b = Borrower(code="NOA", name="Nobody's Analytics, Inc.")
    db.add(b)
    db.flush()
    return b


def test_a_client_with_no_analyst_counts_for_no_analyst_and_for_the_officer(db, world):
    """Owner answer 9: a client with no analyst is no analyst's until one is named."""
    _review(db, _unowned(db))
    assert build_briefing(db, world["analyst"])["needs_you"] == 0
    assert build_briefing(db, _tomas(db))["needs_you"] == 0
    assert build_briefing(db, world["officer"])["needs_you"] == 1


def test_an_item_assigned_to_another_analyst_counts_for_no_one_but_does_not_widen_her_portfolio(db, world):
    tomas = _tomas(db)
    item = _review(db, world["borrower"])
    item.assigned_to = tomas.id  # however it came to be his: assignment does not widen it (owner answer 9)
    db.flush()
    assert build_briefing(db, tomas)["needs_you"] == 0


def test_overdue_reports_count_for_the_clients_analyst_and_signals_never_count(db, world):
    from app.core import clock
    from app.domain.monitoring import Signal
    from app.domain.terms import ReportingObligation
    tomas = _tomas(db)
    world["borrower"].analyst_id = world["analyst"].id
    f = _facility(db, world["borrower"])
    today = clock.today(db)
    db.add(ReportingObligation(borrower_id=world["borrower"].id, facility_id=f.id, requirement_id="q",
                               document_type="quarterly_statements", period_end=today - timedelta(days=60),
                               due_date=today - timedelta(days=5), status="overdue"))
    db.add(Signal(borrower_id=world["borrower"].id, period_end=today, rule_id="dso_increase", rule_version="1",
                  severity="high", status="open"))
    db.flush()
    priya, other, officer = (build_briefing(db, u) for u in (world["analyst"], tomas, world["officer"]))
    assert priya["needs_you"] == 1
    assert other["needs_you"] == 0 and len(other["items"]) == 2
    assert officer["needs_you"] == 0 and len(officer["items"]) == 2


def _signal(db, borrower, rule, severity):
    from app.core import clock
    from app.domain.monitoring import Signal
    row = Signal(borrower_id=borrower.id, period_end=clock.today(db), rule_id=rule, rule_version="1",
                 severity=severity, status="open")
    db.add(row)
    db.flush()
    return row


def test_a_signal_with_an_open_work_item_is_listed_once_as_the_work_item(db, world):
    row = _signal(db, world["borrower"], "runway_below_watch", "high")
    item = raise_item(db, borrower_id=world["borrower"].id, item_type="signal.high", title="Quill: runway below watch",
                      severity="high", question="A high-severity early warning fired. Acknowledge it?", allowed_decisions=["acknowledged"],
                      evidence={"signal_id": str(row.id), "rule_id": "runway_below_watch"})
    items = build_briefing(db, world["analyst"])["items"]
    assert [i["kind"] for i in items] == ["review"] and items[0]["work_item_id"] == str(item.id)
    assert build_briefing(db, world["analyst"])["needs_you"] == 1


def test_a_signal_attached_to_a_chaser_is_not_listed_again(db, world):
    row = _signal(db, world["borrower"], "reporting_late", "high")
    raise_item(db, borrower_id=world["borrower"].id, item_type="intake.missing_document", title="Chase the pack",
               severity="medium", question="Should Squad chase the missing pack from the client?", allowed_decisions=["chased"],
               evidence={"signals": [{"signal_id": str(row.id), "rule_id": "reporting_late"}]})
    assert [i["kind"] for i in build_briefing(db, world["analyst"])["items"]] == ["review"]


def test_a_different_signal_for_the_same_client_is_still_listed(db, world):
    row = _signal(db, world["borrower"], "runway_below_watch", "high")
    _signal(db, world["borrower"], "burn_rising", "medium")
    raise_item(db, borrower_id=world["borrower"].id, item_type="signal.high", title="t", severity="high",
               question="A high-severity early warning fired. Acknowledge it?", allowed_decisions=["acknowledged"],
               evidence={"signal_id": str(row.id), "rule_id": "runway_below_watch"})
    signals = [i for i in build_briefing(db, world["analyst"])["items"] if i["kind"] == "signal"]
    assert [s["title"] for s in signals] == ["Signal: Burn rate rising"]


def test_every_signal_rule_has_a_plain_label_so_no_row_shows_a_stored_id():
    from app.calc import signals as sig
    from app.publishing.content import SIGNAL_LABELS
    assert [r.id for r in sig.RULES if r.id not in SIGNAL_LABELS] == []


def test_a_signal_row_names_its_period_or_the_span_of_its_periods(db, world):
    from app.domain.monitoring import Signal
    for rule, end in (("dso_increase", date(2026, 10, 31)), ("net_loss", date(2026, 10, 31))):
        db.add(Signal(borrower_id=world["borrower"].id, period_end=end, rule_id=rule, rule_version="1", severity="high",
                      status="open"))
    db.flush()
    [row] = [i for i in build_briefing(db, world["analyst"])["items"] if i["kind"] == "signal"]
    assert row["state"] == "watching \u00b7 October 2026"
    db.add(Signal(borrower_id=world["borrower"].id, period_end=date(2025, 12, 31), rule_id="cash_decline",
                  rule_version="1", severity="medium", status="open"))
    db.flush()
    [row] = [i for i in build_briefing(db, world["analyst"])["items"] if i["kind"] == "signal"]
    assert row["state"] == "watching \u00b7 December 2025 to October 2026"
