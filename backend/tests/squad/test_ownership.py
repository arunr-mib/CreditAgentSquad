"""Final review I1, I2, M1, M2: one predicate for who may act. The engine (`workflow.decision_refusal`) owns the rule that
an analyst decides only her own clients' cases (or a case assigned or routed to her); the screens, routing, attaching
and the briefing's "yours" read that predicate and nothing else."""
import pytest
from app.core.roles import APPROVER_PERMISSIONS
from app.domain import workflow
from app.domain.documents import Document
from app.domain.routing import attach_evidence, route_work_item
from app.domain.work_items import raise_item
from app.squad import rules
from app.squad.briefing import build_briefing
from app.squad.cases import build_approvals, build_case

from .conftest import _user, sign_in

VIEW = "Runway is under the watch line; recommend asking for the board's plan."


def _case(db, borrower, permission="decide_work_item", title="Runway below watch"):
    return raise_item(db, borrower_id=borrower.id, item_type="test.routed_case", title=title, severity="high",
                      question="How should the bank respond?", allowed_decisions=["reserve_rights", "no_action"],
                      required_permission=permission)


def _doc(db, borrower):
    from datetime import date

    d = Document(borrower_id=borrower.id, title="Board plan", file_name="p.pdf", storage_path="x", sha256="d" * 64,
                 page_count=1, doc_type="other", period_end=date(2026, 10, 31), status="indexed")
    db.add(d)
    db.flush()
    return d


@pytest.fixture()
def owned(db, world):
    """Priya's client (as Dataflake is in the seeded book) and Tomas, another analyst."""
    world["borrower"].analyst_id = world["analyst"].id
    db.flush()
    return {**world, "tomas": _user(db, "tomas.keller")}


def refuse(db, item, who, decision="no_action"):
    return workflow.decision_refusal(db, item, user_id=who.id, user_role=who.role, decision=decision)


# ---- the engine ----

def test_the_engine_refuses_another_analyst_on_a_clients_unassigned_case_and_names_the_owner(db, owned):
    item = _case(db, owned["borrower"])
    why = refuse(db, item, owned["tomas"])
    assert isinstance(why, PermissionError) and "Priya Raman" in str(why)
    with pytest.raises(PermissionError):
        workflow.decide_work_item(db, item, user_id=owned["tomas"].id, user_role="analyst", decision="no_action")
    assert item.status == "open"
    assert refuse(db, item, owned["analyst"]) is None
    assert refuse(db, item, owned["officer"]) is None  # officers are unchanged


def test_an_assigned_case_is_the_assignees_whoever_the_clients_analyst_is(db, owned):
    item = _case(db, owned["borrower"])
    item.assigned_to = owned["tomas"].id  # assigned, never routed
    db.flush()
    assert refuse(db, item, owned["tomas"]) is None
    assert isinstance(refuse(db, item, owned["analyst"]), PermissionError)


def test_a_client_with_no_analyst_is_any_analysts(db, world):
    item = _case(db, world["borrower"])
    assert refuse(db, item, _user(db, "tomas.keller")) is None


def test_a_routee_who_is_not_the_clients_analyst_may_still_receive_and_decide(db, owned):
    item = _case(db, owned["borrower"])
    view = build_case(db, item, owned["analyst"])
    assert "Tomas Keller" in [p["name"] for p in view["route_to"]]
    route_work_item(db, item, user=owned["analyst"], to_user_id=owned["tomas"].id, view=VIEW)
    assert refuse(db, item, owned["tomas"]) is None


def test_routing_and_attaching_ask_the_same_ownership_rule(db, owned):
    item = _case(db, owned["borrower"])
    doc = _doc(db, owned["borrower"])
    with pytest.raises(PermissionError, match="Priya Raman"):
        route_work_item(db, item, user=owned["tomas"], to_user_id=owned["officer"].id, view=VIEW)
    with pytest.raises(PermissionError, match="Priya Raman"):
        attach_evidence(db, item, user=owned["tomas"], document_id=doc.id)
    attach_evidence(db, item, user=owned["analyst"], document_id=doc.id)
    route_work_item(db, item, user=owned["analyst"], to_user_id=owned["officer"].id, view=VIEW)
    assert item.assigned_to == owned["officer"].id


def test_the_screens_offer_nothing_the_engine_would_refuse(db, owned):
    item = _case(db, owned["borrower"])
    view = build_case(db, item, owned["tomas"])
    assert not (view["may_route"] or view["may_attach"] or view["may_repair"] or view["needs_you"])
    assert not any(d["permitted"] for d in view["decisions"]) and view["candidates"] == []
    assert rules.can_act(owned["tomas"], item, owned["borrower"]) is False
    mine = build_case(db, item, owned["analyst"])
    assert mine["may_route"] and mine["may_attach"] and mine["needs_you"] and mine["may_repair"]


# ---- the API ----

def test_the_api_refuses_tomas_deciding_routing_and_attaching_on_priyas_client(db, client, owned):
    item = _case(db, owned["borrower"])
    doc = _doc(db, owned["borrower"])
    db.commit()
    sign_in(client, "tomas.keller")
    r = client.post(f"/api/v1/work-items/{item.id}/decide", json={"decision": "no_action"})
    assert r.status_code == 403 and "Priya Raman" in r.json()["detail"]
    r = client.post(f"/api/v1/work-items/{item.id}/route", json={"to": str(owned["officer"].id), "view": VIEW})
    assert r.status_code == 403
    r = client.post(f"/api/v1/work-items/{item.id}/attach", json={"document_id": str(doc.id)})
    assert r.status_code == 403
    case = client.get(f"/api/v1/cases/{item.id}").json()
    assert not (case["may_route"] or case["may_attach"]) and not any(d["permitted"] for d in case["decisions"])


def test_the_api_lets_the_assignee_decide_and_refuses_anyone_else(db, client, owned):
    item = _case(db, owned["borrower"])
    item.assigned_to = owned["tomas"].id
    db.commit()
    sign_in(client, "priya.raman")
    assert client.post(f"/api/v1/work-items/{item.id}/decide", json={"decision": "no_action"}).status_code == 403
    sign_in(client, "tomas.keller")
    assert client.post(f"/api/v1/work-items/{item.id}/decide", json={"decision": "no_action"}).status_code == 200


def test_the_officer_still_receives_a_routed_case(db, client, owned):
    item = _case(db, owned["borrower"])
    route_work_item(db, item, user=owned["analyst"], to_user_id=owned["officer"].id, view=VIEW)
    db.commit()
    sign_in(client, "helen.strand")
    assert client.post(f"/api/v1/work-items/{item.id}/decide", json={"decision": "no_action"}).status_code == 200


# ---- I2: "yours" for officers, portfolio managers and credit administration ----

def test_an_analysts_unassigned_judgement_is_not_counted_for_other_roles(db, owned):
    item = _case(db, owned["borrower"])  # decide_work_item on Priya's client: her judgement
    for who in ("helen.strand", "li.zhang", "marcus.oyelaran"):
        person = _user(db, who)
        rows = [i for i in build_briefing(db, person)["items"] if i["work_item_id"] == str(item.id)]
        assert not any(r["needs_you"] for r in rows), who
    assert build_briefing(db, owned["analyst"])["needs_you"] == 1


def test_an_approver_item_and_a_client_without_an_analyst_count_for_the_officer(db, owned):
    breach = _case(db, owned["borrower"], permission="decide_breach", title="Cash below minimum")
    loose = _case(db, owned["other"], title="Confirm revenue")  # the other client has no analyst
    b = build_briefing(db, owned["officer"])
    counted = {i["work_item_id"] for i in b["items"] if i["needs_you"]}
    assert counted == {str(breach.id), str(loose.id)} and b["needs_you"] == 2


def test_home_approval_items_equal_approvals_for_every_role(db, owned):
    _case(db, owned["borrower"], permission="decide_breach", title="Cash below minimum")
    _case(db, owned["borrower"], title="Runway below watch")
    routed = _case(db, owned["borrower"], title="Revenue fell")
    route_work_item(db, routed, user=owned["analyst"], to_user_id=owned["officer"].id, view=VIEW)
    from app.domain.monitoring import WorkItem

    for who in ("helen.strand", "li.zhang", "marcus.oyelaran", "dana.whitfield"):
        person = _user(db, who)
        approvals = {r["work_item_id"] for r in build_approvals(db, person)}
        home = set()
        for i in build_briefing(db, person)["items"]:
            if not (i["needs_you"] and i["work_item_id"]):
                continue
            w = db.get(WorkItem, i["work_item_id"])
            if w.required_permission in APPROVER_PERMISSIONS or w.assigned_to == person.id:
                home.add(i["work_item_id"])
        assert home == approvals, who
    assert {r["work_item_id"] for r in build_approvals(db, owned["officer"])} >= {str(routed.id)}


# ---- M2: no Route while Squad waits for a match confirmation ----

def test_route_is_not_offered_while_a_match_question_is_open(db, owned, monkeypatch):
    item = _case(db, owned["borrower"])
    from app.domain import routing

    monkeypatch.setattr(routing, "open_match_questions", lambda _db, _item: [object()])
    view = build_case(db, item, owned["analyst"])
    assert view["may_route"] is False and view["state_words"] == "Confirm which document first"
    assert view["route_blocked_words"] == "Confirm which document first"
