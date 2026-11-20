import uuid
from datetime import date

from app.core import ledger
from app.domain import workflow
from app.domain.documents import Document
from app.domain.work_items import raise_item
from app.squad.threads import build_thread

from .conftest import sign_in


def _item(db, borrower, title="Confirm revenue"):
    return raise_item(db, borrower_id=borrower.id, item_type="funding_slipped", title=title,
                      question="Should the runway outlook be reviewed?", allowed_decisions=["reviewed", "escalate_to_committee"])


def _doc(db, borrower, status="indexed", title="October compliance certificate"):
    d = Document(borrower_id=borrower.id, title=title, file_name="c.pdf", storage_path="x", sha256="a" * 64,
                 page_count=2, doc_type="compliance_certificate", period_end=date(2026, 10, 31), status=status)
    db.add(d)
    db.flush()
    ledger.record(db, actor_type="system", actor_id="intake", action="document.received", entity_type="document",
                  entity_id=d.id, payload={"borrower_id": borrower.id, "file_name": "c.pdf"})
    return d


def test_an_empty_client_has_an_empty_thread_not_an_error(db, world):
    thread = build_thread(db, world["borrower"].id)
    assert thread["messages"] == []
    assert thread["borrower"]["code"] == "QFL"
    assert isinstance(thread["head_seq"], int)


def test_thread_maps_documents_cases_and_decisions_in_time_order(db, world):
    doc = _doc(db, world["borrower"])
    item = _item(db, world["borrower"])
    workflow.decide_work_item(db, item, user_id=world["analyst"].id, user_role="analyst", decision="reviewed")
    kinds = [m["type"] for m in build_thread(db, world["borrower"].id)["messages"]]
    assert kinds == ["document", "case", "decision"]
    document = build_thread(db, world["borrower"].id)["messages"][0]
    assert document["document_id"] == str(doc.id) and document["pages"] == 2


def test_a_set_aside_document_is_a_held_message_with_its_reason(db, world):
    doc = _doc(db, world["borrower"], status="rejected")
    ledger.record(db, actor_type="user", actor_id=world["analyst"].id, action="document.set_aside",
                  entity_type="document", entity_id=doc.id, payload={"reason": "Not this client's file"})
    held = [m for m in build_thread(db, world["borrower"].id)["messages"] if m["type"] == "held"]
    assert held and held[0]["reason"] == "Not this client's file"


def test_another_clients_records_never_appear(db, world):
    _item(db, world["other"], title="Zinc item")
    _doc(db, world["other"])
    assert build_thread(db, world["borrower"].id)["messages"] == []


def test_copilot_exchange_becomes_a_qa_message_for_that_client_only(db, world):
    run_id = uuid.uuid4()
    for borrower, text in ((world["borrower"], "What is cash?"), (world["other"], "What is zinc?")):
        ledger.record(db, actor_type="user", actor_id=world["analyst"].id, action="copilot.asked",
                      entity_type="agent_run", entity_id=run_id if borrower is world["borrower"] else uuid.uuid4(),
                      payload={"question": text, "borrower_id": borrower.id, "status": "answered",
                               "answer_with_references": "Cash was {{fact:abc}}.", "fact_ids": ["abc"],
                               "citations": [{"document_id": "d1", "page": 3}]})
    qa = [m for m in build_thread(db, world["borrower"].id)["messages"] if m["type"] == "qa"]
    assert len(qa) == 1 and qa[0]["question"] == "What is cash?" and qa[0]["fact_ids"] == ["abc"]
    assert qa[0]["asked_by"] == "Priya Raman"


def test_thread_endpoint_requires_sign_in_and_404s_an_unknown_client(db, client, world):
    assert client.get(f"/api/v1/threads/{world['borrower'].id}").status_code == 401
    sign_in(client, "priya.raman")
    assert client.get(f"/api/v1/threads/{uuid.uuid4()}").status_code == 404
    body = client.get(f"/api/v1/threads/{world['borrower'].id}").json()
    assert body["messages"] == [] and body["borrower"]["name"] == "Quillfeather Labs, Inc."


def test_sort_key_tolerates_a_missing_timestamp():
    from app.squad.threads import _sort_key

    msgs = [{"id": "b", "type": "case", "ts": "2026-11-20T10:00:00+00:00"}, {"id": "a", "type": "case", "ts": ""},
            {"id": "c", "type": "case"}]
    assert [m["id"] for m in sorted(msgs, key=_sort_key)] == ["a", "c", "b"]


def test_a_decided_question_is_an_ask_with_its_choice_and_no_duplicate_decision(db, world):
    item = raise_item(db, borrower_id=world["borrower"].id, item_type="question", title="Which entity?",
                      question="Which entity filed this?", allowed_decisions=["a", "b"],
                      evidence={"options": [{"id": "a", "label": "Parent"}, {"id": "b", "label": "Sub"}]})
    workflow.decide_work_item(db, item, user_id=world["analyst"].id, user_role="analyst", decision="a")
    msgs = build_thread(db, world["borrower"].id)["messages"]
    assert [m["type"] for m in msgs] == ["ask"]
    assert msgs[0]["choice"] == "Parent" and msgs[0]["chosen_by"] == "Priya Raman"


def _breach(db, borrower):
    return raise_item(db, borrower_id=borrower.id, item_type="covenant.breach", title="Cash below minimum",
                      severity="critical", question="Is this a breach?",
                      allowed_decisions=["waiver_requested", "not_a_breach"], required_permission="decide_breach")


def _case(db, user, borrower_id):
    return next(m for m in build_thread(db, borrower_id, user)["messages"] if m["type"] == "case")


def test_a_case_says_per_viewer_whether_it_needs_them(db, world):
    _breach(db, world["borrower"])
    officer = _case(db, world["officer"], world["borrower"].id)
    analyst = _case(db, world["analyst"], world["borrower"].id)
    assert officer["needs_you"] is True
    assert analyst["needs_you"] is False and analyst["state_words"] == "With the credit officer"
    assert _case(db, None, world["borrower"].id)["needs_you"] is False


def test_a_case_the_viewer_prepared_that_needs_a_second_person_is_not_theirs(db, world):
    item = _breach(db, world["borrower"])
    item.requires_second_person = True
    item.prepared_by_id = str(world["officer"].id)
    db.flush()
    assert _case(db, world["officer"], world["borrower"].id)["needs_you"] is False


def test_a_case_with_no_one_special_reads_open(db, world):
    _item(db, world["borrower"])
    assert _case(db, world["admin"], world["borrower"].id)["state_words"] == "Open"


def test_the_thread_route_sends_needs_you_for_the_signed_in_viewer(db, client, world):
    _breach(db, world["borrower"])
    db.commit()
    url = f"/api/v1/threads/{world['borrower'].id}"
    sign_in(client, "helen.strand")
    assert [m["needs_you"] for m in client.get(url).json()["messages"] if m["type"] == "case"] == [True]
    sign_in(client, "priya.raman")
    assert [m["needs_you"] for m in client.get(url).json()["messages"] if m["type"] == "case"] == [False]


def test_a_decision_message_carries_the_shared_past_tense_words(db, world):
    item = _breach(db, world["borrower"])
    workflow.decide_work_item(db, item, user_id=world["officer"].id, user_role="credit_officer", decision="not_a_breach", reason="Cash was reclassified.")
    decision = next(m for m in build_thread(db, world["borrower"].id)["messages"] if m["type"] == "decision")
    assert decision["decision"] == "not_a_breach" and decision["decision_words"] == "marked not a breach"
