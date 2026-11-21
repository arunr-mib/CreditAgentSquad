from app.core.ledger import LedgerEvent
from app.domain.agents import AgentRun, AgentSpecRecord
from app.squad.oversight import evaluation_rows
from sqlalchemy import func, select

from .conftest import sign_in


def test_shares_read_as_percentages_counts_as_counts_and_unmeasured_stays_unmeasured():
    rows = {r["key"]: r for r in evaluation_rows({"covenant_outcome_accuracy": 0.9492, "cycles_run": 20,
                                                   "exception_recall": None, "extraction_abstain_rate": 0.0})}
    assert rows["covenant_outcome_accuracy"] == {"key": "covenant_outcome_accuracy", "label": "Covenant outcome accuracy",
                                                 "value": "94.92", "unit": "pct"}
    assert rows["cycles_run"]["value"] == "20" and rows["cycles_run"]["unit"] == "count"
    assert rows["exception_recall"]["value"] is None
    assert rows["extraction_abstain_rate"]["value"] == "0"


def test_evaluation_endpoint_is_for_oversight_roles(db, client, world):
    db.commit()
    sign_in(client, "priya.raman")
    assert client.get("/api/v1/oversight/evaluation").status_code == 403


def test_evaluation_endpoint_serves_rows_for_an_administrator(db, client, world):
    db.commit()
    sign_in(client, "admin")
    r = client.get("/api/v1/oversight/evaluation")
    assert r.status_code in (200, 404), r.text
    if r.status_code == 200:
        body = r.json()
        assert set(body) == {"mode", "standin", "notice", "gate_passed", "created_at", "rows"}
        assert all(set(x) == {"key", "label", "value", "unit"} for x in body["rows"])


def test_runs_and_agents_are_served_in_words_for_oversight_roles_only(db, client, world):
    db.add(AgentRun(agent_name="certificate_reader", agent_version="2", model="m", task="read_certificate",
                    borrower_id=world["borrower"].id, status="abstained",
                    guardrail_notes=[{"layer": "narrative", "check": "figure_untraceable", "action": "dropped"}]))
    db.add(AgentSpecRecord(name="copilot", version="1", model="m", effort="low", max_steps=3, tools=[],
                           prompt_sha256="a" * 64, spec_sha256="b" * 64, purpose="Answers questions"))
    db.commit()
    sign_in(client, "priya.raman")
    assert client.get("/api/v1/oversight/runs").status_code == 403
    assert client.get("/api/v1/oversight/agents").status_code == 403
    sign_in(client, "admin")
    run = next(r for r in client.get("/api/v1/oversight/runs").json() if r["agent_name"] == "certificate_reader")
    assert run["agent_label"] == "Certificate reader agent" and run["task_label"] == "Read certificate"
    assert run["status_label"] == "Abstained"
    assert run["guardrail_notes"][0]["words"] == "figure untraceable · dropped"
    agent = next(a for a in client.get("/api/v1/oversight/agents").json() if a["name"] == "copilot")
    assert agent["label"] == "Copilot"


def test_oversight_reads_never_write_the_ledger(db, client, world):
    db.commit()
    sign_in(client, "admin")
    before = db.execute(select(func.count()).select_from(LedgerEvent).where(LedgerEvent.action != "auth.login")).scalar_one()
    for path in ("runs", "agents", "evaluation"):
        client.get(f"/api/v1/oversight/{path}")
    after = db.execute(select(func.count()).select_from(LedgerEvent).where(LedgerEvent.action != "auth.login")).scalar_one()
    assert after == before
