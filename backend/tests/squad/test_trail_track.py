import uuid
from datetime import date
from decimal import Decimal as D

from app.core import ledger
from app.domain.agents import AgentRun
from app.domain.facts import CalcRun
from app.domain.facts_service import add_fact
from app.domain.work_items import raise_item
from app.squad.track_record import track_record
from app.squad.trail import case_trail

from .conftest import sign_in

PERIOD = date(2026, 10, 31)


def _run(db, borrower, agent="spreading", task="read_statements"):
    run = AgentRun(agent_name=agent, agent_version="1", model="m", task=task, borrower_id=borrower.id,
                   status="completed", guardrail_notes=[{"layer": "quotes", "check": "quote_on_page",
                                                         "action": "pass", "detail": "found on p. 3"}])
    db.add(run)
    db.flush()
    return run


def _calc(db, borrower):
    calc = CalcRun(borrower_id=borrower.id, formula_key="cov.min_unrestricted_cash", formula_version="1",
                   period_end=PERIOD, inputs=[{"name": "cash", "value": "4600000"}], outputs={"result": "4600000"},
                   trace={}, engine_version="1")
    db.add(calc)
    db.flush()
    return calc


def test_trail_lists_the_run_the_calculation_and_the_guardrail_checks(db, world):
    run = _run(db, world["borrower"])
    calc = _calc(db, world["borrower"])
    item = raise_item(db, borrower_id=world["borrower"].id, item_type="funding_slipped", title="t",
                      question="Review it?", allowed_decisions=["reviewed"], agent_run_id=run.id,
                      evidence={"calc_run_id": str(calc.id)})
    trail = case_trail(db, item)
    assert [s["who"] for s in trail["steps"]] == ["Spreading agent", "Code"]
    assert trail["calculation"]["formula_key"] == "cov.min_unrestricted_cash"
    assert trail["checks"][0]["check"] == "quote_on_page"


def test_a_case_with_no_run_has_an_honest_empty_trail(db, world):
    item = raise_item(db, borrower_id=world["borrower"].id, item_type="funding_slipped", title="t",
                      question="Review it?", allowed_decisions=["reviewed"])
    trail = case_trail(db, item)
    assert trail["steps"] == [] and trail["calculation"] is None and trail["checks"] == []


def _extracted(db, borrower, run, key):
    from app.domain.documents import Document
    doc = Document(borrower_id=borrower.id, title="t", file_name="f", storage_path="p", sha256="b" * 64, page_count=1)
    db.add(doc)
    db.flush()
    return add_fact(db, borrower_id=borrower.id, key=key, period_end=PERIOD, months=1, value=D("100"),
                    kind="extracted", document_id=doc.id, page=1, quote="100", agent_run_id=run.id)


def test_track_record_counts_right_corrected_and_unreviewed_from_the_record(db, world):
    from app.domain.facts_service import correct_fact, reject_fact
    run = _run(db, world["borrower"])
    user = world["analyst"]
    good = _extracted(db, world["borrower"], run, "is.total_revenue")
    bad = _extracted(db, world["borrower"], run, "bs.cash")
    refused = _extracted(db, world["borrower"], run, "bs.debt")
    pending = _extracted(db, world["borrower"], run, "is.cogs")
    good.status, pending.status = "verified", "proposed"
    correct_fact(db, bad, value=D("90"), user_id=user.id, reason="misread")
    reject_fact(db, refused, user_id=user.id, reason="not on the page")
    db.flush()
    [row] = track_record(db, world["borrower"].id)
    assert (row["task"], row["right"], row["corrected"], row["unreviewed"], row["checked"]) == ("read_statements", 1, 2, 1, 4)
    assert row["last_correction_at"] is not None and isinstance(row["since"], str)
    assert row["task_label"] == "Read statements" and row["agent_label"].endswith("agent")
    assert "_" not in row["agent_label"] and row["agent_label"][0].isupper()


def test_a_supersede_by_a_non_person_is_not_a_correction(db, world):
    run = _run(db, world["borrower"])
    fact = _extracted(db, world["borrower"], run, "bs.cash")
    fact.status = "superseded"
    ledger.record(db, actor_type="system", actor_id="facts", action="fact.superseded", entity_type="fact",
                  entity_id=fact.id, payload={})
    db.flush()
    assert track_record(db, world["borrower"].id) == []


def test_trail_endpoints_need_the_view_permission(db, client, world, monkeypatch):
    import app.api.deps as deps
    from app.core.roles import Permission
    real = deps.can
    monkeypatch.setattr(deps, "can", lambda role, perm: False if perm == Permission.VIEW else real(role, perm))
    sign_in(client, "priya.raman")
    assert client.get(f"/api/v1/cases/{uuid.uuid4()}/trail").status_code == 403
    assert client.get(f"/api/v1/borrowers/{world['borrower'].id}/track-record").status_code == 403


def test_track_record_is_empty_for_a_client_nothing_has_read(db, world):
    assert track_record(db, world["other"].id) == []


def test_endpoints_return_404_for_unknown_ids(db, client, world):
    sign_in(client, "priya.raman")
    assert client.get(f"/api/v1/cases/{uuid.uuid4()}/trail").status_code == 404
    assert client.get(f"/api/v1/borrowers/{uuid.uuid4()}/track-record").status_code == 404
    assert client.get(f"/api/v1/borrowers/{world['borrower'].id}/track-record").json() == []


def test_squad_demo_seed_is_idempotent_and_visible_in_the_briefing(db, client, world):
    from app.squad_demo import seed_squad_demo
    first = seed_squad_demo(db)
    second = seed_squad_demo(db)
    assert first["work_item_id"] == second["work_item_id"] and first["draft_id"] == second["draft_id"]
    from app.domain.monitoring import WorkItem
    from sqlalchemy import func, select
    assert db.execute(select(func.count()).select_from(WorkItem).where(WorkItem.item_type == "question")).scalar_one() == 1
    db.commit()
    sign_in(client, "priya.raman")
    kinds = {i["kind"] for i in client.get("/api/v1/me/briefing").json()["items"]}
    assert "question" in kinds


def test_agent_and_task_words_come_from_one_place():
    from app.squad.words import agent_words, task_words
    assert agent_words("certificate_reader") == "Certificate reader agent"
    assert agent_words("review@2") == "Review agent" and agent_words("copilot") == "Copilot"
    assert task_words("read_certificate") == "Read certificate"
