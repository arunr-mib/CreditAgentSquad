"""The evaluation results as the governance screen reads them."""
import pytest
from app.api import routes_evals
from app.api.deps import current_user
from app.core.db import get_db
from app.domain.governance import EvalRun
from app.domain.org import User
from app.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

RESULTS = {"meta": {"suite": "monitoring-cycle", "mode": "standin", "standin": True, "borrowers": 21,
                    "generated_at": "2026-11-17T00:00:00+00:00", "commit": "abc"},
           "gate": {"passed": True, "reasons": []},
           "metrics": {"extraction_accuracy": 1.0, "input_tokens": None},
           "failure_counts": {"invented-number": 0, "false-compliant": 0}, "borrowers": {}}


@pytest.fixture()
def db(engine):
    conn = engine.connect()
    outer = conn.begin()
    session = Session(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
    yield session
    session.close()
    outer.rollback()
    conn.close()


@pytest.fixture()
def api(db):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        yield app, client


def sign_in(app):
    app.dependency_overrides[current_user] = lambda: User(email="r@x.example", name="Reviewer", role="credit_review",
                                                          password_hash="x")


def test_evaluation_routes_need_a_signed_in_user(api):
    _, client = api
    for path in ("/evals/latest", "/evals/runs"):
        assert client.get("/api/v1" + path).status_code == 401


def test_latest_comes_from_the_database_and_a_stand_in_run_says_so(api, db):
    app, client = api
    sign_in(app)
    db.add(EvalRun(suite="monitoring-cycle", mode="standin", commit="abc", results=RESULTS, gate_passed=True))
    db.flush()
    body = client.get("/api/v1/evals/latest").json()
    assert body["source"] == "database" and body["mode"] == "standin" and body["standin"] is True
    assert "not model performance" in body["notice"] and body["gate_passed"] is True
    assert body["results"]["metrics"]["input_tokens"] is None  # unmeasured stays null
    runs = client.get("/api/v1/evals/runs").json()
    assert len(runs) == 1 and runs[0]["borrowers"] == 21 and "results" not in runs[0]
    assert client.get(f"/api/v1/evals/runs/{runs[0]['id']}").json()["results"]["meta"]["commit"] == "abc"
    assert client.get("/api/v1/evals/runs/not-an-id").status_code == 404


def test_a_real_model_run_carries_no_stand_in_notice(api, db):
    app, client = api
    sign_in(app)
    db.add(EvalRun(suite="monitoring-cycle", mode="recorded", results={**RESULTS, "meta": {**RESULTS["meta"], "mode": "recorded"}},
                   gate_passed=False))
    db.flush()
    body = client.get("/api/v1/evals/latest").json()
    assert body["standin"] is False and body["notice"] is None and body["gate_passed"] is False


def test_latest_falls_back_to_the_results_file_and_is_404_when_nothing_has_run(api, db, tmp_path, monkeypatch):
    import json

    app, client = api
    sign_in(app)
    monkeypatch.setattr(routes_evals, "RESULTS_FILE", tmp_path / "latest.json")
    assert client.get("/api/v1/evals/latest").status_code == 404
    (tmp_path / "latest.json").write_text(json.dumps(RESULTS))
    body = client.get("/api/v1/evals/latest").json()
    assert body["source"] == "file" and body["id"] is None and body["standin"] is True
    assert client.get("/api/v1/evals/latest", params={"suite": "other"}).status_code == 404
