"""The Spreading Agent with a scripted model: what code verifies, stores and refuses."""
import json
from datetime import date
from decimal import Decimal as D

import pytest
from app.agents.llm import LLMResponse, ScriptedClient
from app.agents.spreading import spread_document
from app.core.config import get_settings
from app.domain.credit import Borrower
from app.domain.documents_service import ingest_pdf
from app.domain.facts import Fact
from app.domain.facts_service import add_fact, current_fact
from app.domain.monitoring import WorkItem
from sqlalchemy import select
from support.statement_pdf import PRIOR_FYE_CASH_THOUSANDS, build_pdf, perfect_answer, perfect_cells

PERIOD = date(2026, 9, 30)
PRIOR_CASH = D(PRIOR_FYE_CASH_THOUSANDS * 1000)


@pytest.fixture()
def setup(db, tmp_path, monkeypatch):
    monkeypatch.setenv("FILE_STORE_DIR", str(tmp_path))
    get_settings.cache_clear()
    borrower = Borrower(code="HTD", name="Harrowgate Tool & Die, Inc.")
    db.add(borrower)
    db.flush()
    yield borrower
    get_settings.cache_clear()


def spread(db, borrower, answer, pdf=None):
    doc = ingest_pdf(db, borrower_id=borrower.id, data=pdf or build_pdf(), file_name="q3-2026.pdf",
                     doc_type="interim_statements", doc_type_source="system", period_end=PERIOD)
    llm = ScriptedClient([LLMResponse(content=[{"type": "text", "text": json.dumps(answer)}], stop_reason="end_turn")])
    return spread_document(db, borrower=borrower, document=doc, period_end=PERIOD, months=9, cycle=None,
                           llm=llm, prior_fye_cash=PRIOR_CASH), doc


def items(db):
    return [(w.item_type, w.severity) for w in db.execute(select(WorkItem).order_by(WorkItem.created_at)).scalars()]


def test_clean_statement_is_spread_with_citations_and_no_person(db, setup):
    result, doc = spread(db, setup, perfect_answer())
    assert result.status == "spread" and result.unverified == [] and result.failed_checks == [] and items(db) == []

    revenue = current_fact(db, setup.id, "is.revenue", PERIOD, 9)
    assert revenue.value == D("48250000") and revenue.kind == "extracted" and revenue.status == "verified"
    assert revenue.document_id == doc.id and revenue.page == 1 and revenue.quote == "$ 48,250"
    assert revenue.scale_as_reported == 1000 and len(revenue.bbox) == 4

    # an expense printed without brackets and an outflow printed in brackets are both stored positive
    assert current_fact(db, setup.id, "is.cogs", PERIOD, 9).value == D("33775000")
    assert current_fact(db, setup.id, "cf.capex", PERIOD, 9).value == D("1400000")
    assert current_fact(db, setup.id, "cf.change_in_working_capital", PERIOD, 9).value == D("-1090000")
    # balance sheet lines are point in time
    assert current_fact(db, setup.id, "bs.cash", PERIOD, 0).value == D("2150000")
    # a printed dash is a verified zero, not a missing value
    assert current_fact(db, setup.id, "sup.financed_capex", PERIOD, 9).value == D("0")

    # totals are calculated by code and name their inputs
    total = current_fact(db, setup.id, "bs.total_assets", PERIOD, 0)
    assert total.kind == "calculated" and total.value == D("34500000") and total.calc_run_id is not None
    assert current_fact(db, setup.id, "is.net_income", PERIOD, 9).value == D("2340000")
    # the printed total is kept too, as its own extracted fact
    assert current_fact(db, setup.id, "stated.bs.total_assets", PERIOD, 0).kind == "extracted"
    # no fact was ever stored from a number typed by the model
    assert db.execute(select(Fact).where(Fact.kind == "extracted", Fact.quote.is_(None))).first() is None


def test_figure_reported_without_its_brackets_goes_to_a_person_and_no_totals_are_stored(db, setup):
    answer = perfect_answer()
    for cell in answer["cells"]:
        if cell["key"] == "cf.capex":
            cell["printed_figure"] = "1,400"  # the page prints (1,400)
    result, _ = spread(db, setup, answer)
    assert result.status == "needs_person"
    assert [u["key"] for u in result.unverified] == ["cf.capex"] and result.unverified[0]["reason"] == "not_found"
    assert ("spread.value_unverified", "medium") in items(db)
    assert current_fact(db, setup.id, "cf.capex", PERIOD, 9) is None
    assert current_fact(db, setup.id, "cf.cfi", PERIOD, 9) is None  # no total computed from a gap


def test_reading_the_prior_year_column_is_caught(db, setup):
    answer = perfect_answer()
    for cell in answer["cells"]:
        if cell["key"] == "is.revenue":
            cell["printed_figure"] = "$ 45,100"  # prior-year figure, current-year header
    result, _ = spread(db, setup, answer)
    assert result.unverified[0]["reason"] == "column_unconfirmed"
    proposed = db.execute(select(Fact).where(Fact.key == "is.revenue")).scalar_one()
    assert proposed.status == "proposed"  # kept for the person, never used in a calculation
    assert current_fact(db, setup.id, "is.revenue", PERIOD, 9) is None


def test_a_missed_line_fails_footing(db, setup):
    answer = perfect_answer()
    answer["cells"] = [c for c in answer["cells"] if c["key"] != "bs.inventory"]
    answer["absent_keys"].append("bs.inventory")  # the model claims there is no inventory line
    result, _ = spread(db, setup, answer)
    assert result.status == "needs_person" and ("spread.does_not_foot", "high") in items(db)
    codes = {e["code"] for e in result.failed_checks}
    assert "does_not_foot" in codes and "absent_not_verified" in codes
    assert current_fact(db, setup.id, "bs.total_assets", PERIOD, 0) is None


def test_units_phrase_not_reported_is_caught_by_code(db, setup):
    result, _ = spread(db, setup, perfect_answer(scale_statement="", scale_page=0))
    assert result.status == "needs_person" and items(db) == [("spread.value_unverified", "high")]
    assert db.execute(select(Fact)).first() is None  # nothing stored at the wrong scale


def test_wrong_period_document_stores_nothing(db, setup):
    answer = perfect_answer(cells=perfect_cells("comparative"), comparative_cells=[])
    result, _ = spread(db, setup, answer)
    assert result.status == "needs_person" and db.execute(select(Fact)).first() is None


def test_restated_comparative_raises_an_item(db, setup):
    prior = date(2025, 9, 30)
    add_fact(db, borrower_id=setup.id, key="is.revenue", period_end=prior, months=9, value=D("44000000"), kind="seeded")
    result, _ = spread(db, setup, perfect_answer())
    assert ("spread.restatement", "medium") in items(db)
    # the confirmed prior-period fact is untouched
    assert current_fact(db, setup.id, "is.revenue", prior, 9).value == D("44000000")


def test_a_note_with_a_typed_figure_is_removed(db, setup):
    result, _ = spread(db, setup, perfect_answer(notes=["Revenue grew to 48,250.", "Page two is slightly skewed."]))
    shown = [n["detail"] for n in result.notes if n["action"] == "shown"]
    assert shown == ["Page two is slightly skewed."]
    assert any(n["action"] == "dropped" for n in result.notes)


def test_unknown_or_computed_keys_are_dropped(db, setup):
    answer = perfect_answer()
    answer["cells"].append({"key": "is.ebitda", "page": 1, "printed_figure": "4,205",
                            "printed_label": "Operating income", "column_header": "September 30, 2026"})
    answer["cells"].append({"key": "bs.total_assets", "page": 2, "printed_figure": "$ 34,500",
                            "printed_label": "Total assets", "column_header": "September 30, 2026"})
    result, _ = spread(db, setup, answer)
    assert result.status == "spread"
    assert sum(1 for n in result.notes if n["check"] == "unknown_key") == 2


def test_image_only_document_goes_to_a_person_without_a_model_call(db, setup):
    import io

    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.showPage()
    c.save()
    doc = ingest_pdf(db, borrower_id=setup.id, data=buf.getvalue(), file_name="scan.pdf")
    llm = ScriptedClient([])
    result = spread_document(db, borrower=setup, document=doc, period_end=PERIOD, months=9, cycle=None, llm=llm)
    assert result.status == "needs_person" and llm.requests == [] and items(db) == [("spread.image_only", "medium")]
