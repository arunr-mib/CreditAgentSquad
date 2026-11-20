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
