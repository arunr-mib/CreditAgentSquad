"""Upload size, the session cookie, sign-in lockout and the API documentation routes."""
from datetime import UTC, datetime, timedelta

import pytest
from app.api import auth
from app.core import config
from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.ledger import LedgerEvent
from app.domain.credit import Borrower
from app.main import create_app
from app.seed_users import seed_users
from fastapi.testclient import TestClient
from sqlalchemy import select

API = "/api/v1"
PRIYA, DANA = "priya.raman@bankofstoic.example", "dana.whitfield@bankofstoic.example"


@pytest.fixture()
def users(db, tmp_path, monkeypatch):
    monkeypatch.setenv("FILE_STORE_DIR", str(tmp_path))
    get_settings.cache_clear()
    seed_users(db, password="pw-for-tests")
    yield
    get_settings.cache_clear()


def login(client, email=PRIYA, password="pw-for-tests"):
    return client.post(f"{API}/auth/login", json={"email": email, "password": password})


def actions(db, prefix="auth."):
    return [e.action for e in db.execute(select(LedgerEvent).where(LedgerEvent.action.like(prefix + "%"))
                                         .order_by(LedgerEvent.seq)).scalars()]


def app_in(db, monkeypatch, env: str | None):
    """The app as it starts with SQUAD_ENV set to `env`, or not set at all."""
    if env is None:
        monkeypatch.delenv("SQUAD_ENV", raising=False)
    else:
        monkeypatch.setenv("SQUAD_ENV", env)
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    return app


# ---- upload size ------------------------------------------------------------------------------


def test_an_upload_over_the_limit_is_refused_and_nothing_is_stored(client, db, users):
    assert config.MAX_UPLOAD_BYTES == 25 * 1024 * 1024
    borrower = Borrower(code="HTD", name="Harrowgate Tool & Die, Inc.")
    db.add(borrower)
    db.flush()
    assert login(client).status_code == 200
    url = f"{API}/borrowers/{borrower.id}/documents"
    too_big = b"%PDF-1.7\n" + b"0" * config.MAX_UPLOAD_BYTES  # nine bytes over
    refused = client.post(url, files={"file": ("big.pdf", too_big)})
    assert refused.status_code == 413 and "25 MB" in refused.json()["detail"]
    assert client.get(f"{API}/borrowers/{borrower.id}/documents").json() == []
    assert "document.received" not in actions(db, "document.")


def test_a_request_that_declares_an_oversized_body_is_refused_before_it_is_read(client, users):
    declared = str(config.MAX_UPLOAD_BYTES * 4)
    refused = client.post(f"{API}/borrowers/00000000-0000-4000-8000-000000000000/documents", content=b"x",
                          headers={"Content-Length": declared, "Content-Type": "multipart/form-data; boundary=x"})
    assert refused.status_code == 413 and "25 MB" in refused.json()["detail"]


# ---- session cookie -----------------------------------------------------------------------------


def test_settings_fail_safe_when_the_environment_is_not_named(monkeypatch):
    monkeypatch.delenv("SQUAD_ENV", raising=False)
    unset = Settings(_env_file=None)
    assert unset.cookie_secure is True and unset.serve_api_docs is False
    local = Settings(_env_file=None, squad_env="local")
    assert local.cookie_secure is False and local.serve_api_docs is True
    assert Settings(_env_file=None, squad_env="local", session_cookie_secure=True).cookie_secure is True
    assert Settings(_env_file=None, api_docs_enabled=True).serve_api_docs is True


@pytest.mark.parametrize("env, secure", [(None, True), ("production", True), ("local", False)])
def test_the_session_cookie_is_https_only_outside_local_development(db, users, monkeypatch, env, secure):
    with TestClient(app_in(db, monkeypatch, env)) as client:
        cookie = login(client).headers["set-cookie"].lower()
    assert ("secure" in [part.strip() for part in cookie.split(";")]) is secure
    assert "httponly" in cookie and "samesite=lax" in cookie


# ---- sign-in lockout ----------------------------------------------------------------------------


def test_five_failures_lock_the_account_and_the_lock_is_on_the_ledger(client, db, users, monkeypatch):
    for _ in range(5):
        assert login(client, password="wrong").status_code == 401
    locked = login(client)  # the right password, but the account is locked
    assert locked.status_code == 429 and int(locked.headers["retry-after"]) > 0
    assert login(client, password="wrong").status_code == 429
    assert actions(db) == ["auth.sign_in_failed"] * 5 + ["auth.locked_out"]  # refused attempts add nothing
    assert login(client, email=DANA).status_code == 200  # another account is not affected
    # sixteen minutes later the failures are outside the window
    later = datetime.now(UTC) + timedelta(minutes=16)
    monkeypatch.setattr(auth, "_now", lambda: later)
    assert login(client).status_code == 200


def test_a_successful_sign_in_clears_the_count_and_unknown_accounts_are_not_recorded(client, db, users):
    for _ in range(4):
        assert login(client, password="wrong").status_code == 401
    assert login(client).status_code == 200
    for _ in range(4):
        assert login(client, password="wrong").status_code == 401
    assert login(client).status_code == 200  # eight failures in all, never five in a row
    before = len(actions(db))
    assert login(client, email="nobody@bankofstoic.example", password="x").status_code == 401
    assert len(actions(db)) == before and "auth.locked_out" not in actions(db)


# ---- API documentation --------------------------------------------------------------------------


@pytest.mark.parametrize("env, status", [(None, 404), ("production", 404), ("local", 200)])
def test_api_documentation_is_served_only_where_a_setting_allows_it(db, monkeypatch, env, status):
    with TestClient(app_in(db, monkeypatch, env)) as client:
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert client.get(path).status_code == status, path
        assert client.get(f"{API}/health").status_code == 200
    get_settings.cache_clear()


def test_api_documentation_can_be_switched_on_by_its_own_setting(db, monkeypatch):
    monkeypatch.setenv("API_DOCS_ENABLED", "true")
    with TestClient(app_in(db, monkeypatch, "production")) as client:
        assert client.get("/openapi.json").status_code == 200
    get_settings.cache_clear()
