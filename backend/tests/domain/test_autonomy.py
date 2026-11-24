"""Autonomy: by default a document reading that passed every check still waits for a person.

The rest of the suite runs with EXTRACTION_AUTONOMY=automatic (see conftest.py); these tests
run with the deployment default.
"""
import json
from datetime import date
from decimal import Decimal as D

import pytest
from app.agents.llm import KeyedScriptedClient, LLMResponse
from app.core.config import get_settings
from app.core.ledger import LedgerEvent
from app.domain import hooks, stages, workflow  # noqa: F401
from app.domain.credit import Borrower
from app.domain.documents_service import ingest_pdf
from app.domain.facts_service import add_fact, current_fact
from app.domain.monitoring import WorkItem
from app.domain.org import User
from sqlalchemy import select
from support.statement_pdf import PRIOR_FYE_CASH_THOUSANDS, build_pdf, perfect_answer

PERIOD = date(2026, 9, 30)


@pytest.fixture()
def world(db, tmp_path, monkeypatch):
    monkeypatch.setenv("FILE_STORE_DIR", str(tmp_path))
    monkeypatch.setenv("EXTRACTION_AUTONOMY", "assisted")
    get_settings.cache_clear()
    borrower = Borrower(code="HTD", name="Harrowgate Tool & Die, Inc.")
    analyst = User(email="an@x.example", name="Analyst", role="analyst", password_hash="x")
    db.add_all([borrower, analyst])
    db.flush()
    borrower.analyst_id = analyst.id  # the test's analyst owns the test's client: an analyst acts only on her own clients (owner answer 9)
    add_fact(db, borrower_id=borrower.id, key="bs.cash", period_end=date(2025, 12, 31), months=0,
             value=D(PRIOR_FYE_CASH_THOUSANDS * 1000), kind="seeded")
    doc = ingest_pdf(db, borrower_id=borrower.id, data=build_pdf(), file_name="q3.pdf", doc_type="interim_statements",
                     doc_type_source="system", period_end=PERIOD, received_date=date(2026, 10, 30))
    cycle = workflow.open_cycle(db, borrower_id=borrower.id, period_end=PERIOD, months=9)
    for st in workflow.stages(db, cycle):
        if st.stage in ("awaiting_package", "intake"):
            st.status = "done"
    db.flush()
    client = KeyedScriptedClient({"spreading/": [LLMResponse(
        content=[{"type": "text", "text": json.dumps(perfect_answer())}], stop_reason="end_turn")]})
    monkeypatch.setattr(stages, "LLM_FACTORY", lambda: client)
    workflow.advance(db, cycle)
    workflow.run_next_job(db)  # the spreading stage only
    yield borrower, analyst, doc, cycle
    monkeypatch.delenv("EXTRACTION_AUTONOMY")
    get_settings.cache_clear()


def _stage(db, cycle, name):
    return next(s for s in workflow.stages(db, cycle) if s.stage == name)


def test_the_default_is_assisted():
    from app.core.config import Settings
    assert Settings.model_fields["extraction_autonomy"].default == "assisted"


def test_a_clean_reading_waits_for_a_person_and_goes_on_once_confirmed(db, world, monkeypatch):
    borrower, analyst, doc, cycle = world
    # the reading itself was clean: every figure verified, totals stored
    assert current_fact(db, borrower.id, "bs.total_assets", PERIOD, 0).value == D("34500000")
    (item,) = db.execute(select(WorkItem).where(WorkItem.cycle_id == cycle.id, WorkItem.status == "open")).scalars()
    assert item.item_type == "reading.review" and item.blocks_stage and item.evidence["document_id"] == str(doc.id)
    assert _stage(db, cycle, "spreading").status == "needs_person" and cycle.stage == "spreading"

    monkeypatch.setattr(workflow, "STAGE_HANDLERS", {})  # later stages are not under test
    workflow.decide_work_item(db, item, user_id=analyst.id, user_role=analyst.role, decision="reading_confirmed")
    assert item.status == "decided" and _stage(db, cycle, "spreading").status == "done"
    event = db.execute(select(LedgerEvent).where(LedgerEvent.action == "reading.confirmed")).scalar_one()
    assert event.payload["confirmed_by"] == "Analyst" and str(event.entity_id) == str(doc.id)


def test_asking_for_a_new_document_sets_the_reading_aside(db, world):
    borrower, analyst, doc, cycle = world
    (item,) = db.execute(select(WorkItem).where(WorkItem.cycle_id == cycle.id, WorkItem.status == "open")).scalars()
    workflow.decide_work_item(db, item, user_id=analyst.id, user_role=analyst.role, decision="request_new_document",
                              reason="This is a draft; the final statements are due next week.")
    assert doc.status == "rejected"
    assert _stage(db, cycle, "spreading").status in ("pending", "running")  # waits for the new document
