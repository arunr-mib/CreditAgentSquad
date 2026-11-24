import pytest
from app.domain.credit import Borrower
from app.domain.org import User
from app.seed_users import seed_users
from sqlalchemy import select

PASSWORD = "pw"


def sign_in(client, who: str):
    r = client.post("/api/v1/auth/login", json={"email": f"{who}@bankofstoic.example", "password": PASSWORD})
    assert r.status_code == 200, r.text


def _user(db, email_start: str) -> User:
    return db.execute(select(User).where(User.email.like(f"{email_start}@%"))).scalar_one()


@pytest.fixture()
def world(db):
    seed_users(db, password=PASSWORD)
    analyst = _user(db, "priya.raman")
    # both clients are Priya's: an analyst acts only on her own clients, and a client with no analyst is no
    # analyst's (owner answer 9, 22 Nov)
    borrower = Borrower(code="QFL", name="Quillfeather Labs, Inc.", template_id="vc-1", analyst_id=analyst.id)
    other = Borrower(code="ZZZ", name="Zephyr Zinc Works, Inc.", analyst_id=analyst.id)
    db.add_all([borrower, other])
    db.flush()
    return {"analyst": analyst, "officer": _user(db, "helen.strand"),
            "admin": _user(db, "admin"), "borrower": borrower, "other": other}
