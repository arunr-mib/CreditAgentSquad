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


def _results_file(tmp_path, monkeypatch, metrics, name="latest.json"):
    import json

    path = tmp_path / name
    path.write_text(json.dumps({"meta": {"mode": "standin", "suite": "book", "commit": "abc1234", "borrowers": 20,
                                         "generated_at": "2026-11-20T10:00:00Z"},
                                "gate": {"passed": True}, "metrics": metrics}))
    monkeypatch.setattr("app.api.routes_evals.RESULTS_FILE", path)


def test_evaluation_from_the_repository_file_says_so_and_converts_exactly(db, client, world, tmp_path, monkeypatch):
    _results_file(tmp_path, monkeypatch, {"covenant_outcome_accuracy": 0.9492, "cycles_run": 20, "exception_recall": None})
    db.commit()
    sign_in(client, "admin")
    body = client.get("/api/v1/oversight/evaluation").json()
    assert body["source"] == "file" and body["suite"] == "book" and body["commit"] == "abc1234" and body["borrowers"] == 20
    assert body["id"] is None and body["standin"] is True and body["gate_passed"] is True
    assert body["rows"] == [
        {"key": "covenant_outcome_accuracy", "label": "Covenant outcome accuracy", "value": "94.92", "unit": "pct"},
        {"key": "cycles_run", "label": "Cycles run", "value": "20", "unit": "count"},
        {"key": "exception_recall", "label": "Exception recall", "value": None, "unit": "pct"}]


def test_evaluation_is_404_in_the_servers_words_when_there_is_none(db, client, world, tmp_path, monkeypatch):
    monkeypatch.setattr("app.api.routes_evals.RESULTS_FILE", tmp_path / "missing.json")
    db.commit()
    sign_in(client, "admin")
    r = client.get("/api/v1/oversight/evaluation")
    assert r.status_code == 404 and "No evaluation has been run" in r.json()["detail"]


def test_a_run_in_this_database_wins_over_the_file(db, client, world, tmp_path, monkeypatch):
    from app.domain.governance import EvalRun

    _results_file(tmp_path, monkeypatch, {"cycles_run": 20})
    db.add(EvalRun(suite="book", mode="recorded", commit="def5678", gate_passed=False,
                   results={"meta": {"borrowers": 3}, "metrics": {"cycles_run": 3}}))
    db.commit()
    sign_in(client, "admin")
    body = client.get("/api/v1/oversight/evaluation").json()
    assert body["source"] == "database" and body["id"] and body["commit"] == "def5678" and body["gate_passed"] is False
    assert body["rows"][0]["value"] == "3"


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


def _ledger(db, actions):
    from app.core import ledger

    for i, (kind, who, action) in enumerate(actions):
        ledger.record(db, actor_type=kind, actor_id=who, action=action, entity_type="x", entity_id=str(i))


def test_ledger_filter_families_come_from_the_ledger_in_words_and_each_returns_its_events(db, client, world):
    _ledger(db, [("system", "x", "obligation.became_overdue"), ("system", "x", "covenant.tested"),
                 ("system", "x", "borrowing_base.reviewed"), ("system", "x", "funding_event.created"),
                 ("system", "x", "signal.raised"), ("user", str(world["admin"].id), "auth.login")])
    db.commit()
    sign_in(client, "admin")
    families = client.get("/api/v1/oversight/ledger-actions").json()
    by_key = {f["key"]: f["words"] for f in families}
    assert {"obligation", "covenant", "borrowing_base", "funding_event", "signal", "auth"} <= set(by_key)
    assert by_key["borrowing_base"] == "Borrowing base" and by_key["auth"] == "Sign-ins"
    for f in families:
        events = client.get("/api/v1/oversight/ledger", params={"action": f["key"], "limit": 5}).json()
        assert events and all(e["action"].startswith(f["key"]) for e in events), f
    every = {e["action"].split(".")[0] for e in client.get("/api/v1/oversight/ledger", params={"limit": 500}).json()}
    assert every <= set(by_key)


def test_ledger_can_hide_sign_ins_on_the_server_and_names_the_actor(db, client, world):
    _ledger(db, [("agent", "certificate_reader@2", "document.read"), ("system", "x", "cycle.opened")])
    db.commit()
    sign_in(client, "admin")
    rows = client.get("/api/v1/oversight/ledger", params={"hide_sign_ins": "true", "limit": 500}).json()
    assert rows and not any(r["action"].startswith("auth.") for r in rows)
    assert next(r for r in rows if r["action"] == "document.read")["actor_label"] == "Certificate reader agent"
    everything = client.get("/api/v1/oversight/ledger", params={"limit": 500}).json()
    assert any(r["action"].startswith("auth.") for r in everything)
    assert next(r for r in everything if r["action"].startswith("auth."))["actor_label"] == world["admin"].name


def test_ledger_is_for_oversight_roles(db, client, world):
    db.commit()
    sign_in(client, "priya.raman")
    assert client.get("/api/v1/oversight/ledger").status_code == 403
    assert client.get("/api/v1/oversight/ledger-actions").status_code == 403


def test_runs_page_past_one_hundred_and_carry_their_tool_calls_and_error(db, client, world):
    for i in range(7):
        db.add(AgentRun(agent_name="copilot", agent_version="1", model="m", task="ask", status="failed" if i == 0 else "completed",
                        steps_count=3, error="The model did not answer." if i == 0 else None))
    db.commit()
    sign_in(client, "admin")
    first = client.get("/api/v1/oversight/runs", params={"limit": 5}).json()
    rest = client.get("/api/v1/oversight/runs", params={"limit": 5, "offset": 5}).json()
    assert len(first) == 5 and len(rest) == 2 and {r["id"] for r in first}.isdisjoint(r["id"] for r in rest)
    assert all(r["tool_calls"] == 3 for r in first + rest)
    failed = next(r for r in first + rest if r["status"] == "failed")
    assert failed["error"] == "The model did not answer."


def test_briefing_says_whether_oversight_is_offered(db, client, world):
    db.commit()
    sign_in(client, "admin")
    assert client.get("/api/v1/me/briefing").json()["oversight"] == {"offered": True}
    sign_in(client, "priya.raman")
    assert client.get("/api/v1/me/briefing").json()["oversight"] == {"offered": False}


def test_asking_for_sign_ins_shows_them_even_with_sign_ins_hidden(db, client, world):
    db.commit()
    sign_in(client, "admin")
    rows = client.get("/api/v1/oversight/ledger", params={"action": "auth", "hide_sign_ins": "true"}).json()
    assert rows and all(r["action"].startswith("auth.") for r in rows)
