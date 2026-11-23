"""Borrower template and funding events."""
from datetime import date
from decimal import Decimal as D

import pytest
from app.core.ledger import LedgerEvent
from app.domain.credit import Borrower
from app.domain.funding import FundingEvent, check_funding_events
from app.domain.monitoring import WorkItem
from app.domain.org import User
from app.seed_users import seed_users
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError


def make_borrower(db, code="VCO", **kw) -> Borrower:
    b = Borrower(code=code, name="Quillfeather Labs, Inc.", **kw)
    db.add(b)
    db.flush()
    db.refresh(b)
    return b


def test_new_borrowers_default_to_ci_template(db):
    assert make_borrower(db).template_id == "ci-1"


def test_template_must_be_known(db):
    with pytest.raises(IntegrityError):
        make_borrower(db, code="BAD", template_id="xx-9")


def test_slipped_funding_raises_one_work_item(db):
    b = make_borrower(db, template_id="vc-1")
    db.add(FundingEvent(borrower_id=b.id, kind="extension", amount=D("8000000"),
                        expected_close=date(2026, 12, 12), status="signed"))
    db.flush()
    assert check_funding_events(db, date(2026, 12, 10)) == []
    slipped = check_funding_events(db, date(2026, 12, 13))
    assert [e.status for e in slipped] == ["slipped"]
    assert check_funding_events(db, date(2026, 12, 14)) == []  # not raised twice
    items = db.execute(select(WorkItem).where(WorkItem.item_type == "funding_slipped")).scalars().all()
    assert len(items) == 1 and items[0].severity == "high" and items[0].borrower_id == b.id
    actions = db.execute(select(LedgerEvent.action).where(LedgerEvent.action == "funding_event.slipped")).all()
    assert len(actions) == 1


def test_closed_events_never_slip(db):
    b = make_borrower(db)
    db.add(FundingEvent(borrower_id=b.id, kind="equity_round", amount=D("1"),
                        expected_close=date(2026, 1, 1), status="closed"))
    db.flush()
    assert check_funding_events(db, date(2026, 12, 1)) == []


def _sign_in(client, who):
    r = client.post("/api/v1/auth/login", json={"email": f"{who}@bankofstoic.example", "password": "pw"})
    assert r.status_code == 200, r.text


def test_funding_event_api(client, db):
    seed_users(db, password="pw")
    b = make_borrower(db, template_id="vc-1")
    url = f"/api/v1/borrowers/{b.id}/funding-events"
    body = {"kind": "equity_round", "amount": "12000000.50", "expected_close": "2027-01-31"}
    assert client.get(url).status_code == 401
    _sign_in(client, "ruth.calloway")  # view only
    assert client.get(url).json() == []
    assert client.post(url, json=body).status_code == 403
    _sign_in(client, "priya.raman")
    created = client.post(url, json=body)
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "expected" and created.json()["amount"] == "12000000.5"
    assert client.post(url, json={**body, "kind": "grant"}).status_code == 422
    assert len(client.get(url).json()) == 1
    assert db.execute(select(LedgerEvent).where(LedgerEvent.action == "funding_event.recorded")).first()
    assert client.get("/api/v1/borrowers/00000000-0000-4000-8000-000000000000/funding-events").status_code == 404


def _slipped_item(db):
    b = make_borrower(db, template_id="vc-1")
    db.add(FundingEvent(borrower_id=b.id, kind="equity_round", amount=D("8000000"),
                        expected_close=date(2026, 12, 12), status="expected"))
    db.flush()
    check_funding_events(db, date(2026, 12, 13))
    return db.execute(select(WorkItem).where(WorkItem.item_type == "funding_slipped",
                                             WorkItem.borrower_id == b.id)).scalar_one()


def test_the_slipped_item_offers_four_responses_in_order(db):
    item = _slipped_item(db)
    assert item.allowed_decisions == ["ask_for_new_timeline", "note_and_watch", "reserve_rights", "escalate"]
    assert "Squad drafts the email for you to send" in item.question
    assert "has not closed. What should we do:" in item.question


@pytest.mark.parametrize("role,decision,reason", [
    ("analyst", "ask_for_new_timeline", ""), ("analyst", "note_and_watch", ""),
    ("credit_officer", "reserve_rights", "rights reserved under the loan agreement"),
    ("credit_officer", "escalate", "needs the credit officer")])
def test_each_response_can_be_recorded_by_the_right_role_and_closes_the_item(db, role, decision, reason):
    from app.domain import workflow
    seed_users(db, password="pw")
    person = db.execute(select(User).where(User.role == role)).scalars().first()
    item = _slipped_item(db)
    from app.domain.credit import Borrower
    db.get(Borrower, item.borrower_id).analyst_id = person.id if role == "analyst" else None  # the test's analyst owns the test's client: an analyst acts only on her own clients (owner answer 9)
    workflow.decide_work_item(db, item, user_id=person.id, user_role=person.role, decision=decision, reason=reason)
    assert item.status == "decided" and item.decision == decision


@pytest.mark.parametrize("decision", ["reserve_rights", "escalate"])
def test_an_analyst_cannot_reserve_rights_or_escalate_a_slipped_round(db, decision):
    from app.domain import workflow
    seed_users(db, password="pw")
    analyst = db.execute(select(User).where(User.role == "analyst")).scalars().first()
    item = _slipped_item(db)
    with pytest.raises(PermissionError, match="decide_breach"):
        workflow.decide_work_item(db, item, user_id=analyst.id, user_role=analyst.role, decision=decision,
                                  reason="a reason")
    assert item.status == "open"


def test_reserving_rights_and_escalating_need_a_reason(db):
    from app.domain import workflow
    seed_users(db, password="pw")
    officer = db.execute(select(User).where(User.role == "credit_officer")).scalars().first()
    for decision in ("reserve_rights", "escalate"):
        with pytest.raises(ValueError, match="reason"):
            workflow.decide_work_item(db, _slipped_item_for(db, decision), user_id=officer.id,
                                      user_role=officer.role, decision=decision)


def _slipped_item_for(db, code):
    b = make_borrower(db, code=f"S-{code}"[:12], template_id="vc-1")
    db.add(FundingEvent(borrower_id=b.id, kind="equity_round", amount=D("1"),
                        expected_close=date(2026, 12, 12), status="expected"))
    db.flush()
    check_funding_events(db, date(2026, 12, 13))
    return db.execute(select(WorkItem).where(WorkItem.item_type == "funding_slipped",
                                             WorkItem.borrower_id == b.id)).scalar_one()


# ---- lifecycle: PATCH /borrowers/{id}/funding-events/{event_id} ---------------------------------

def _doc(db, borrower, name="term-sheet.pdf"):
    from app.domain.documents import Document
    d = Document(borrower_id=borrower.id, title=name, file_name=name, storage_path=name, sha256=name.ljust(64, "0"),
                 page_count=1)
    db.add(d)
    db.flush()
    return d


@pytest.fixture()
def lifecycle(client, db):
    seed_users(db, password="pw")
    b = make_borrower(db, template_id="vc-1")
    event = FundingEvent(borrower_id=b.id, kind="equity_round", amount=D("5000000"),
                         expected_close=date(2027, 1, 31), status="expected")
    db.add(event)
    db.flush()
    db.commit()
    _sign_in(client, "priya.raman")
    return b, event, f"/api/v1/borrowers/{b.id}/funding-events/{event.id}"


@pytest.mark.parametrize("path", [
    ["signed", "closed"], ["slipped", "expected", "signed", "slipped", "signed", "closed"], ["closed"],
    ["signed", "slipped", "closed"]])
def test_legal_status_transitions(client, lifecycle, path):
    _, _, url = lifecycle
    previous = "expected"
    for status in path:
        body = {"status": status}
        if previous == "slipped" and status in ("expected", "signed"):
            body["expected_close"] = "2099-12-31"  # reviving a slipped round needs a new timeline
        r = client.patch(url, json=body)
        assert r.status_code == 200 and r.json()["status"] == status, r.text
        previous = status


@pytest.mark.parametrize("start,target", [
    ("expected", "expected"), ("signed", "expected"), ("closed", "signed"), ("closed", "slipped"),
    ("closed", "expected"), ("expected", "open")])
def test_illegal_status_transitions_are_refused(client, db, lifecycle, start, target):
    _, event, url = lifecycle
    if start != "expected":
        path = {"signed": ["signed"], "closed": ["closed"]}[start]
        for status in path:
            assert client.patch(url, json={"status": status}).status_code == 200
    r = client.patch(url, json={"status": target})
    assert r.status_code == 422, r.text
    assert client.get(url.rsplit("/", 1)[0]).json()[0]["status"] == start


def test_a_new_timeline_changes_the_close_date_and_the_ledger_keeps_before_and_after(client, db, lifecycle):
    _, event, url = lifecycle
    assert client.patch(url, json={"status": "slipped"}).status_code == 200
    r = client.patch(url, json={"status": "expected", "expected_close": "2027-03-31"})
    assert r.status_code == 200 and r.json()["expected_close"] == "2027-03-31"
    last = db.execute(select(LedgerEvent).where(LedgerEvent.action == "funding_event.updated")
                      .order_by(LedgerEvent.seq.desc())).scalars().first()
    assert last.payload["before"]["status"] == "slipped" and last.payload["after"]["status"] == "expected"
    assert last.payload["before"]["expected_close"] == "2027-01-31"
    assert last.payload["after"]["expected_close"] == "2027-03-31"


def test_evidence_documents_are_appended_and_must_belong_to_the_borrower(client, db, lifecycle):
    b, event, url = lifecycle
    mine = _doc(db, b)
    other = _doc(db, make_borrower(db, code="OTH"), "other.pdf")
    db.commit()
    r = client.patch(url, json={"evidence_document_ids": [str(mine.id)]})
    assert r.status_code == 200 and r.json()["evidence_document_ids"] == [str(mine.id)]
    r = client.patch(url, json={"evidence_document_ids": [str(mine.id)]})  # not added twice
    assert r.json()["evidence_document_ids"] == [str(mine.id)]
    assert client.patch(url, json={"evidence_document_ids": [str(other.id)]}).status_code == 422
    assert client.patch(url, json={"evidence_document_ids": ["not-a-uuid"]}).status_code == 422
    assert client.patch(url, json={"evidence_document_ids": ["00000000-0000-4000-8000-000000000000"]}).status_code == 422
    assert client.patch(url, json={}).status_code == 422


def test_posting_an_event_validates_evidence_too(client, db, lifecycle):
    b, _, url = lifecycle
    base = url.rsplit("/", 1)[0]
    other = _doc(db, make_borrower(db, code="OT2"), "other.pdf")
    db.commit()
    body = {"kind": "extension", "amount": "1000", "expected_close": "2027-02-28"}
    assert client.post(base, json={**body, "evidence_document_ids": [str(other.id)]}).status_code == 422
    mine = _doc(db, b)
    db.commit()
    r = client.post(base, json={**body, "evidence_document_ids": [str(mine.id)]})
    assert r.status_code == 201 and r.json()["evidence_document_ids"] == [str(mine.id)]


def test_patching_needs_the_prepare_permission_and_an_event_of_this_borrower(client, db, lifecycle):
    b, event, url = lifecycle
    other = make_borrower(db, code="OT3")
    db.commit()
    assert client.patch(f"/api/v1/borrowers/{other.id}/funding-events/{event.id}",
                        json={"status": "signed"}).status_code == 404
    _sign_in(client, "ruth.calloway")  # view only
    assert client.patch(url, json={"status": "signed"}).status_code == 403


@pytest.mark.parametrize("body", [{"status": "expected"}, {"status": "signed", "expected_close": "2020-01-31"}])
def test_a_slipped_round_comes_back_only_with_a_future_close(client, lifecycle, body):
    _, _, url = lifecycle
    assert client.patch(url, json={"status": "slipped"}).status_code == 200
    r = client.patch(url, json=body)
    assert r.status_code == 422 and "after today" in r.text
    assert client.get(url.rsplit("/", 1)[0]).json()[0]["status"] == "slipped"


def test_a_closed_event_cannot_be_edited(client, lifecycle):
    _, _, url = lifecycle
    assert client.patch(url, json={"status": "closed"}).status_code == 200
    r = client.patch(url, json={"expected_close": "2027-06-30"})
    assert r.status_code == 422 and "final" in r.text


def test_the_slipped_title_carries_no_figure_and_the_amount_stays_a_recorded_value(db):
    """Final review I3: a title is shown unsourced (home rows, Approvals, the thread, the ledger), so it names no
    figure. The amount is kept in the evidence as the funding event's stored value, shown with its source."""
    item = _slipped_item(db)
    assert item.title == "Expected equity round has slipped"
    assert not any(ch.isdigit() for ch in item.title + item.question.split("expected to close on")[0])
    assert item.evidence["amount"] == "8000000.00" and item.evidence["kind"] == "equity_round"
