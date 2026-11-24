from app.domain import workflow
from app.domain.routing import route_work_item
from app.domain.work_items import raise_item
from app.squad.briefing import build_briefing
from app.squad.cases import build_approvals, build_case
from app.squad.questions import raise_question
from app.squad.threads import build_thread

from .conftest import _user, sign_in

VIEW = "Recommend reserving rights."


def _case(db, borrower, permission="decide_breach"):
    return raise_item(db, borrower_id=borrower.id, item_type="test.routed_case", title="Cash below minimum",
                      severity="high", question="How should the bank respond?",
                      allowed_decisions=["reserve_rights", "no_action"], required_permission=permission)


def test_the_case_view_says_what_each_person_may_do(db, world):
    item = _case(db, world["borrower"])
    analyst = build_case(db, item, world["analyst"])
    assert analyst["may_route"] and not analyst["may_return"]
    assert not any(d["permitted"] for d in analyst["decisions"])
    assert {d["id"]: d["needs_reason"] for d in analyst["decisions"]} == {"reserve_rights": True, "no_action": False}
    assert [p["name"] for p in analyst["route_to"]] == ["Helen Strand"]
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    officer = build_case(db, item, world["officer"])
    assert officer["may_return"] and all(d["permitted"] for d in officer["decisions"])
    assert officer["view"]["text"] == VIEW and officer["view"]["by"] == "Priya Raman"
    assert officer["needs_you"] is True
    admin = build_case(db, item, world["admin"])
    assert not (admin["may_route"] or admin["may_return"] or admin["may_attach"])
    assert not any(d["permitted"] for d in admin["decisions"])


def test_an_extra_permission_on_one_decision_is_the_engines(db, world, monkeypatch):
    monkeypatch.setitem(workflow.DECISION_PERMISSIONS, ("test.routed_case", "reserve_rights"), "decide_breach")
    item = _case(db, world["borrower"], permission="decide_work_item")
    view = {d["id"]: d["permitted"] for d in build_case(db, item, world["analyst"])["decisions"]}
    assert view == {"reserve_rights": False, "no_action": True}


def test_approvals_list_what_was_routed_to_the_officer_with_the_view(db, world):
    item = _case(db, world["borrower"])
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    rows = build_approvals(db, world["officer"])
    assert [r["work_item_id"] for r in rows] == [str(item.id)]
    assert rows[0]["view"] == VIEW and rows[0]["routed_by"] == "Priya Raman" and rows[0]["returns"] == 0
    assert build_approvals(db, world["analyst"]) == []


def test_an_unrouted_breach_waits_in_approvals_and_an_unrouted_analyst_item_does_not(db, world):
    breach = _case(db, world["borrower"])
    _case(db, world["borrower"], permission="decide_work_item")
    assert [r["work_item_id"] for r in build_approvals(db, world["officer"])] == [str(breach.id)]


def test_the_briefing_says_who_is_offered_approvals_the_browser_holds_no_list(db, world):
    item = _case(db, world["borrower"])
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    assert build_briefing(db, world["officer"])["approvals"] == {"offered": True, "waiting": 1}
    assert build_briefing(db, world["analyst"])["approvals"] == {"offered": False, "waiting": 0}
    assert build_briefing(db, _user(db, "dana.whitfield"))["approvals"]["offered"] is True  # approves commentary
    assert build_briefing(db, world["admin"])["approvals"]["offered"] is False


def test_an_ask_says_whose_it_is_for_each_viewer(db, world):
    world["borrower"].analyst_id = world["analyst"].id
    raise_question(db, borrower_id=world["borrower"].id, title="Map a line", question="ARR or MRR?",
                   options=[{"id": "arr", "label": "ARR", "evidence": "Labelled annual."},
                            {"id": "mrr", "label": "MRR", "evidence": "A monthly column."}])
    tomas = _user(db, "tomas.keller")

    def ask(who):
        return next(m for m in build_thread(db, world["borrower"].id, who)["messages"] if m["type"] == "ask")

    assert ask(world["analyst"])["needs_you"] is True
    other = ask(tomas)
    assert other["needs_you"] is False and other["state_words"] == "With Priya Raman"


def test_case_and_approvals_endpoints(db, client, world):
    item = _case(db, world["borrower"])
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    db.commit()
    sign_in(client, "helen.strand")
    assert client.get(f"/api/v1/cases/{item.id}").json()["may_return"] is True
    assert [r["work_item_id"] for r in client.get("/api/v1/me/approvals").json()] == [str(item.id)]
    assert client.get("/api/v1/me/briefing").json()["approvals"]["offered"] is True
    assert client.get("/api/v1/cases/00000000-0000-0000-0000-000000000000").status_code == 404


def test_each_decision_is_served_with_its_words_and_hint_and_the_thread_agrees(db, world):
    from app.squad.words import DECISION_WORDS, decision_words
    item = _case(db, world["borrower"])
    decisions = {d["id"]: d for d in build_case(db, item, world["analyst"])["decisions"]}
    assert decisions["reserve_rights"]["label"] == DECISION_WORDS["reserve_rights"]["label"] == "Reserve the bank’s rights"
    assert decisions["reserve_rights"]["hint"] and decisions["no_action"]["label"] == "No action"
    # an id the table lacks reads as its words, never as the raw key
    assert decision_words("some_new_decision") == "some new decision"
    # the thread's past tense and the case's label come from the one module: every labelled decision reads as words in the past tense too
    assert all("_" not in decision_words(k) for k in DECISION_WORDS)
    # "reminder email", never "chaser"; and the option says who sent it, because Squad emails nothing
    assert DECISION_WORDS["chaser_sent"] == {"label": "I sent the reminder email",
                                             "hint": "You sent it yourself, outside Squad. Squad records this and emails nothing."}
    assert decision_words("chaser_sent") == "reminder email sent"  # reads "reminder email sent by Priya Raman"
    assert not any("chaser" in (v["label"] + v["hint"]).lower() for v in DECISION_WORDS.values())


# ---- final review I5: rows say the client once ----

def test_rows_carry_the_subject_without_the_client_name_the_title_is_kept(db, world):
    from app.squad.words import subject_words

    name = world["borrower"].name
    item = raise_item(db, borrower_id=world["borrower"].id, item_type="test.routed_case",
                      title=f"{name}: runway below watch", severity="high", question="How should the bank respond?",
                      allowed_decisions=["reserve_rights", "no_action"], required_permission="decide_breach")
    assert subject_words(item.title, name) == "Runway below watch"
    assert subject_words("Cash below minimum", name) == "Cash below minimum"
    home = next(i for i in build_briefing(db, world["officer"])["items"] if i["work_item_id"] == str(item.id))
    assert home["subject"] == "Runway below watch" and home["title"] == f"{name}: runway below watch"
    (row,) = build_approvals(db, world["officer"])
    assert row["subject"] == "Runway below watch"
    case = next(m for m in build_thread(db, world["borrower"].id, world["officer"])["messages"] if m["type"] == "case")
    assert case["subject"] == "Runway below watch"
    assert item.title == f"{name}: runway below watch"  # the stored title is unchanged
