from app.core.ledger import LedgerEvent
from app.seed_users import seed_users
from sqlalchemy import select


def test_health(client):
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_sign_in_me_and_sign_out(client, db):
    seed_users(db, password="pw-for-tests")
    assert client.get("/api/v1/auth/me").status_code == 401

    bad = client.post("/api/v1/auth/login", json={"email": "priya.raman@bankofstoic.example", "password": "no"})
    assert bad.status_code == 401

    ok = client.post("/api/v1/auth/login",
                     json={"email": "Priya.Raman@bankofstoic.example", "password": "pw-for-tests"})
    assert ok.status_code == 200
    body = ok.json()
    assert body["role"] == "analyst" and "confirm_spread" in body["permissions"]
    assert "approve_terms" not in body["permissions"]

    assert client.get("/api/v1/auth/me").json()["email"] == "priya.raman@bankofstoic.example"
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401

    actions = [e.action for e in db.execute(select(LedgerEvent).order_by(LedgerEvent.seq)).scalars()]
    assert actions.count("auth.signed_in") == 1 and actions.count("auth.signed_out") == 1
