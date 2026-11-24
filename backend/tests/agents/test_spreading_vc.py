"""A venture (vc-1) spread: required totals and the cash roll follow the borrower's template."""
import io
import json
from datetime import date
from decimal import Decimal as D

import pytest
from app.agents import spreading
from app.agents.llm import LLMResponse, ScriptedClient
from app.agents.spreading import finalize_spread, spread_document
from app.calc import template
from app.core.config import get_settings
from app.domain import stages
from app.domain.credit import Borrower
from app.domain.documents_service import ingest_pdf
from app.domain.facts_service import add_fact, current_fact
from app.domain.monitoring import Cycle, WorkItem
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import select

PERIOD = date(2026, 9, 30)
PRIOR_FYE = date(2025, 12, 31)
CUR = "September 30, 2026"

# printed in thousands. Totals are listed with their template keys; `stated.` is added for them.
ROWS = {
    1: [("is.subscription_revenue", "5,000"), ("is.services_revenue", "500"), ("is.total_revenue", "5,500"),
        ("is.cost_of_revenue", "1,500"), ("is.vc_gross_profit", "4,000"), ("is.rnd", "3,000"),
        ("is.sales_marketing", "2,500"), ("is.gna", "1,500"), ("is.vc_depreciation_amortization", "200"),
        ("is.vc_operating_loss", "(3,200)"), ("is.vc_interest", "100"), ("is.vc_other_income", "50"),
        ("is.vc_net_loss", "(3,250)")],
    2: [("bs.cash_unrestricted", "4,000"), ("bs.cash_restricted", "500"), ("bs.vc_total_cash", "4,500"),
        ("bs.short_term_investments", "1,000"), ("bs.accounts_receivable", "800"), ("bs.other_current_assets", "200"),
        ("bs.capitalised_software", "1,500"), ("bs.vc_other_intangibles", "100"), ("bs.other_noncurrent_assets", "100"),
        ("bs.vc_total_assets", "8,200"),
        ("bs.accounts_payable", "600"), ("bs.accrued_liabilities", "400"), ("bs.deferred_revenue_current", "900"),
        ("bs.deferred_revenue_noncurrent", "100"), ("bs.venture_debt_current", "500"),
        ("bs.venture_debt_noncurrent", "2,000"), ("bs.convertible_notes", "300"), ("bs.safes", "200"),
        ("bs.vc_other_liabilities", "100"), ("bs.vc_total_liabilities", "5,100"),
        ("bs.preferred_equity", "6,000"), ("bs.common_equity", "(2,900)"), ("bs.vc_total_equity", "3,100"),
        ("bs.vc_total_liabilities_and_equity", "8,200")],
    3: [("cf.vc_operating_cash_flow", "(2,900)"), ("cf.vc_capex", "(100)"), ("cf.capitalised_software_spend", "(200)"),
        ("cf.equity_raised", "3,000"), ("cf.debt_raised", "500"), ("cf.vc_other_financing", "100"),
        ("cf.vc_net_change_in_cash", "400"),
        ("sup.cash_interest_paid", "90"), ("sup.scheduled_principal", "400"),
        ("saas.mrr", "400"), ("saas.arr", "4,800"), ("saas.customers", "120")],
}
PRIOR_FYE_CASH = D("4100000")  # 4,500 now, less a 400 net change over the nine months


def _pdf() -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, invariant=1)
    for rows in ROWS.values():
        c.setFont("Helvetica-Bold", 11)
        c.drawString(72, 740, "Quillfeather Labs, Inc.")
        c.setFont("Helvetica", 9)
        c.drawString(72, 726, f"Unaudited, nine months ended {CUR} (in thousands)")
        c.drawRightString(440, 706, CUR)
        y = 688
        for key, figure in rows:
            c.drawString(72, y, template.ALL_LINE_BY_KEY[key].label)
            c.drawRightString(440, y, figure)
            y -= 15
        c.drawString(72, 40, "SYNTHETIC - FOR DEMONSTRATION")
        c.showPage()
    c.save()
    return buf.getvalue()


def _answer(drop: str | None = None) -> dict:
    cells = []
    for page, rows in ROWS.items():
        for key, figure in rows:
            line = template.ALL_LINE_BY_KEY[key]
            cells.append({"key": template.STATED_PREFIX + key if line.computed else key, "page": page,
                          "printed_figure": figure, "printed_label": line.label, "column_header": CUR})
    if drop:
        cells = [c for c in cells if c["key"] != drop]
    return {"scale_statement": "(in thousands)", "scale_page": 1, "cells": cells, "comparative_cells": [],
            "absent_keys": [], "notes": []}


@pytest.fixture()
def vc(db, tmp_path, monkeypatch):
    monkeypatch.setenv("FILE_STORE_DIR", str(tmp_path))
    get_settings.cache_clear()
    b = Borrower(code="VCQ", name="Quillfeather Labs, Inc.", template_id="vc-1")
    db.add(b)
    db.flush()
    yield b
    get_settings.cache_clear()


def _spread(db, b, answer, prior_cash=PRIOR_FYE_CASH):
    doc = ingest_pdf(db, borrower_id=b.id, data=_pdf(), file_name="q3-2026.pdf", doc_type="interim_statements",
                     doc_type_source="system", period_end=PERIOD)
    llm = ScriptedClient([LLMResponse(content=[{"type": "text", "text": json.dumps(answer)}], stop_reason="end_turn")])
    return spread_document(db, borrower=b, document=doc, period_end=PERIOD, months=9, cycle=None, llm=llm,
                           prior_fye_cash=prior_cash)


def test_a_complete_venture_spread_is_stored_with_totals(db, vc):
    result = _spread(db, vc, _answer())
    assert result.failed_checks == [] and result.status == "spread", (result.failed_checks, result.unverified)
    assert current_fact(db, vc.id, "bs.vc_total_assets", PERIOD, 0).value == D("8200000")


def test_a_venture_spread_missing_a_required_total_is_not_finalised_silently(db, vc):
    result = _spread(db, vc, _answer(drop="stated.is.vc_net_loss"))
    assert {e["key"] for e in result.failed_checks if e["code"] == "total_not_read"} == {"is.vc_net_loss"}
    assert result.status == "needs_person"
    assert db.execute(select(WorkItem).where(WorkItem.item_type == "spread.does_not_foot")).first() is not None
    assert current_fact(db, vc.id, "bs.vc_total_assets", PERIOD, 0) is None


def test_the_venture_cash_roll_is_checked_not_skipped(db, vc):
    result = _spread(db, vc, _answer(), prior_cash=D("3000000"))  # the statements imply 4,100,000
    assert "cash_roll_mismatch" in {e["code"] for e in result.failed_checks}


def test_the_repair_path_looks_up_the_venture_cash_roll_key(db, vc):
    _spread(db, vc, _answer())
    add_fact(db, borrower_id=vc.id, key="bs.vc_total_cash", period_end=PRIOR_FYE, months=0, value=D("3000000"),
             kind="seeded")
    result = finalize_spread(db, borrower=vc, document=None, period_end=PERIOD, months=9, scale=1000, absent=[],
                             cycle=None)
    assert "cash_roll_mismatch" in {e["code"] for e in result.failed_checks}


def test_the_spreading_stage_passes_the_prior_year_total_cash_for_a_venture_borrower(db, vc, monkeypatch):
    add_fact(db, borrower_id=vc.id, key="bs.vc_total_cash", period_end=PRIOR_FYE, months=0, value=PRIOR_FYE_CASH,
             kind="seeded")
    doc = ingest_pdf(db, borrower_id=vc.id, data=_pdf(), file_name="q3-2026.pdf", doc_type="interim_statements",
                     doc_type_source="system", period_end=PERIOD)
    cycle = Cycle(borrower_id=vc.id, period_end=PERIOD, months=9, cycle_type="quarterly")
    db.add(cycle)
    db.flush()
    seen = {}

    def fake(db_, **kw):
        seen.update(kw)
        return spreading.SpreadResult(status="needs_person")

    monkeypatch.setattr(stages.spreading, "spread_document", fake)
    monkeypatch.setattr(stages, "_llm", lambda: None)
    stages.spreading_stage(db, cycle, type("St", (), {"detail": {}})())
    assert seen["prior_fye_cash"] == PRIOR_FYE_CASH and seen["document"].id == doc.id


def test_the_calculation_records_the_borrowers_template_not_the_default(db, vc):
    from app.domain.facts import CalcRun
    _spread(db, vc, _answer())
    runs = db.execute(select(CalcRun).where(CalcRun.borrower_id == vc.id,
                                            CalcRun.formula_key == "template_totals")).scalars().all()
    assert runs and {(r.formula_version, r.engine_version) for r in runs} == {("vc-1", "template-vc-1")}


def test_an_optional_line_listed_as_absent_is_never_filed_as_a_zero(db, vc):
    answer = _answer()
    answer["absent_keys"] = ["saas.net_new_arr", "is.vc_stock_based_compensation", "saas.net_revenue_retention"]
    result = _spread(db, vc, answer)
    assert result.status == "spread", result.failed_checks
    for key in answer["absent_keys"]:
        assert current_fact(db, vc.id, key, PERIOD, 0 if key.startswith("saas") else 9) is None


def test_an_optional_line_that_is_printed_is_stored_and_changes_no_total(db, vc, monkeypatch):
    memo = ("is.vc_stock_based_compensation", "5,000")
    monkeypatch.setitem(ROWS, 1, [*ROWS[1], memo])
    answer = _answer()
    result = _spread(db, vc, answer)
    assert result.status == "spread", (result.failed_checks, result.unverified)
    assert current_fact(db, vc.id, "is.vc_stock_based_compensation", PERIOD, 9).value == D("5000000")
    assert current_fact(db, vc.id, "is.vc_net_loss", PERIOD, 9).value == D("-3250000")  # footing unchanged
