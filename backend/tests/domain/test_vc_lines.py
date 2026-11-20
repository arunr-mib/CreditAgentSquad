"""The line index follows the borrower's own template outside spreading too."""
from datetime import date
from decimal import Decimal as D

import pytest
from app.domain import corrections
from app.domain.credit import Borrower
from app.domain.facts_service import add_fact, current_fact
from app.domain.org import User
from app.publishing.content import Registry, _spread
from app.seed_users import seed_users
from sqlalchemy import select

END = date(2026, 9, 30)


@pytest.fixture()
def vc(db):
    b = Borrower(code="VCL", name="Quillfeather Labs, Inc.", template_id="vc-1")
    db.add(b)
    db.flush()
    return b


def _user(db) -> User:
    seed_users(db, password="pw")
    return db.execute(select(User).where(User.email == "priya.raman@bankofstoic.example")).scalar_one()


def _revenue(db, b):
    return add_fact(db, borrower_id=b.id, key="is.subscription_revenue", period_end=END, months=9,
                    value=D("1000000"), kind="seeded")


def test_correction_on_a_vc_line_succeeds(db, vc):
    user = _user(db)
    fact = _revenue(db, vc)
    new, _ = corrections.correct(db, fact, value=D("1100000"), user_id=user.id, reason="restated")
    assert current_fact(db, vc.id, "is.subscription_revenue", END, 9).id == new.id


def test_entering_a_ci_line_on_a_vc_borrower_is_refused(db, vc):
    user = _user(db)
    with pytest.raises(ValueError, match="template"):
        corrections.enter(db, borrower_id=vc.id, key="is.revenue", period_end=END, months=9, value=D(5),
                          user_id=user.id, reason="typo")


def test_manual_entry_route_follows_the_borrowers_template(client, db, vc):
    seed_users(db, password="pw")
    client.post("/api/v1/auth/login", json={"email": "priya.raman@bankofstoic.example", "password": "pw"})
    url = f"/api/v1/borrowers/{vc.id}/facts"
    body = {"period_end": "2026-09-30", "months": 9, "value": "5", "reason": "keyed"}
    assert client.post(url, json={**body, "key": "is.revenue"}).status_code == 422
    assert client.post(url, json={**body, "key": "is.subscription_revenue"}).status_code == 201


def test_spread_view_lists_the_vc_lines(client, db, vc):
    seed_users(db, password="pw")
    client.post("/api/v1/auth/login", json={"email": "priya.raman@bankofstoic.example", "password": "pw"})
    _revenue(db, vc)
    body = client.get(f"/api/v1/borrowers/{vc.id}/spread").json()
    keys = [line["key"] for line in body["lines"]]
    assert body["template"] == "vc-1" and "is.subscription_revenue" in keys and "is.revenue" not in keys
    cells = {line["key"]: line["cells"] for line in body["lines"]}
    assert cells["is.subscription_revenue"]


def test_publishing_spread_for_a_vc_borrower(db, vc):
    _revenue(db, vc)
    out = _spread(db, Registry(db), vc, END)
    assert out["template"] == "vc-1" and "is.subscription_revenue" in out["cells"]
