"""One source for every label a screen shows: the browser keeps no table of document types, signals, ledger
events or agent names (Task 5b retired the front-end tables)."""
from datetime import UTC, datetime, timedelta

from app.core import ledger
from app.domain.agents import AgentRun
from app.publishing.content import SIGNAL_LABELS
from app.squad.briefing import build_briefing
from app.squad.threads import build_thread
from app.squad.words import describe_event, signal_words

from .conftest import sign_in


def test_a_signal_rule_reads_as_its_published_label_and_an_unknown_rule_as_words():
    assert signal_words("reporting_late") == SIGNAL_LABELS["reporting_late"]
    assert signal_words("brand_new_rule") == "Brand new rule"


def test_the_browser_is_served_the_signal_words(db, client, world):
    db.commit()
    sign_in(client, "priya.raman")
    served = client.get("/api/v1/words/signals").json()
    assert served["rules"] == SIGNAL_LABELS


def test_a_report_in_the_thread_and_an_overnight_row_carry_the_agents_words(db, world):
    db.add(AgentRun(agent_name="certificate_reader", agent_version="1", model="m", task="t", borrower_id=world["borrower"].id,
                    status="completed", finished_at=datetime.now(UTC) - timedelta(hours=1), output={"narrative": "all read"}))
    db.flush()
    report = next(m for m in build_thread(db, world["borrower"].id)["messages"] if m["type"] == "report")
    assert report["agent_label"] == "Certificate reader agent"
    assert build_briefing(db, world["analyst"])["overnight"][0]["agent_label"] == "Certificate reader agent"


def test_a_trail_step_names_its_agent_in_the_same_words(db, world):
    from app.domain.work_items import raise_item
    from app.squad.trail import case_trail
    run = AgentRun(agent_name="certificate_reader", agent_version="1", model="m", task="read_certificate",
                   borrower_id=world["borrower"].id, status="completed")
    db.add(run)
    db.flush()
    item = raise_item(db, borrower_id=world["borrower"].id, item_type="funding_slipped", title="t", question="q?",
                      allowed_decisions=["reviewed"], agent_run_id=run.id)
    assert case_trail(db, item)["steps"][0]["who"] == "Certificate reader agent"


def _event(action, payload, document_title=None):
    return describe_event(action, payload, document_title=document_title)


def test_a_ledger_event_reads_in_plain_words():
    assert _event("work_item.decided", {"decision": "reservation_of_rights", "reason": "Certificate overstates EBITDA."}) \
        == "reserved rights · “Certificate overstates EBITDA.”"
    assert _event("work_item.decided", {"decision": "not_a_breach"}) == "marked not a breach"
    assert _event("cycle.stage_changed", {"stage": "covenant_testing", "from": "needs_person", "to": "done"}) \
        == "Covenant testing: needs a person to done"
    assert _event("clock.set", {"to": "2026-11-17", "from": None}) == "to 17 Nov 2026"
    assert _event("covenant.tested", {"covenant": "total_leverage", "outcome": "breach_reported_compliant", "period_end": "2026-09-30"}) \
        == "Total leverage · breach reported compliant · period ended 30 Sep 2026"
    assert _event("work_item.routed", {"view": "Recommend reserving rights."}) == "“Recommend reserving rights.”"
    assert _event("document.classified", {"document_type": "mrr_report"}) == "MRR report"
    assert _event("signal.raised", {"rule_id": "reporting_late", "subject": "october_package"}) \
        == f"{SIGNAL_LABELS['reporting_late']} (october package)"


def test_a_ledger_event_with_nothing_known_shows_only_listed_words_never_a_figure_in_any_form():
    payload = {"zeta": "z-note", "ref": "0a1b2c3d-0a1b-0a1b-0a1b-0a1b2c3d4e5f", "kind": "equity_round", "status": "open"}
    out = _event("x.y", payload)
    assert out == "kind equity round · status open"  # listed keys only, in key order; free values and ids are not shown
    assert _event("x.y", dict(reversed(list(payload.items())))) == out
    for amount in ("$5,000,000 USD", "USD 5,000,000", "5000000.00 USD", "raised 5000000 dollars", "Pays down $12.4 million", "5000000", "about two million"):
        for key in ("amount", "note", "headline", "kind", "x"):
            shown = _event("funding_event.recorded", {key: amount})
            assert not any(ch.isdigit() for ch in shown) and "million" not in shown, (key, amount, shown)


def test_an_agent_failure_does_not_print_the_exception_text():
    assert "Traceback" not in _event("agent.run_failed", {"reason": "Traceback: boom", "agent": "review"})
    assert _event("agent.run_refused", {"reason": "{'stop': 'x'}"}) == ""


def test_the_ledger_and_the_timeline_are_served_with_the_words(db, client, world):
    ledger.record(db, actor_type="system", actor_id="intake", action="document.classified", entity_type="borrower",
                  entity_id=world["borrower"].id, payload={"document_type": "bank_statements"})
    db.commit()
    sign_in(client, "admin")
    rows = client.get("/api/v1/oversight/ledger?action=document").json()
    assert rows and rows[0]["summary"] == "Bank statement"
    sign_in(client, "priya.raman")
    timeline = client.get(f"/api/v1/ui/borrowers/{world['borrower'].id}/timeline").json()
    assert any(r["summary"] == "Bank statement" for r in timeline)
    assert {r["actor_label"] for r in timeline if r["actor_type"] == "system"} == {"System"}  # a name in words, never "system"/"agent" raw


def test_anyone_who_may_see_a_client_can_read_its_runs_in_plain_words_and_no_figure_reaches_them(db, client, world):
    import json

    from app.domain.agents import AgentStep
    run = AgentRun(agent_name="certificate_reader", agent_version="1", model="m", task="read_certificate", borrower_id=world["borrower"].id,
                   status="failed", error="ValueError: loan 5000000 exceeds 4400000", guardrail_notes=[{"layer": "q", "check": "quote_on_page", "action": "dropped", "detail": "figure 8800000 not found"}], output={"narrative": "private"}, raw_output="raw model text")
    db.add(run)
    db.flush()
    db.add(AgentStep(run_id=run.id, n=1, kind="tool", name="read_page", input_summary="{'amount': 5000000}", output_summary="out 7300000",
                     detail={"x": "secret"}, refused=False))
    db.add(AgentStep(run_id=run.id, n=2, kind="guardrail", name="quote_on_page", input_summary="'$9,100,000'", output_summary="", refused=True))
    db.commit()
    sign_in(client, "priya.raman")
    listed = client.get(f"/api/v1/borrowers/{world['borrower'].id}/runs").json()
    assert listed[0]["agent_label"] == "Certificate reader agent" and listed[0]["task_label"] == "Read certificate"
    assert listed[0]["guardrail_notes"] == [{"words": "quote on page · dropped"}]
    assert listed[0]["status_label"] == "Failed" and "raw_output" not in listed[0] and "output" not in listed[0]
    one = client.get(f"/api/v1/runs/{run.id}").json()
    assert [s["words"] for s in one["steps"]] == ["Tool: read page", "Guardrail: quote on page, refused"]
    assert one["error_words"] == "The run stopped on an error; administrators can see the detail in Oversight."
    for body in (json.dumps(listed), json.dumps(one)):
        for leaked in ("5000000", "7300000", "9,100,000", "4400000", "ValueError", "8800000", "secret", "raw model text", "private"):
            assert leaked not in body, leaked
    assert "error" not in one and "scope" not in one and "input_summary" not in json.dumps(one)
    assert client.get("/api/v1/runs/00000000-0000-0000-0000-000000000000").status_code == 404


def test_a_ledger_action_reads_in_words():
    from app.squad.words import action_words
    assert action_words("work_item.decided") == "Cases: decided"
    assert action_words("cycle.stage_changed") == "Cycles: stage changed"
    assert action_words("odd_family.thing") == "Odd family: thing"
    assert action_words("bare") == "Bare"
