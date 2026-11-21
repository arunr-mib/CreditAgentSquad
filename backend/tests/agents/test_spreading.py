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
    # a line the statement does not print is a sourced zero, proved by the totals that foot without it
    absent = current_fact(db, setup.id, "bs.subordinated_debt", PERIOD, 0)
    assert absent.value == D("0") and absent.kind == "calculated" and absent.calc_run_id is not None
    assert current_fact(db, setup.id, "cf.other_investing", PERIOD, 9).value == D("0")
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


def test_an_absent_line_is_not_stored_when_the_statement_does_not_foot(db, setup):
    answer = perfect_answer()
    answer["cells"] = [c for c in answer["cells"] if c["key"] != "bs.inventory"]
    spread(db, setup, answer)
    assert current_fact(db, setup.id, "bs.subordinated_debt", PERIOD, 0) is None


def test_one_image_only_page_sends_the_whole_document_to_a_person(db, setup):
    import io

    import pymupdf
    pdf = pymupdf.open(stream=build_pdf(), filetype="pdf")
    pdf.new_page()  # a page with no text stands in for a scanned page
    buf = io.BytesIO()
    pdf.save(buf)
    doc = ingest_pdf(db, borrower_id=setup.id, data=buf.getvalue(), file_name="mixed.pdf",
                     doc_type="interim_statements", doc_type_source="system", period_end=PERIOD)
    assert doc.status == "indexed" and doc.meta["image_only_pages"] == [4]
    llm = ScriptedClient([])
    result = spread_document(db, borrower=setup, document=doc, period_end=PERIOD, months=9, cycle=None, llm=llm)
    assert result.status == "needs_person" and llm.requests == [] and items(db) == [("spread.image_only", "medium")]


def test_units_phrase_not_reported_is_caught_by_code(db, setup):
    result, _ = spread(db, setup, perfect_answer(scale_statement="", scale_page=0))
    assert result.status == "needs_person" and items(db) == [("spread.value_unverified", "high")]
    assert db.execute(select(Fact)).first() is None  # nothing stored at the wrong scale


def test_wrong_period_document_stores_nothing(db, setup):
    answer = perfect_answer(cells=perfect_cells("comparative"), comparative_cells=[])
    result, _ = spread(db, setup, answer)
    assert result.status == "needs_person" and items(db) == [("spread.value_unverified", "high")]
    # nothing read from the wrong column is left where a person could wave it through
    assert db.execute(select(Fact).where(Fact.status.in_(("verified", "confirmed", "proposed")))).first() is None


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


# ---- a reader that files a figure under the wrong line, however it words the label -------------
# Found by the independent review: the reader chose the label text it was checked against.

def cell(answer, key):
    return next(c for c in answer["cells"] if c["key"] == key)


def held(result, key):
    return [u for u in result.unverified if u["key"] == key]


def test_swapped_debt_rows_are_held_even_when_the_reader_reports_label_fragments(db, setup):
    answer = perfect_answer()
    debt, other = cell(answer, "bs.long_term_debt"), cell(answer, "bs.other_noncurrent_liabilities")
    debt["key"], other["key"] = "bs.other_noncurrent_liabilities", "bs.long_term_debt"
    debt["printed_label"], other["printed_label"] = "net of current portion", "liabilities"
    result, _ = spread(db, setup, answer)
    assert result.status == "needs_person" and items(db) == [("spread.value_unverified", "medium")]
    assert "reads as 'Long-term debt, net of current portion', not 'Other liabilities'" in held(
        result, "bs.other_noncurrent_liabilities")[0]["detail"]
    assert held(result, "bs.other_noncurrent_liabilities")[0]["row_label"] == "Long-term debt, net of current portion"
    assert current_fact(db, setup.id, "bs.long_term_debt", PERIOD, 0) is None
    assert current_fact(db, setup.id, "bs.total_liabilities", PERIOD, 0) is None  # no totals from held lines


def test_debt_folded_into_other_liabilities_and_declared_absent_is_held(db, setup):
    answer = perfect_answer()
    debt = cell(answer, "bs.long_term_debt")
    debt["key"], debt["printed_label"] = "bs.other_noncurrent_liabilities", "net of current portion"
    answer["absent_keys"].append("bs.long_term_debt")
    result, _ = spread(db, setup, answer)
    assert result.status == "needs_person"
    assert current_fact(db, setup.id, "bs.long_term_debt", PERIOD, 0) is None
    assert current_fact(db, setup.id, "bs.total_liabilities", PERIOD, 0) is None


def test_supplemental_lines_must_come_from_their_own_rows(db, setup):
    # no total covers the supplemental lines, so the row label is the only check they have
    answer = perfect_answer()
    cell(answer, "sup.scheduled_principal").update(printed_figure="—", printed_label="purchase-money debt")
    cell(answer, "sup.cash_interest_paid").update(page=1, printed_figure="1,200", printed_label="Interest expense")
    cell(answer, "sup.cash_taxes_paid").update(page=1, printed_figure="740", printed_label="Income tax expense")
    result, _ = spread(db, setup, answer)
    assert result.status == "needs_person"
    for key in ("sup.scheduled_principal", "sup.cash_interest_paid", "sup.cash_taxes_paid"):
        assert held(result, key) and current_fact(db, setup.id, key, PERIOD, 9) is None, key


def test_an_add_back_line_cannot_be_filled_from_another_expense_row(db, setup):
    answer = perfect_answer()
    sga, charges = cell(answer, "is.sga"), cell(answer, "is.nonrecurring_expense")
    sga["key"], charges["key"] = "is.nonrecurring_expense", "is.sga"
    sga["printed_label"], charges["printed_label"] = "general and administrative", "charges"
    result, _ = spread(db, setup, answer)
    assert result.status == "needs_person" and held(result, "is.nonrecurring_expense") and held(result, "is.sga")


def test_a_header_naming_two_periods_is_refused_before_anything_is_stored(db, setup):
    wide = f"{PERIOD:%B %-d, %Y} September 30, 2025"
    answer = perfect_answer()
    answer["cells"] = [dict(c, column_header=wide) for c in answer["comparative_cells"]]
    answer["comparative_cells"] = []
    result, _ = spread(db, setup, answer)
    assert result.status == "needs_person" and items(db) == [("spread.value_unverified", "high")]
    assert db.execute(select(Fact).where(Fact.borrower_id == setup.id,
                                         Fact.status.in_(("verified", "confirmed", "proposed")))).first() is None


def test_a_spread_whose_printed_totals_were_not_read_is_not_accepted(db, setup):
    answer = perfect_answer()
    answer["cells"] = [c for c in answer["cells"] if not c["key"].startswith("stated.")]
    answer["absent_keys"] = []
    result, _ = spread(db, setup, answer)
    assert result.status == "needs_person" and ("spread.does_not_foot", "high") in items(db)
    assert {e["code"] for e in result.failed_checks} >= {"total_not_read"}
    assert current_fact(db, setup.id, "bs.total_assets", PERIOD, 0) is None


def test_a_borrowers_own_wording_is_confirmed_once_by_a_person_and_then_remembered(db, setup):
    from app.domain.facts_service import confirm_fact
    from app.domain.org import User

    labels = {"bs.revolver": "Notes payable to bank"}
    result, _ = spread(db, setup, perfect_answer(labels=labels), pdf=build_pdf(labels=labels))
    assert result.status == "needs_person"
    assert {u["key"] for u in result.unverified} == {"bs.revolver", "bs.revolver@comparative"}
    entry = held(result, "bs.revolver")[0]
    assert "not a known name" in entry["detail"] and entry["row_label"] == "Notes payable to bank"
    analyst = User(email="an@x.example", name="Analyst", role="analyst", password_hash="x")
    db.add(analyst)
    db.flush()
    confirm_fact(db, db.get(Fact, entry["fact_id"]), analyst.id)

    # the next statement from the same borrower prints the same label: no person is needed
    again, _ = spread(db, setup, perfect_answer(labels=labels), pdf=build_pdf(labels=labels))
    assert again.status == "spread" and again.unverified == []
    # another borrower gets no benefit from that confirmation
    other = Borrower(code="OTH", name="Otherwise Metals, Inc.")
    db.add(other)
    db.flush()
    elsewhere, _ = spread(db, other, perfect_answer(labels=labels), pdf=build_pdf(labels=labels))
    assert elsewhere.status == "needs_person"


def test_a_note_may_point_at_a_page_the_document_has(db, setup):
    notes = ["The debt schedule on page 2 has no template line.", "Leverage on page 2 is high.",
             "The debt schedule on page 9 has no template line."]
    result, _ = spread(db, setup, perfect_answer(notes=notes))
    shown = [n["detail"] for n in result.notes if n["action"] == "shown"]
    assert shown == [notes[0]]
