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
        == "reservation of rights · “Certificate overstates EBITDA.”"
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


def test_a_ledger_event_with_nothing_known_shows_a_few_plain_fields_and_short_ids():
    out = _event("x.y", {"count": 3, "ref": "0a1b2c3d-0a1b-0a1b-0a1b-0a1b2c3d4e5f", "nested": {"a": 1}})
    assert out == "count 3 · ref 0a1b2c3d"


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


def test_anyone_who_may_see_a_client_can_read_its_runs_in_words_without_the_raw_output(db, client, world):
    from app.domain.agents import AgentStep
    run = AgentRun(agent_name="certificate_reader", agent_version="1", model="m", task="read_certificate", borrower_id=world["borrower"].id,
                   status="completed", output={"narrative": "private"}, raw_output="raw model text")
    db.add(run)
    db.flush()
    db.add(AgentStep(run_id=run.id, n=1, kind="tool", name="read_page", input_summary="page 2", output_summary="ok", detail={}))
    db.commit()
    sign_in(client, "priya.raman")
    listed = client.get(f"/api/v1/borrowers/{world['borrower'].id}/runs").json()
    assert listed[0]["agent_label"] == "Certificate reader agent" and listed[0]["task_label"] == "Read certificate"
    assert listed[0]["status_label"] == "Completed" and "raw_output" not in listed[0] and "output" not in listed[0]
    one = client.get(f"/api/v1/runs/{run.id}").json()
    assert one["steps"][0]["name"] == "read_page" and "detail" not in one["steps"][0] and "raw_output" not in one and one["agent_label"].endswith("agent")
    assert client.get("/api/v1/runs/00000000-0000-0000-0000-000000000000").status_code == 404
