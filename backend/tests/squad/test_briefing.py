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
