"""An agent run as the workspace reads it: the scope as data, a step count that matches the
steps listed, and input tokens that include what was read from and written to the prompt cache."""
from datetime import UTC, date, datetime

import pytest
from app.domain.agents import AgentRun, AgentStep
from app.domain.credit import Borrower
from app.seed_users import seed_users


@pytest.fixture()
def run(db, client):
    seed_users(db, password="pw")
    borrower = Borrower(code="RUN-001", name="Run Borrower")
    db.add(borrower)
    db.flush()
    scope = {"borrower_id": str(borrower.id), "facility_id": None, "period_end": "2026-09-30", "months": 9,
             "cycle_id": None, "document_ids": []}
    r = AgentRun(agent_name="covenant", agent_version="1", model="m", task="t", borrower_id=borrower.id,
                 period_end=date(2026, 9, 30), scope=scope, status="completed", steps_count=1,
                 input_tokens=1300, output_tokens=150, cache_read_tokens=4000, finished_at=datetime.now(UTC))
    db.add(r)
    db.flush()
    usage = [{"input_tokens": 100, "cache_creation_input_tokens": 1000, "cache_read_input_tokens": 0,
              "output_tokens": 100},
             {"input_tokens": 200, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 4000,
              "output_tokens": 50}]
    db.add_all([
        AgentStep(run_id=r.id, n=1, kind="model", name="response", detail={"usage": usage[0]}),
        AgentStep(run_id=r.id, n=2, kind="tool", name="get_fact", detail={}),
        AgentStep(run_id=r.id, n=3, kind="model", name="response", detail={"usage": usage[1]}),
    ])
    db.flush()
    r = client.post("/api/v1/auth/login", json={"email": "priya.raman@bankofstoic.example", "password": "pw"})
    assert r.status_code == 200
    return db.query(AgentRun).filter(AgentRun.agent_name == "covenant").one(), borrower


def test_a_run_reads_as_data(client, run):
    row, borrower = run
    body = client.get(f"/api/v1/agent-runs/{row.id}").json()
    # only the fields code set, as a structured object: no "facility id None", no "document ids []"
    assert body["scope"] == {"borrower_id": str(borrower.id), "period_end": "2026-09-30", "months": 9}
    # the count is of the steps listed; the tool calls the step cap counts are given separately
    assert body["steps_count"] == len(body["steps"]) == 3
    assert body["tool_calls"] == 1
    # input includes what was read from the cache and what was written to it
    assert body["input_tokens"] == 100 + 1000 + 200 + 4000
    assert body["cache_read_tokens"] == 4000 and body["cache_creation_tokens"] == 1000
    assert body["output_tokens"] == 150


def test_the_list_counts_the_same_way(client, run):
    row, _ = run
    listed = next(r for r in client.get("/api/v1/agent-runs").json() if r["id"] == str(row.id))
    detail = client.get(f"/api/v1/agent-runs/{row.id}").json()
    for field in ("steps_count", "tool_calls", "input_tokens", "cache_read_tokens", "cache_creation_tokens",
                  "output_tokens", "scope"):
        assert listed[field] == detail[field], field


def test_a_run_without_step_usage_falls_back_to_its_totals(client, db, run):
    row, borrower = run
    bare = AgentRun(agent_name="intake", agent_version="1", model="m", task="t", borrower_id=borrower.id,
                    scope={}, status="running", input_tokens=500, output_tokens=20, cache_read_tokens=300)
    db.add(bare)
    db.flush()
    body = client.get(f"/api/v1/agent-runs/{bare.id}").json()
    assert body["scope"] == {} and body["steps_count"] == 0 and body["steps"] == []
    assert body["input_tokens"] == 800 and body["cache_read_tokens"] == 300
    assert body["cache_creation_tokens"] is None  # not stored apart for this run: unknown, not zero
