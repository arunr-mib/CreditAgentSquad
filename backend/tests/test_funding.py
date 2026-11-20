"""Borrower template and funding events."""
from datetime import date
from decimal import Decimal as D

import pytest
from app.core.ledger import LedgerEvent
from app.domain.credit import Borrower
from app.domain.funding import FundingEvent, check_funding_events
from app.domain.monitoring import WorkItem
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
