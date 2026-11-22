"""Final review group F: bounded inputs on the new endpoints, raw run records for Oversight roles only, and a
seq-only ledger heartbeat."""
from datetime import UTC, datetime

import pytest
from app.core import ledger
from app.domain.agents import AgentRun
from app.domain.credit import Borrower
from app.domain.work_items import raise_item
from app.seed_users import seed_users


def sign_in(client, who):
    r = client.post("/api/v1/auth/login", json={"email": f"{who}@bankofstoic.example", "password": "pw"})
    assert r.status_code == 200, r.text


@pytest.fixture()
def world(db):
    seed_users(db, password="pw")
    b = Borrower(code="BND", name="Boundary Works, Inc.")
    db.add(b)
    db.flush()
    run = AgentRun(agent_name="covenant", agent_version="1", model="m", task="t", borrower_id=b.id, scope={},
                   status="completed", raw_output={"text": "Revenue was 4,200,000."}, finished_at=datetime.now(UTC))
    db.add(run)
    item = raise_item(db, borrower_id=b.id, item_type="test.routed_case", title="Cash below minimum",
                      question="How should the bank respond?", allowed_decisions=["no_action"])
    db.commit()
    return b, run, item


def test_a_return_with_more_than_five_needs_is_refused_before_it_is_parsed(client, world):
    _, _, item = world
    sign_in(client, "helen.strand")
    needs = [{"doc_type": "bank_statement", "period_end": "2026-09-30"}] * 6
    r = client.post(f"/api/v1/work-items/{item.id}/return", json={"reason": "x", "needs": needs})
    assert r.status_code == 422 and isinstance(r.json()["detail"], list)  # the request model, not the engine


def test_an_answer_note_is_bounded(client, world):
    _, _, item = world
    sign_in(client, "priya.raman")
    r = client.post(f"/api/v1/work-items/{item.id}/answer", json={"option_id": "x", "note": "a" * 4001})
    assert r.status_code == 422 and isinstance(r.json()["detail"], list)


def test_the_oversight_runs_offset_is_bounded(client, world):
    sign_in(client, "ruth.calloway")
    assert client.get("/api/v1/oversight/runs", params={"offset": 10**6 + 1}).status_code == 422
    assert client.get("/api/v1/oversight/runs", params={"offset": -1}).status_code == 422
    assert client.get("/api/v1/oversight/runs", params={"offset": 0}).status_code == 200


def test_the_raw_run_record_is_for_oversight_roles_and_the_words_view_for_everyone(client, world):
    _, run, _ = world
    sign_in(client, "priya.raman")
    assert client.get("/api/v1/agent-runs").status_code == 403
    assert client.get(f"/api/v1/agent-runs/{run.id}").status_code == 403
    words = client.get(f"/api/v1/runs/{run.id}")
    assert words.status_code == 200 and "raw_output" not in words.json()
    sign_in(client, "ruth.calloway")
    assert client.get("/api/v1/agent-runs").status_code == 200
    assert client.get(f"/api/v1/agent-runs/{run.id}").json()["raw_output"] == {"text": "Revenue was 4,200,000."}


def test_the_heartbeat_reads_only_the_ledgers_latest_sequence(client, db, world):
    sign_in(client, "priya.raman")
    head = ledger.head(db)
    body = client.get("/api/v1/ledger/head").json()
    assert body == {"seq": head[0] if head else 0}
