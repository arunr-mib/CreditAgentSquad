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
    """Priya's client (as Datamarrow is in the seeded book) and Tomas, another analyst."""
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


def test_holding_a_case_of_a_client_not_hers_does_not_let_an_analyst_act(db, owned):
    """Owner answer 9: assignment does not widen an analyst's fixed portfolio."""
    item = _case(db, owned["borrower"])
    item.assigned_to = owned["tomas"].id  # however it came to be his
    db.flush()
    why = refuse(db, item, owned["tomas"])
    assert isinstance(why, PermissionError) and "Priya Raman" in str(why)
    assert isinstance(refuse(db, item, owned["analyst"]), PermissionError)  # it is with someone else
    assert refuse(db, item, owned["officer"]) is None


def test_a_client_with_no_analyst_is_no_analysts_until_one_is_named(db, world):
    from app.domain.credit import Borrower

    unowned = Borrower(code="NOA", name="Nobody's Analytics, Inc.")
    db.add(unowned)
    db.flush()
    world = {**world, "other": unowned}
    item = _case(db, unowned)
    for who in (world["analyst"], _user(db, "tomas.keller")):
        why = refuse(db, item, who)
        assert isinstance(why, PermissionError) and "has no analyst yet" in str(why)
    assert refuse(db, item, world["officer"]) is None
    assert workflow.client_refusal(db, world["other"].id, user_id=world["analyst"].id, user_role="analyst") is not None


def test_a_case_cannot_be_routed_to_an_analyst_who_does_not_own_the_client(db, owned):
    item = _case(db, owned["borrower"])
    view = build_case(db, item, owned["analyst"])
    names = [p["name"] for p in view["route_to"]]
    assert "Tomas Keller" not in names and "Helen Strand" in names
    with pytest.raises(ValueError, match="Priya Raman"):
        route_work_item(db, item, user=owned["analyst"], to_user_id=owned["tomas"].id, view=VIEW)
    assert item.assigned_to is None


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


def test_the_api_refuses_an_analyst_holding_a_case_of_a_client_not_hers(db, client, owned):
    item = _case(db, owned["borrower"])
    item.assigned_to = owned["tomas"].id
    db.commit()
    sign_in(client, "tomas.keller")
    r = client.post(f"/api/v1/work-items/{item.id}/decide", json={"decision": "no_action"})
    assert r.status_code == 403 and "Priya Raman" in r.json()["detail"]


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
    from app.domain.credit import Borrower

    unowned = Borrower(code="NOA", name="Nobody's Analytics, Inc.")
    db.add(unowned)
    db.flush()
    loose = _case(db, unowned, title="Confirm revenue")  # a client with no analyst
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


# ---- fact repair follows the same engine rule (coordinator, after the final fix wave) ----

def _held_fact(db, borrower):
    from decimal import Decimal

    from app.domain.facts_service import add_fact
    return add_fact(db, borrower_id=borrower.id, key="bs.cash", period_end=__import__("datetime").date(2026, 9, 30),
                    months=0, value=Decimal("1000"), kind="seeded", status="proposed")


def test_the_engine_refuses_another_analyst_repairing_a_clients_figures(db, owned):
    refuse = workflow.client_refusal
    why = refuse(db, owned["borrower"].id, user_id=owned["tomas"].id, user_role="analyst")
    assert isinstance(why, PermissionError) and "Priya Raman" in str(why)
    assert refuse(db, owned["borrower"].id, user_id=owned["analyst"].id, user_role="analyst") is None
    assert refuse(db, owned["borrower"].id, user_id=owned["officer"].id, user_role="credit_officer") is None
    case = _case(db, owned["borrower"])
    case.assigned_to = owned["tomas"].id
    db.flush()
    assert refuse(db, owned["borrower"].id, user_id=owned["tomas"].id, user_role="analyst") is not None  # no widening


def test_the_fact_repair_routes_refuse_another_analyst_with_403_naming_the_clients_analyst(db, client, owned):
    fact = _held_fact(db, owned["borrower"])
    db.commit()
    sign_in(client, "tomas.keller")
    for path, body in ((f"/api/v1/facts/{fact.id}/confirm", None),
                       (f"/api/v1/facts/{fact.id}/correct", {"value": "1200", "reason": "As printed."}),
                       (f"/api/v1/facts/{fact.id}/reject", {"reason": "Wrong line."}),
                       (f"/api/v1/borrowers/{owned['borrower'].id}/facts",
                        {"key": "bs.cash", "period_end": "2026-09-30", "months": 0, "value": "1200", "reason": "Keyed."})):
        r = client.post(path, json=body) if body is not None else client.post(path)
        assert r.status_code == 403 and "Priya Raman" in r.json()["detail"], (path, r.status_code, r.text)
    sign_in(client, "priya.raman")
    assert client.post(f"/api/v1/facts/{fact.id}/confirm").status_code == 200


# ---- final re-review O1: assigning goes through the same engine rule ----

def test_another_analyst_cannot_assign_a_clients_case_to_himself_and_so_cannot_decide_or_repair(db, client, owned):
    item = _case(db, owned["borrower"])
    fact = _held_fact(db, owned["borrower"])
    db.commit()
    sign_in(client, "tomas.keller")
    r = client.post(f"/api/v1/work-items/{item.id}/assign", json={"assigned_to": str(owned["tomas"].id)})
    assert r.status_code == 403 and "Priya Raman" in r.json()["detail"]
    db.refresh(item)
    assert item.assigned_to is None
    assert client.post(f"/api/v1/work-items/{item.id}/decide", json={"decision": "no_action"}).status_code == 403
    assert client.post(f"/api/v1/facts/{fact.id}/confirm").status_code == 403


def test_a_case_cannot_be_assigned_to_an_analyst_who_does_not_own_the_client(db, client, owned):
    item = _case(db, owned["borrower"])
    db.commit()
    for who in ("priya.raman", "helen.strand"):  # neither the client's analyst nor an officer can widen it
        sign_in(client, who)
        r = client.post(f"/api/v1/work-items/{item.id}/assign", json={"assigned_to": str(owned["tomas"].id)})
        assert r.status_code == 422 and "Priya Raman" in r.json()["detail"], who
    db.refresh(item)
    assert item.assigned_to is None
    sign_in(client, "helen.strand")
    assert client.post(f"/api/v1/work-items/{item.id}/assign", json={"assigned_to": str(owned["officer"].id)}).status_code == 200
    sign_in(client, "priya.raman")  # her client: she may take it back
    assert client.post(f"/api/v1/work-items/{item.id}/assign", json={"assigned_to": str(owned["analyst"].id)}).status_code == 200


def test_an_analyst_cannot_move_a_case_on_another_analysts_client_that_is_with_someone_else(db, client, owned):
    item = _case(db, owned["borrower"])
    item.assigned_to = owned["officer"].id
    db.commit()
    sign_in(client, "tomas.keller")
    r = client.post(f"/api/v1/work-items/{item.id}/assign", json={"assigned_to": str(owned["tomas"].id)})
    assert r.status_code == 403
    sign_in(client, "priya.raman")  # her client: she may move it back to herself
    assert client.post(f"/api/v1/work-items/{item.id}/assign", json={"assigned_to": str(owned["analyst"].id)}).status_code == 200


def test_yours_and_approvals_never_count_a_case_for_an_analyst_who_does_not_own_the_client(db, owned):
    item = _case(db, owned["borrower"])
    item.assigned_to = owned["tomas"].id
    db.flush()
    rows = [i for i in build_briefing(db, owned["tomas"])["items"] if i["work_item_id"] == str(item.id)]
    assert not any(r["needs_you"] for r in rows)
    assert str(item.id) not in {r["work_item_id"] for r in build_approvals(db, owned["tomas"])}
    assert rules.yours(owned["tomas"], item, owned["borrower"]) is False
