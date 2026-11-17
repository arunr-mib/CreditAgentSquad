"""A corrected figure must not leave results calculated from the old one in use."""
import json
from datetime import date
from decimal import Decimal as D

import pytest
from app.agents.llm import KeyedScriptedClient, LLMResponse
from app.calc import template
from app.core.config import get_settings
from app.domain import corrections, hooks, stages, workflow  # noqa: F401
from app.domain.credit import Borrower
from app.domain.documents_service import ingest_pdf
from app.domain.facts_service import add_fact, current_fact
from app.domain.monitoring import WorkItem
from app.domain.org import User
from sqlalchemy import select
from support.statement_pdf import PRIOR_FYE_CASH_THOUSANDS, build_pdf, perfect_answer

PERIOD = date(2026, 9, 30)


def test_two_facts_written_in_one_transaction_resolve_to_the_later_one(db):
    """`now()` is the same instant for a whole transaction, so the order must not rest on it."""
    borrower = Borrower(code="ORD", name="Orderly Supply, Inc.")
    db.add(borrower)
    db.flush()
    for i in range(40):
        add_fact(db, borrower_id=borrower.id, key=f"probe.{i}", period_end=PERIOD, months=0, value=D(1), kind="seeded")
        add_fact(db, borrower_id=borrower.id, key=f"probe.{i}", period_end=PERIOD, months=0, value=D(2), kind="seeded")
    assert {current_fact(db, borrower.id, f"probe.{i}", PERIOD, 0).value for i in range(40)} == {D(2)}


# ---- a statement read from a document: the corrected figures must still foot -----------------

@pytest.fixture()
def spread(db, tmp_path, monkeypatch):
    monkeypatch.setenv("FILE_STORE_DIR", str(tmp_path))
    get_settings.cache_clear()
    borrower = Borrower(code="HTD", name="Harrowgate Tool & Die, Inc.")
    analyst = User(email="an@x.example", name="Analyst", role="analyst", password_hash="x")
    db.add_all([borrower, analyst])
    db.flush()
    add_fact(db, borrower_id=borrower.id, key="bs.cash", period_end=date(2025, 12, 31), months=0,
             value=D(PRIOR_FYE_CASH_THOUSANDS * 1000), kind="seeded")
    ingest_pdf(db, borrower_id=borrower.id, data=build_pdf(), file_name="q3.pdf", doc_type="interim_statements",
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
    monkeypatch.setattr(workflow, "STAGE_HANDLERS", {})  # later stages are not under test
    assert current_fact(db, borrower.id, "bs.total_assets", PERIOD, 0).value == D("34500000")
    yield borrower, analyst, cycle
    get_settings.cache_clear()


def _open(db, borrower):
    return list(db.execute(select(WorkItem).where(WorkItem.borrower_id == borrower.id,
                                                  WorkItem.status == "open")).scalars())


def test_a_correction_that_breaks_the_footing_withholds_the_totals_until_it_is_put_right(db, spread):
    borrower, analyst, _ = spread
    cash = current_fact(db, borrower.id, "bs.cash", PERIOD, 0)
    wrong, summary = corrections.correct(db, cash, value=cash.value + D(500000), user_id=analyst.id,
                                         reason="Misread the cash line.")
    assert summary["totals"] == "does_not_foot"
    assert current_fact(db, borrower.id, "bs.total_assets", PERIOD, 0) is None  # no total from figures that disagree
    assert [w.item_type for w in _open(db, borrower)] == ["spread.does_not_foot"]

    _, summary = corrections.correct(db, wrong, value=cash.value, user_id=analyst.id, reason="Read it again: as printed.")
    assert summary["totals"] == "recalculated"
    assert current_fact(db, borrower.id, "bs.total_assets", PERIOD, 0).value == D("34500000")


def test_keying_a_line_the_statement_did_not_print_replaces_the_assumed_zero(db, spread):
    borrower, analyst, _ = spread
    zero = current_fact(db, borrower.id, "bs.subordinated_debt", PERIOD, 0)
    assert zero.value == 0 and zero.kind == "calculated"
    new, summary = corrections.enter(db, borrower_id=borrower.id, key="bs.subordinated_debt", period_end=PERIOD,
                                     months=0, value=D(250000), user_id=analyst.id,
                                     reason="Shareholder note found in the footnotes.")
    assert zero.status == "superseded" and new.supersedes_fact_id == zero.id
    assert current_fact(db, borrower.id, "bs.subordinated_debt", PERIOD, 0).id == new.id
    # the printed totals no longer agree with the lines, so no total is stored and a person is asked
    assert summary["totals"] == "does_not_foot"
    assert current_fact(db, borrower.id, "bs.total_liabilities", PERIOD, 0) is None


def test_rejecting_a_figure_retires_what_was_calculated_from_it(db, spread):
    borrower, analyst, _ = spread
    revenue = current_fact(db, borrower.id, "is.revenue", PERIOD, 9)
    summary = corrections.reject(db, revenue, user_id=analyst.id, reason="Wrong column.")
    assert summary["retired"] > 0 and summary["totals"] == "does_not_foot"
    assert current_fact(db, borrower.id, "is.revenue", PERIOD, 9) is None
    assert current_fact(db, borrower.id, "is.gross_profit", PERIOD, 9) is None
    assert all(line.key for line in template.LINES)
