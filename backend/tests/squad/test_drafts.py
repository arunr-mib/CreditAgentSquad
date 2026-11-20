# backend/tests/squad/test_drafts.py
import uuid

import pytest
from app.core.ledger import LedgerEvent
from app.squad.drafts import create_draft, drafts_for, edit_draft, send_draft
from app.squad.threads import build_thread
from sqlalchemy import select

from .conftest import sign_in


def _draft(db, borrower):
    return create_draft(db, borrower_id=borrower.id, to="cfo@quillfeather.example", subject="October MRR",
                        body="Hi Priya, could you send the October MRR report?", kind="reminder")


def test_a_new_draft_is_unsent_and_written_by_squad(db, world):
    d = _draft(db, world["borrower"])
    assert d["status"] == "draft" and d["created_by"] == "Squad" and d["sent_by"] is None


def test_editing_changes_the_body_and_keeps_the_history_on_the_ledger(db, world):
    d = _draft(db, world["borrower"])
    edit_draft(db, uuid.UUID(d["draft_id"]), world["analyst"], body="Hi Priya, October MRR please.")
    [now] = drafts_for(db, world["borrower"].id)
    assert now["body"] == "Hi Priya, October MRR please." and now["edited_by"] == "Priya Raman"
    actions = [e.action for e in db.execute(select(LedgerEvent).where(LedgerEvent.entity_type == "draft").order_by(LedgerEvent.seq)).scalars()]
    assert actions == ["draft.created", "draft.edited"]


def test_send_records_the_person_and_claims_no_delivery(db, world):
    d = _draft(db, world["borrower"])
    sent = send_draft(db, uuid.UUID(d["draft_id"]), world["analyst"])
    assert sent["status"] == "sent" and sent["sent_by"] == "Priya Raman"
    event = db.execute(select(LedgerEvent).where(LedgerEvent.action == "draft.sent")).scalars().one()
    assert event.actor_type == "user" and event.payload["delivery"] == "recorded_only"


def test_a_sent_draft_cannot_be_edited_or_sent_again(db, world):
    d = _draft(db, world["borrower"])
    send_draft(db, uuid.UUID(d["draft_id"]), world["analyst"])
    with pytest.raises(ValueError):
        edit_draft(db, uuid.UUID(d["draft_id"]), world["analyst"], body="late change")
    with pytest.raises(ValueError):
        send_draft(db, uuid.UUID(d["draft_id"]), world["analyst"])


def test_an_empty_body_cannot_be_sent(db, world):
    d = _draft(db, world["borrower"])
    edit_draft(db, uuid.UUID(d["draft_id"]), world["analyst"], body="   ")
    with pytest.raises(ValueError):
        send_draft(db, uuid.UUID(d["draft_id"]), world["analyst"])


def test_drafts_are_per_client_and_appear_in_the_thread(db, world):
    _draft(db, world["borrower"])
    assert drafts_for(db, world["other"].id) == []
    message = [m for m in build_thread(db, world["borrower"].id)["messages"] if m["type"] == "draft"]
    assert len(message) == 1 and message[0]["subject"] == "October MRR"


def test_unknown_draft_is_a_lookup_error(db, world):
    with pytest.raises(LookupError):
        send_draft(db, uuid.uuid4(), world["analyst"])


def test_endpoints_enforce_the_permission_and_never_deliver(db, client, world):
    d = _draft(db, world["borrower"])
    db.commit()
    sign_in(client, "helen.strand")  # an officer may not send client email
    assert client.post(f"/api/v1/drafts/{d['draft_id']}/send").status_code == 403
    sign_in(client, "priya.raman")
    r = client.post(f"/api/v1/drafts/{d['draft_id']}/send")
    assert r.status_code == 200 and r.json()["delivered"] is False
    assert client.post(f"/api/v1/drafts/{d['draft_id']}/send").status_code == 422
    assert client.post(f"/api/v1/drafts/{uuid.uuid4()}/send").status_code == 404
    created = client.post(f"/api/v1/borrowers/{world['borrower'].id}/drafts",
                          json={"to": "a@b.example", "subject": "s", "body": "b"})
    assert created.status_code == 201 and created.json()["created_by"] == "Priya Raman"


def _sent_elsewhere(db, d, who):
    """What another session committing while we waited for the lock leaves behind."""
    from app.core import ledger
    ledger.record(db, actor_type="user", actor_id=who.id, action="draft.sent", entity_type="draft",
                  entity_id=d["draft_id"], payload={"borrower_id": d["borrower_id"], "delivery": "recorded_only"})


def test_send_and_edit_take_the_lock_before_reading_so_a_concurrent_send_is_seen(db, world, monkeypatch):
    from app.core import ledger
    d = _draft(db, world["borrower"])
    real = ledger.lock

    def lock_then_other_session_wins(session):
        real(session)
        monkeypatch.setattr("app.squad.drafts.ledger.lock", real)  # inject once
        _sent_elsewhere(db, d, world["officer"])

    monkeypatch.setattr("app.squad.drafts.ledger.lock", lock_then_other_session_wins)
    with pytest.raises(ValueError):
        send_draft(db, uuid.UUID(d["draft_id"]), world["analyst"])
    with pytest.raises(ValueError):
        edit_draft(db, uuid.UUID(d["draft_id"]), world["analyst"], body="late")
    assert len(db.execute(select(LedgerEvent).where(LedgerEvent.action == "draft.sent")).scalars().all()) == 1


def test_events_after_the_first_send_are_ignored_by_the_fold(db, world):
    from app.core import ledger
    d = _draft(db, world["borrower"])
    send_draft(db, uuid.UUID(d["draft_id"]), world["analyst"])
    ledger.record(db, actor_type="user", actor_id=world["officer"].id, action="draft.edited", entity_type="draft",
                  entity_id=d["draft_id"], payload={"borrower_id": d["borrower_id"], "body": "rewritten after send"})
    _sent_elsewhere(db, d, world["officer"])
    [now] = drafts_for(db, world["borrower"].id)
    assert now["body"] == d["body"] and now["sent_by"] == "Priya Raman" and now["edited_by"] is None


def test_an_empty_subject_cannot_be_set_on_edit(db, world):
    d = _draft(db, world["borrower"])
    with pytest.raises(ValueError):
        edit_draft(db, uuid.UUID(d["draft_id"]), world["analyst"], subject="  ")


def test_a_draft_may_only_cite_a_work_item_of_the_same_client(db, world):
    from app.domain.work_items import raise_item
    mine = raise_item(db, borrower_id=world["borrower"].id, item_type="funding_slipped", title="t",
                      question="Review it?", allowed_decisions=["reviewed"])
    theirs = raise_item(db, borrower_id=world["other"].id, item_type="funding_slipped", title="t",
                        question="Review it?", allowed_decisions=["reviewed"])
    ok = create_draft(db, borrower_id=world["borrower"].id, to="a@b.example", subject="s", body="b", work_item_id=mine.id)
    assert ok["work_item_id"] == str(mine.id)
    for bad in (theirs.id, uuid.uuid4()):
        with pytest.raises(ValueError):
            create_draft(db, borrower_id=world["borrower"].id, to="a@b.example", subject="s", body="b", work_item_id=bad)
