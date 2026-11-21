from datetime import date

import pytest
from app.core.roles import SecondPersonRequired
from app.domain import workflow
from app.domain.documents import Document
from app.domain.routing import attach_evidence, return_work_item, route_work_item
from app.domain.work_items import raise_item
from app.squad.briefing import build_briefing
from app.squad.cases import build_case
from app.squad.threads import build_thread

from .conftest import _user, sign_in

VIEW = "Unrestricted cash fell under the floor; recommend reserving rights."


def _case(db, borrower, permission="decide_breach", title="Cash below minimum"):
    # a type reserved for tests: real types gain decision hooks later
    return raise_item(db, borrower_id=borrower.id, item_type="test.routed_case", title=title, severity="high",
                      question="How should the bank respond?", allowed_decisions=["reserve_rights", "no_action"],
                      required_permission=permission)


def _doc(db, borrower, title="Signed term sheet"):
    d = Document(borrower_id=borrower.id, title=title, file_name="t.pdf", storage_path="x", sha256="b" * 64,
                 page_count=1, doc_type="term_sheet", period_end=date(2026, 10, 31), status="indexed")
    db.add(d)
    db.flush()
    return d


def test_routing_needs_a_view_and_a_person_who_may_decide(db, world):
    item = _case(db, world["borrower"])
    with pytest.raises(ValueError, match="your view"):
        route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view="   ")
    with pytest.raises(ValueError, match="cannot decide"):
        route_work_item(db, item, user=world["analyst"], to_user_id=world["admin"].id, view=VIEW)
    with pytest.raises(ValueError, match="someone else"):
        route_work_item(db, item, user=world["analyst"], to_user_id=world["analyst"].id, view=VIEW)
    assert item.assigned_to is None


def test_routing_records_the_view_and_the_engine_keeps_the_router_from_deciding(db, world):
    item = _case(db, world["borrower"], permission="decide_work_item")
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    assert item.assigned_to == world["officer"].id
    assert item.prepared_by_id == str(world["analyst"].id) and item.requires_second_person is True
    with pytest.raises(SecondPersonRequired):
        workflow.decide_work_item(db, item, user_id=world["analyst"].id, user_role="analyst", decision="no_action")


def test_the_engine_refuses_the_router_even_when_someone_else_prepared_it(db, world):
    item = _case(db, world["borrower"], permission="decide_work_item")
    item.prepared_by_id = "terms-agent-run"
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    assert item.prepared_by_id == "terms-agent-run"  # the earlier preparer is kept
    with pytest.raises(SecondPersonRequired, match="sent this case"):
        workflow.decide_work_item(db, item, user_id=world["analyst"].id, user_role="analyst", decision="no_action")
    workflow.decide_work_item(db, item, user_id=world["officer"].id, user_role="credit_officer", decision="no_action")
    assert item.status == "decided"


def test_the_predicate_keeps_the_engines_order_of_refusals(db, world):
    item = _case(db, world["borrower"], permission="decide_work_item")
    refuse = workflow.decision_refusal
    assert isinstance(refuse(db, item, user_id=world["admin"].id, user_role="admin"), PermissionError)
    assert isinstance(refuse(db, item, user_id=world["analyst"].id, user_role="analyst", decision="nope"), ValueError)
    assert isinstance(refuse(db, item, user_id=world["analyst"].id, user_role="analyst", decision="reserve_rights",
                             reason=""), ValueError)
    assert refuse(db, item, user_id=world["analyst"].id, user_role="analyst", decision="no_action", reason="") is None


def test_a_case_with_someone_else_cannot_be_routed_by_another(db, world):
    item = _case(db, world["borrower"])
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    with pytest.raises(ValueError, match="with someone else"):
        route_work_item(db, item, user=_user(db, "tomas.keller"), to_user_id=world["officer"].id, view=VIEW)


def test_a_return_goes_back_to_the_router_with_the_reason_and_needs_her(db, world):
    item = _case(db, world["borrower"])
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    with pytest.raises(PermissionError):
        return_work_item(db, item, user=world["analyst"], reason="x")
    with pytest.raises(ValueError, match="reason"):
        return_work_item(db, item, user=world["officer"], reason="  ")
    return_work_item(db, item, user=world["officer"], reason="Attach the signed term sheet first.")
    assert item.assigned_to == world["analyst"].id and item.status == "open"
    mine = [i for i in build_briefing(db, world["analyst"])["items"] if i["work_item_id"] == str(item.id)]
    assert mine and mine[0]["needs_you"] is True and mine[0]["state"] == "returned to you"
    officer = [i for i in build_briefing(db, world["officer"])["items"] if i["work_item_id"] == str(item.id)]
    assert not any(i["needs_you"] for i in officer)


def test_the_case_message_agrees_with_the_briefing_after_a_return(db, world):
    item = _case(db, world["borrower"])
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    return_work_item(db, item, user=world["officer"], reason="Attach the signed term sheet first.")

    def case(who):
        return next(m for m in build_thread(db, world["borrower"].id, who)["messages"] if m["type"] == "case")

    assert case(world["analyst"])["needs_you"] is True
    officer = case(world["officer"])
    assert officer["needs_you"] is False and officer["state_words"] == "With Priya Raman"


def test_a_plain_assignment_is_never_read_as_a_return(db, world):
    item = _case(db, world["borrower"])
    item.assigned_to = world["analyst"].id  # assigned, never routed or returned
    db.flush()
    rows = [i for i in build_briefing(db, world["analyst"])["items"] if i["work_item_id"] == str(item.id)]
    assert not any(i["needs_you"] or i["state"] == "returned to you" for i in rows)


def test_a_case_never_routed_cannot_be_returned(db, world):
    item = _case(db, world["borrower"])
    item.assigned_to = world["officer"].id
    with pytest.raises(ValueError, match="not routed to you"):
        return_work_item(db, item, user=world["officer"], reason="Why is this mine?")


def test_attach_takes_only_this_clients_documents_and_each_once(db, world):
    item = _case(db, world["borrower"])
    mine, theirs = _doc(db, world["borrower"]), _doc(db, world["other"])
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    return_work_item(db, item, user=world["officer"], reason="Attach the signed term sheet first.")
    with pytest.raises(ValueError, match="not on this client's file"):
        attach_evidence(db, item, user=world["analyst"], document_id=theirs.id)
    attach_evidence(db, item, user=world["analyst"], document_id=mine.id, note="As asked.")
    with pytest.raises(ValueError, match="already attached"):
        attach_evidence(db, item, user=world["analyst"], document_id=mine.id)
    view = build_case(db, item, world["analyst"])
    assert [(a["document_id"], a["title"], a["note"]) for a in view["attached"]] == [(str(mine.id), "Signed term sheet", "As asked.")]
    assert str(mine.id) not in {c["document_id"] for c in view["candidates"]}
    assert "attached" not in (item.evidence or {})  # the ledger is the one record of what was attached


def test_the_whole_loop_reads_in_order_in_the_thread_and_ends_with_two_people(db, world):
    item = _case(db, world["borrower"])
    doc = _doc(db, world["borrower"])
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    return_work_item(db, item, user=world["officer"], reason="Attach the signed term sheet first.")
    attach_evidence(db, item, user=world["analyst"], document_id=doc.id, note="As asked.")
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view="Term sheet attached.")
    workflow.decide_work_item(db, item, user_id=world["officer"].id, user_role="credit_officer",
                              decision="reserve_rights", reason="Rights reserved pending the close.")
    thread = build_thread(db, world["borrower"].id, world["analyst"])
    msgs = [m for m in thread["messages"] if m.get("work_item_id") == str(item.id)]
    assert [m["type"] for m in msgs] == ["case", "handoff", "returned", "attached", "handoff", "decision"]
    assert msgs[1]["view"] == VIEW and msgs[2]["reason"] == "Attach the signed term sheet first."
    assert msgs[3]["title"] == "Signed term sheet" and msgs[5]["by"] == "Helen Strand"


def test_route_api_refuses_an_administrator(db, client, world):
    item = _case(db, world["borrower"])
    db.commit()
    sign_in(client, "admin")
    r = client.post(f"/api/v1/work-items/{item.id}/route", json={"to": str(world["officer"].id), "view": VIEW})
    assert r.status_code == 403


def test_route_api_refuses_an_empty_view_in_words(db, client, world):
    item = _case(db, world["borrower"])
    db.commit()
    sign_in(client, "priya.raman")
    r = client.post(f"/api/v1/work-items/{item.id}/route", json={"to": str(world["officer"].id), "view": " "})
    assert r.status_code == 422 and "your view" in r.json()["detail"]


def test_the_router_is_refused_through_the_decide_api_with_409(db, client, world):
    item = _case(db, world["borrower"], permission="decide_work_item")
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    db.commit()
    sign_in(client, "priya.raman")
    r = client.post(f"/api/v1/work-items/{item.id}/decide", json={"decision": "no_action"})
    assert r.status_code == 409


def test_the_router_with_an_earlier_preparer_is_refused_through_the_api_with_409(db, client, world):
    item = _case(db, world["borrower"], permission="decide_work_item")
    item.prepared_by_id = "terms-agent-run"
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    db.commit()
    sign_in(client, "priya.raman")
    r = client.post(f"/api/v1/work-items/{item.id}/decide", json={"decision": "no_action"})
    assert r.status_code == 409 and "sent this case" in r.json()["detail"]


def test_return_api_needs_the_person_the_case_is_with(db, client, world):
    item = _case(db, world["borrower"])
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    db.commit()
    sign_in(client, "priya.raman")
    assert client.post(f"/api/v1/work-items/{item.id}/return", json={"reason": "x"}).status_code == 403


# ---- fix round 1 ----

def test_a_returned_case_cannot_be_decided_until_it_is_routed_again(db, world):
    item = _case(db, world["borrower"], permission="decide_work_item")
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    return_work_item(db, item, user=world["officer"], reason="Attach the signed term sheet first.")
    refuse = workflow.decision_refusal
    why = refuse(db, item, user_id=world["officer"].id, user_role="credit_officer", decision="no_action")
    assert isinstance(why, ValueError) and "returned" in str(why)
    assert [d["permitted"] for d in build_case(db, item, world["officer"])["decisions"]] == [False, False]
    with pytest.raises(ValueError, match="returned"):
        workflow.decide_work_item(db, item, user_id=world["officer"].id, user_role="credit_officer", decision="no_action")
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view="Attached.")
    assert refuse(db, item, user_id=world["officer"].id, user_role="credit_officer", decision="no_action") is None


def test_only_the_person_a_case_was_routed_to_may_decide_it(db, world):
    item = _case(db, world["borrower"], permission="decide_work_item")
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    dana = _user(db, "dana.whitfield")  # holds the permission, but the case is with Helen
    why = workflow.decision_refusal(db, item, user_id=dana.id, user_role=dana.role, decision="no_action")
    assert isinstance(why, ValueError) and "Helen Strand" in str(why)
    assert [d["permitted"] for d in build_case(db, item, dana)["decisions"]] == [False, False]


def test_decide_api_refuses_a_returned_case_and_a_case_with_someone_else(db, client, world):
    item = _case(db, world["borrower"], permission="decide_work_item")
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    db.commit()
    sign_in(client, "dana.whitfield")
    assert client.post(f"/api/v1/work-items/{item.id}/decide", json={"decision": "no_action"}).status_code == 422
    return_work_item(db, item, user=world["officer"], reason="Attach the signed term sheet first.")
    db.commit()
    sign_in(client, "helen.strand")
    r = client.post(f"/api/v1/work-items/{item.id}/decide", json={"decision": "no_action"})
    assert r.status_code == 422 and "returned" in r.json()["detail"]


def test_the_router_is_still_refused_after_a_re_route_and_a_second_router_cannot_route_it_back(db, world):
    item = _case(db, world["borrower"], permission="decide_work_item")
    tomas = _user(db, "tomas.keller")
    route_work_item(db, item, user=world["analyst"], to_user_id=tomas.id, view=VIEW)
    route_work_item(db, item, user=tomas, to_user_id=world["officer"].id, view="Agreed.")
    for who in (world["analyst"], tomas):
        assert isinstance(workflow.decision_refusal(db, item, user_id=who.id, user_role=who.role, decision="no_action"),
                          SecondPersonRequired)
    with pytest.raises(ValueError, match="with someone else"):
        route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    return_work_item(db, item, user=world["officer"], reason="Not yet.")
    route_work_item(db, item, user=tomas, to_user_id=world["officer"].id, view="Again.")
    assert isinstance(workflow.decision_refusal(db, item, user_id=world["analyst"].id, user_role="analyst",
                                                decision="no_action"), SecondPersonRequired)


def test_the_router_check_ignores_the_case_of_an_id(db, world, monkeypatch):
    item = _case(db, world["borrower"], permission="decide_work_item")
    item.prepared_by_id = "terms-agent-run"  # so only the router check can refuse her
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    item.assigned_to = world["analyst"].id
    monkeypatch.setattr(workflow, "routed_by", lambda _db, _item: {str(world["analyst"].id).upper()})
    assert isinstance(workflow.decision_refusal(db, item, user_id=world["analyst"].id, user_role="analyst"),
                      SecondPersonRequired)


def test_the_route_event_records_what_it_changed(db, world):
    from app.core.ledger import LedgerEvent
    from sqlalchemy import select
    item = _case(db, world["borrower"])
    item.prepared_by_id = "terms-agent-run"
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    p = db.execute(select(LedgerEvent).where(LedgerEvent.action == "work_item.routed",
                                             LedgerEvent.entity_id == str(item.id))).scalar_one().payload
    assert p["previous_prepared_by_id"] == "terms-agent-run" and p["previous_requires_second_person"] is False


def test_an_unknown_required_permission_is_a_rule_refusal_422(db, client, world):
    item = _case(db, world["borrower"], permission="decide_work_item")
    item.required_permission = "no_such_permission"
    db.commit()
    sign_in(client, "helen.strand")
    assert client.post(f"/api/v1/work-items/{item.id}/decide", json={"decision": "no_action"}).status_code == 422


def test_assign_refuses_a_routed_case_whoever_asks(db, client, world):
    item = _case(db, world["borrower"])
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    db.commit()
    sign_in(client, "priya.raman")
    r = client.post(f"/api/v1/work-items/{item.id}/assign", json={"assigned_to": None})
    assert r.status_code == 409 and "Return" in r.json()["detail"]
    sign_in(client, "helen.strand")  # even the person holding it goes through Route or Return
    assert client.post(f"/api/v1/work-items/{item.id}/assign", json={"assigned_to": None}).status_code == 409


def test_waiting_is_zero_when_approvals_is_not_offered(db, world):
    item = _case(db, world["borrower"], permission="decide_work_item")
    tomas = _user(db, "tomas.keller")
    route_work_item(db, item, user=world["analyst"], to_user_id=tomas.id, view=VIEW)
    assert build_briefing(db, tomas)["approvals"] == {"offered": False, "waiting": 0}


def test_assign_cannot_walk_a_returned_case_back_to_the_officer(db, client, world):
    item = _case(db, world["borrower"], permission="decide_work_item")
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    return_work_item(db, item, user=world["officer"], reason="Attach the signed term sheet first.")
    db.commit()
    sign_in(client, "priya.raman")
    for body in ({"assigned_to": str(world["officer"].id)}, {"assigned_to": None}):
        r = client.post(f"/api/v1/work-items/{item.id}/assign", json=body)
        assert r.status_code == 409 and "Route" in r.json()["detail"]
    sign_in(client, "helen.strand")
    assert client.post(f"/api/v1/work-items/{item.id}/decide", json={"decision": "no_action"}).status_code == 422


def test_a_case_is_returned_whoever_it_is_assigned_to(db, world):
    item = _case(db, world["borrower"], permission="decide_work_item")
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    return_work_item(db, item, user=world["officer"], reason="Attach the signed term sheet first.")
    for holder in (world["officer"].id, None):  # however it got there, a return stands until it is routed again
        item.assigned_to = holder
        why = workflow.decision_refusal(db, item, user_id=world["officer"].id, user_role="credit_officer",
                                        decision="no_action")
        assert isinstance(why, ValueError) and "returned" in str(why)


def test_an_item_with_an_unknown_permission_is_not_in_an_analysts_briefing(db, world):
    item = _case(db, world["borrower"], permission="decide_work_item")
    item.required_permission = "no_such_permission"
    db.flush()
    assert not any(i["work_item_id"] == str(item.id) for i in build_briefing(db, world["analyst"])["items"])
