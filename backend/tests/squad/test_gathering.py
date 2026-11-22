"""Task 5c: when an officer returns a case saying what is needed, code matches and Squad gathers; a person confirms
only when Squad is not sure. No model call anywhere."""
from datetime import date

import pytest
from app.core.ledger import LedgerEvent
from app.domain import gathering
from app.domain.documents import Document
from app.domain.monitoring import WorkItem
from app.domain.routing import RouteBlocked, attached_ids, return_work_item, route_work_item
from app.domain.work_items import raise_item
from app.squad import drafts
from app.squad.cases import build_case
from app.squad.questions import answer_question
from app.squad.threads import build_thread
from sqlalchemy import select

from .conftest import sign_in

VIEW = "Unrestricted cash fell under the floor; recommend reserving rights."
SEPT = date(2026, 9, 30)
OCT = date(2026, 10, 31)


def _case(db, borrower):
    return raise_item(db, borrower_id=borrower.id, item_type="test.routed_case", title="Cash below minimum",
                      severity="high", question="How should the bank respond?",
                      allowed_decisions=["reserve_rights", "no_action"], required_permission="decide_breach")


def _doc(db, borrower, doc_type="bank_statement", period=SEPT, source="system", status="indexed", title=None, pages=3):
    d = Document(borrower_id=borrower.id, title=title or f"Account statement {period:%B %Y}", file_name="s.pdf",
                 storage_path="x", sha256="c" * 64, page_count=pages, doc_type=doc_type, doc_type_source=source,
                 period_end=period, received_date=date(2026, 10, 3), status=status)
    db.add(d)
    db.flush()
    return d


def _returned(db, world, needs, case=None):
    item = case or _case(db, world["borrower"])
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    return_work_item(db, item, user=world["officer"], reason="Need the September statement.", needs=needs)
    return item


NEED = {"doc_type": "bank_statement", "period_end": SEPT}


def _events(db, item, action):
    return list(db.execute(select(LedgerEvent).where(LedgerEvent.entity_id == str(item.id),
                                                     LedgerEvent.action == action).order_by(LedgerEvent.seq)).scalars())


def _questions(db, item):
    return [q for q in db.execute(select(WorkItem).where(WorkItem.item_type == "question")).scalars()
            if (q.evidence or {}).get("topic") == "evidence_match" and q.evidence.get("case_id") == str(item.id)]


def _requests(db, borrower):
    return [d for d in drafts.drafts_for(db, borrower.id) if d["kind"] == "evidence_request"]


def test_one_confident_match_is_attached_by_squad_and_said_in_the_thread(db, world):
    doc = _doc(db, world["borrower"])
    item = _returned(db, world, [NEED])
    (event,) = _events(db, item, "work_item.evidence_attached")
    assert (event.actor_type, event.actor_id) == ("system", "squad")
    assert event.payload["document_id"] == str(doc.id) and event.payload["matched_need"] == 0
    assert event.payload["rule"] == "doc_type+period_end"
    text = "Attached the Bank statement for September 2026 that Helen Strand asked for."
    thread = build_thread(db, world["borrower"].id, world["analyst"])
    msg = next(m for m in thread["messages"] if m["type"] == "attached")
    assert msg["by"] == "Squad" and msg["note"] == text
    states = gathering.need_states(db, item)
    assert states[0]["state"] == "attached" and states[0]["document_id"] == str(doc.id)
    assert states[0]["state_words"] == "Attached: Bank statement, September 2026"


def test_no_match_drafts_one_request_per_need_and_twice_keeps_one(db, world):
    item = _returned(db, world, [NEED, {"doc_type": "mrr_report", "period_end": SEPT}])
    gathering.gather_requested(db, item)
    found = _requests(db, world["borrower"])
    assert len(found) == 2
    assert any(d["body"] == "Could you send the Bank statement for September 2026 when you have a moment?"
               for d in found)
    assert {s["state"] for s in gathering.need_states(db, item)} == {"requested_from_client"}
    assert gathering.need_states(db, item)[0]["state_words"] == "Asked the client"


def test_two_candidates_ask_the_holder_and_block_the_route_until_answered(db, world):
    a = _doc(db, world["borrower"], title="Statement A")
    b = _doc(db, world["borrower"], title="Statement B", pages=5)
    item = _returned(db, world, [NEED])
    (q,) = _questions(db, item)
    assert q.assigned_to == world["analyst"].id and q.status == "open"
    labels = [o["label"] for o in q.evidence["options"]]
    assert len(labels) == 3 and labels[-1] == "None of these"
    assert "Statement A" in labels[0] + labels[1] and "5 pages" in labels[0] + labels[1]
    assert _events(db, item, "work_item.evidence_attached") == []
    gathering.gather_requested(db, item)
    assert len(_questions(db, item)) == 1  # idempotent
    assert gathering.need_states(db, item)[0]["state"] == "waiting_for_you"
    with pytest.raises(RouteBlocked, match="more than one document"):
        route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view="Done.")
    option = next(o for o in q.evidence["options"] if o["label"].startswith("Statement B"))
    answer_question(db, q, world["analyst"], option["id"])
    (event,) = _events(db, item, "work_item.evidence_attached")
    assert event.actor_type == "user" and event.actor_id == str(world["analyst"].id)
    assert event.payload["document_id"] == str(b.id) and event.payload["matched_need"] == 0
    assert str(a.id) not in attached_ids(db, item)
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view="Done.")


def test_none_of_these_leaves_the_need_unmet_and_drafts_the_request(db, world):
    _doc(db, world["borrower"], title="Statement A")
    _doc(db, world["borrower"], title="Statement B")
    item = _returned(db, world, [NEED])
    (q,) = _questions(db, item)
    answer_question(db, q, world["analyst"], "none")
    assert _events(db, item, "work_item.evidence_attached") == []
    assert len(_requests(db, world["borrower"])) == 1
    gathering.gather_requested(db, item)
    assert len(_questions(db, item)) == 1 and len(_requests(db, world["borrower"])) == 1
    assert gathering.need_states(db, item)[0]["state"] == "requested_from_client"
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view="Asked the client.")


def test_unmet_needs_asked_of_the_client_do_not_block_routing(db, world):
    item = _returned(db, world, [NEED])
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view="Waiting on the client.")


def test_one_agent_classified_candidate_is_asked_not_attached(db, world):
    _doc(db, world["borrower"], source="agent")
    item = _returned(db, world, [NEED])
    assert _events(db, item, "work_item.evidence_attached") == []
    (q,) = _questions(db, item)
    assert len(q.evidence["options"]) == 2


def test_a_document_classified_after_the_return_is_gathered(db, world):
    item = _returned(db, world, [NEED])
    assert len(_requests(db, world["borrower"])) == 1
    _doc(db, world["borrower"])
    gathering.gather_for_borrower(db, world["borrower"].id)
    assert len(_events(db, item, "work_item.evidence_attached")) == 1
    assert gathering.need_states(db, item)[0]["state"] == "attached"
    gathering.gather_for_borrower(db, world["borrower"].id)
    assert len(_events(db, item, "work_item.evidence_attached")) == 1


def test_rejected_other_client_other_period_and_attached_documents_are_never_matched(db, world):
    _doc(db, world["borrower"], status="rejected")
    _doc(db, world["other"])
    _doc(db, world["borrower"], period=OCT)
    _doc(db, world["borrower"], doc_type="mrr_report")
    item = _returned(db, world, [NEED])
    assert _events(db, item, "work_item.evidence_attached") == [] and _questions(db, item) == []
    assert len(_requests(db, world["borrower"])) == 1
    only = _doc(db, world["borrower"])
    gathering.gather_requested(db, item)
    assert attached_ids(db, item) == {str(only.id)}
    gathering.gather_requested(db, item)
    assert len(_events(db, item, "work_item.evidence_attached")) == 1


@pytest.mark.parametrize("needs, message", [
    ([{"doc_type": "napkin", "period_end": SEPT}], "document type"),
    ([{"doc_type": "bank_statement", "period_end": date(2026, 9, 15)}], "month end"),
    ([{"doc_type": "bank_statement", "period_end": date(2026, m, 28 if m == 2 else 30)} for m in range(1, 7)], "at most 5"),
])
def test_invalid_needs_are_refused_in_words(db, world, needs, message):
    item = _case(db, world["borrower"])
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    with pytest.raises(ValueError, match=message):
        return_work_item(db, item, user=world["officer"], reason="Need things.", needs=needs)
    assert _events(db, item, "work_item.returned") == []


def test_the_return_api_takes_needs_and_refuses_bad_ones_with_422(db, client, world):
    _doc(db, world["borrower"])
    item = _case(db, world["borrower"])
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    db.commit()
    sign_in(client, "helen.strand")
    url = f"/api/v1/work-items/{item.id}/return"
    bad = client.post(url, json={"reason": "x", "needs": [{"doc_type": "bank_statement", "period_end": "2026-09-15"}]})
    assert bad.status_code == 422 and "month end" in bad.json()["detail"]
    six = [{"doc_type": "bank_statement", "period_end": f"2026-{m:02d}-28" if m == 2 else f"2026-{m:02d}-30"}
           for m in range(1, 7)]
    assert client.post(url, json={"reason": "x", "needs": six}).status_code == 422
    ok = client.post(url, json={"reason": "Need it.", "needs": [{"doc_type": "bank_statement", "period_end": "2026-09-30"}]})
    assert ok.status_code == 200
    need = ok.json()["needs"][0]
    assert need["state"] == "attached" and need["state_words"] == "Attached: Bank statement, September 2026"


def test_the_route_api_says_409_while_a_match_question_is_open(db, client, world):
    _doc(db, world["borrower"], title="Statement A")
    _doc(db, world["borrower"], title="Statement B")
    item = _returned(db, world, [NEED])
    db.commit()
    sign_in(client, "priya.raman")
    r = client.post(f"/api/v1/work-items/{item.id}/route", json={"to": str(world["officer"].id), "view": "Done."})
    assert r.status_code == 409 and "confirm which" in r.json()["detail"]


def test_the_case_view_lists_each_need_with_its_state(db, world):
    _doc(db, world["borrower"])
    item = _returned(db, world, [NEED, {"doc_type": "mrr_report", "period_end": SEPT}])
    view = build_case(db, item, world["analyst"])
    assert [(n["state"], n["state_words"]) for n in view["needs"]] == [
        ("attached", "Attached: Bank statement, September 2026"), ("requested_from_client", "Asked the client")]
    assert view["needs"][1]["words"] == "MRR report, September 2026"


# ---- fix round 1 ----
from app.domain import gathering as gathering_module  # noqa: E402
from app.domain.routing import attach_evidence, clean_needs  # noqa: E402
from app.squad.questions import raise_question  # noqa: E402


def _routed(db, world):
    item = _case(db, world["borrower"])
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    return item


def test_c1_an_earlier_rejected_attachment_does_not_meet_a_new_request(db, world):
    wrong = _doc(db, world["borrower"], title="Wrong account")
    item = _case(db, world["borrower"])
    attach_evidence(db, item, user=world["analyst"], document_id=wrong.id)  # before the return
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    wrong.status = "rejected"
    right = _doc(db, world["borrower"], title="Right account")
    return_work_item(db, item, user=world["officer"], reason="Wrong account.", needs=[NEED])
    states = gathering.need_states(db, item)
    assert states[0]["state"] == "attached" and states[0]["document_id"] == str(right.id)
    assert str(right.id) in attached_ids(db, item)


def test_c1_an_earlier_attachment_that_is_still_valid_does_not_meet_it_either(db, world):
    earlier = _doc(db, world["borrower"], title="Earlier")
    item = _case(db, world["borrower"])
    attach_evidence(db, item, user=world["analyst"], document_id=earlier.id)
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    return_work_item(db, item, user=world["officer"], reason="Not this one.", needs=[NEED])
    assert gathering.need_states(db, item)[0]["state"] == "requested_from_client"


def test_c1_two_right_documents_ask_and_block_routing_while_unsure(db, world):
    wrong = _doc(db, world["borrower"], title="Wrong account")
    item = _case(db, world["borrower"])
    attach_evidence(db, item, user=world["analyst"], document_id=wrong.id)
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    wrong.status = "rejected"
    _doc(db, world["borrower"], title="Right one")
    _doc(db, world["borrower"], title="Right two")
    return_work_item(db, item, user=world["officer"], reason="Wrong account.", needs=[NEED])
    assert gathering.need_states(db, item)[0]["state"] == "waiting_for_you"
    with pytest.raises(RouteBlocked):
        route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view="Done.")


def test_c1_an_answer_naming_a_document_rejected_meanwhile_is_refused(db, world):
    _doc(db, world["borrower"], title="Statement A")
    b = _doc(db, world["borrower"], title="Statement B")
    item = _returned(db, world, [NEED])
    (q,) = _questions(db, item)
    b.status = "rejected"
    option = next(o for o in q.evidence["options"] if o["label"].startswith("Statement B"))
    with pytest.raises(ValueError, match="set aside"):
        answer_question(db, q, world["analyst"], option["id"])
    assert _events(db, item, "work_item.evidence_attached") == []


def test_i2_a_gathering_failure_never_fails_the_return(db, world, monkeypatch):
    def boom(db_, item_):
        raise RuntimeError("gathering broke")

    monkeypatch.setattr(gathering_module, "gather_requested", boom)
    item = _returned(db, world, [NEED])
    assert len(_events(db, item, "work_item.returned")) == 1
    failed = _events(db, item, "work_item.gathering_failed")
    assert len(failed) == 1 and "gathering broke" not in str(failed[0].payload.get("reason", ""))
    view = build_case(db, item, world["analyst"])
    assert view["needs"][0]["state_words"] == "Squad could not gather; please attach by hand"


def test_m1_none_of_these_offers_a_document_that_arrived_meanwhile(db, world):
    _doc(db, world["borrower"], title="Statement A")
    _doc(db, world["borrower"], title="Statement B")
    item = _returned(db, world, [NEED])
    (q,) = _questions(db, item)
    c = _doc(db, world["borrower"], title="Corrected statement")
    gathering.gather_for_borrower(db, world["borrower"].id)  # an open question is left alone
    assert len(_questions(db, item)) == 1
    answer_question(db, q, world["analyst"], "none")
    assert _requests(db, world["borrower"]) == []
    assert attached_ids(db, item) == {str(c.id)}


def test_m1_a_doubtful_newcomer_is_asked_about_not_drafted_for(db, world):
    _doc(db, world["borrower"], title="Statement A")
    _doc(db, world["borrower"], title="Statement B")
    item = _returned(db, world, [NEED])
    (q,) = _questions(db, item)
    _doc(db, world["borrower"], title="Maybe", source="agent")
    answer_question(db, q, world["analyst"], "none")
    assert _requests(db, world["borrower"]) == []
    opened = [x for x in _questions(db, item) if x.status == "open"]
    assert len(opened) == 1 and "Maybe" in opened[0].evidence["options"][0]["label"]


def test_m1_a_draft_made_earlier_is_marked_no_longer_needed_when_the_document_comes(db, world):
    item = _returned(db, world, [NEED])
    (draft,) = _requests(db, world["borrower"])
    _doc(db, world["borrower"])
    gathering.gather_for_borrower(db, world["borrower"].id)
    now = drafts.get_draft(db, draft["draft_id"])
    assert now["status"] == "withdrawn"
    with pytest.raises(ValueError, match="no longer needed"):
        drafts.send_draft(db, draft["draft_id"], world["analyst"])
    assert [e for e in _events(db, item, "work_item.evidence_attached")]


@pytest.mark.parametrize("bad", ["quarterly_statements", "bank_statements", "other"])
def test_m2_only_types_a_document_can_have_are_accepted(bad):
    with pytest.raises(ValueError, match="document type"):
        clean_needs([{"doc_type": bad, "period_end": SEPT}])


def test_m2_the_served_words_say_which_types_can_be_asked_for(db, client, world):
    sign_in(client, "helen.strand")
    served = client.get("/api/v1/words/document-types").json()
    assert "bank_statement" in served["needable"] and "other" not in served["needable"]
    assert "quarterly_statements" not in served["needable"]


def test_m3_an_answer_to_a_question_of_another_need_attaches_nothing(db, world):
    _doc(db, world["borrower"], title="Statement A")
    _doc(db, world["borrower"], title="Statement B")
    item = _returned(db, world, [NEED])
    (q,) = _questions(db, item)
    q.evidence = {**q.evidence, "need_key": "stale"}
    answer_question(db, q, world["analyst"], next(iter(q.evidence["option_documents"])))
    assert _events(db, item, "work_item.evidence_attached") == []


def test_m5_a_question_closed_without_an_answer_lets_the_need_be_asked_again(db, world):
    _doc(db, world["borrower"], title="Statement A")
    _doc(db, world["borrower"], title="Statement B")
    item = _returned(db, world, [NEED])
    (q,) = _questions(db, item)
    q.status, q.decision = "decided", None
    gathering.gather_requested(db, item)
    assert [x.status for x in _questions(db, item)].count("open") == 1 and len(_questions(db, item)) == 2


def test_the_person_who_picks_a_document_confirms_its_type_for_next_time(db, world):
    _doc(db, world["borrower"], title="Statement A", source="agent")
    b = _doc(db, world["borrower"], title="Statement B", source="agent")
    item = _returned(db, world, [NEED])
    (q,) = _questions(db, item)
    option = next(o for o in q.evidence["options"] if o["label"].startswith("Statement B"))
    answer_question(db, q, world["analyst"], option["id"])
    assert b.doc_type_source == "person"
    (event,) = [e for e in db.execute(select(LedgerEvent).where(
        LedgerEvent.entity_id == str(b.id), LedgerEvent.action == "document.classified")).scalars()]
    assert event.actor_type == "user" and event.payload["doc_type"] == "bank_statement"
    assert event.payload["confirmed_by_person"] is True and item.status == "open"


def test_n1_a_figure_in_an_option_is_refused_unless_the_question_is_written_by_code(db, world):
    options = [{"id": "a", "label": "Statement, 5 pages", "evidence": ""}, {"id": "b", "label": "None", "evidence": ""}]
    with pytest.raises(ValueError, match="figure"):
        raise_question(db, borrower_id=world["borrower"].id, title="t", question="Which?", options=options,
                       actor=("system", "other"))
    raise_question(db, borrower_id=world["borrower"].id, title="t", question="Which?", options=options,
                   actor=("system", "squad"), written_by_code=True)


def test_n2_the_thread_says_by_kind_who_attached(db, world):
    _doc(db, world["borrower"])
    item = _returned(db, world, [NEED])
    other = _doc(db, world["borrower"], title="Another", doc_type="mrr_report")
    attach_evidence(db, item, user=world["analyst"], document_id=other.id)
    kinds = [m["by_kind"] for m in build_thread(db, world["borrower"].id, world["analyst"])["messages"]
             if m["type"] == "attached"]
    assert kinds == ["squad", "user"]
