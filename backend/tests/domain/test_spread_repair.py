"""The repair path for a held spread: a person keys or confirms figures, or sets the document
aside, and the cycle carries on from there."""
import json
from datetime import date
from decimal import Decimal as D

import pytest
from app.agents.llm import KeyedScriptedClient, LLMResponse
from app.core.config import get_settings
from app.domain import hooks, stages, workflow  # noqa: F401
from app.domain.credit import Borrower
from app.domain.documents_service import ingest_pdf
from app.domain.facts import Fact
from app.domain.facts_service import add_fact, current_fact
from app.domain.monitoring import WorkItem
from app.domain.org import User
from sqlalchemy import select
from support.statement_pdf import PRIOR_FYE_CASH_THOUSANDS, build_pdf, perfect_answer

PERIOD = date(2026, 9, 30)


@pytest.fixture()
def world(db, tmp_path, monkeypatch):
    monkeypatch.setenv("FILE_STORE_DIR", str(tmp_path))
    get_settings.cache_clear()
    borrower = Borrower(code="HTD", name="Harrowgate Tool & Die, Inc.")
    analyst = User(email="an@x.example", name="Analyst", role="analyst", password_hash="x")
    db.add_all([borrower, analyst])
    db.flush()
    add_fact(db, borrower_id=borrower.id, key="bs.cash", period_end=date(2025, 12, 31), months=0,
             value=D(PRIOR_FYE_CASH_THOUSANDS * 1000), kind="seeded")
    doc = ingest_pdf(db, borrower_id=borrower.id, data=build_pdf(), file_name="q3.pdf", doc_type="interim_statements",
                     doc_type_source="system", period_end=PERIOD, received_date=date(2026, 10, 30))
    cycle = workflow.open_cycle(db, borrower_id=borrower.id, period_end=PERIOD, months=9)
    for st in workflow.stages(db, cycle):  # start the cycle at spreading
        if st.stage in ("awaiting_package", "intake"):
            st.status = "done"
    db.flush()
    yield borrower, analyst, doc, cycle
    get_settings.cache_clear()


def run_spreading(db, cycle, monkeypatch, answer):
    client = KeyedScriptedClient({"spreading/": [LLMResponse(
        content=[{"type": "text", "text": json.dumps(answer)}], stop_reason="end_turn")]})
    monkeypatch.setattr(stages, "LLM_FACTORY", lambda: client)
    workflow.advance(db, cycle)
    workflow.run_next_job(db)  # the spreading stage only
    return db.execute(select(WorkItem).where(WorkItem.cycle_id == cycle.id, WorkItem.status == "open")).scalars().all()


def held_answer():
    answer = perfect_answer()
    for cell in answer["cells"]:
        if cell["key"] == "cf.capex":
            cell["printed_figure"] = "1,400"  # the page prints (1,400): not found, so no value is stored
    return answer


def test_a_person_keys_the_missing_figure_and_the_spread_is_finished(db, world, monkeypatch):
    borrower, analyst, _, cycle = world
    items = run_spreading(db, cycle, monkeypatch, held_answer())
    assert [i.item_type for i in items] == ["spread.value_unverified"] and cycle.stage == "spreading"
    item = items[0]
    assert item.evidence["spread"]["scale"] == 1000 and "bs.subordinated_debt" in item.evidence["spread"]["absent"]
    # confirming is refused: there is no value on file for the figure that was not found
    with pytest.raises(ValueError, match="enter them first: cf.capex"):
        workflow.decide_work_item(db, item, user_id=analyst.id, user_role=analyst.role, decision="values_confirmed")
    assert item.status == "open"
    # the analyst keys it from the page, then says the values are corrected
    add_fact(db, borrower_id=borrower.id, key="cf.capex", period_end=PERIOD, months=9, value=D("1400000"),
             kind="manual", entered_by=analyst.id, reason="Read from page 3: (1,400) in thousands.")
    monkeypatch.setattr(workflow, "STAGE_HANDLERS", {})  # stop after spreading: later stages are not under test
    workflow.decide_work_item(db, item, user_id=analyst.id, user_role=analyst.role, decision="values_corrected")
    assert item.status == "decided"
    assert current_fact(db, borrower.id, "cf.cfi", PERIOD, 9).value == D("-1400000")
    assert current_fact(db, borrower.id, "bs.total_assets", PERIOD, 0).value == D("34500000")
    assert current_fact(db, borrower.id, "bs.subordinated_debt", PERIOD, 0).value == D("0")
    assert {s.stage: s.status for s in workflow.stages(db, cycle)}["spreading"] == "done"


def test_a_wrong_correction_is_caught_by_the_footing_check_again(db, world, monkeypatch):
    borrower, analyst, _, cycle = world
    item = run_spreading(db, cycle, monkeypatch, held_answer())[0]
    add_fact(db, borrower_id=borrower.id, key="cf.capex", period_end=PERIOD, months=9, value=D("1900000"),
             kind="manual", entered_by=analyst.id, reason="Keyed in a hurry.")
    workflow.decide_work_item(db, item, user_id=analyst.id, user_role=analyst.role, decision="values_corrected")
    still = db.execute(select(WorkItem).where(WorkItem.cycle_id == cycle.id, WorkItem.status == "open")).scalars().all()
    assert [i.item_type for i in still] == ["spread.does_not_foot"] and cycle.stage == "spreading"
    assert current_fact(db, borrower.id, "cf.cfi", PERIOD, 9) is None  # no total from a figure that does not foot


def test_setting_the_document_aside_waits_for_a_new_one(db, world, monkeypatch):
    borrower, analyst, doc, cycle = world
    item = run_spreading(db, cycle, monkeypatch, held_answer())[0]
    workflow.decide_work_item(db, item, user_id=analyst.id, user_role=analyst.role, decision="request_new_document",
                              reason="Capex line is illegible.")
    workflow.drain(db)
    assert doc.status == "rejected" and cycle.stage == "spreading" and cycle.status == "open"
    assert {s.stage: s.status for s in workflow.stages(db, cycle)}["spreading"] == "pending"  # waiting, not done
    assert db.execute(select(Fact).where(Fact.key == "bs.total_assets")).first() is None
