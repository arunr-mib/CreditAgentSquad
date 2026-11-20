"""The SaaS lines are filled from the MRR/ARR report, so a financial-statement spread does not need them."""
import io
import json
from decimal import Decimal as D

import pytest
from app.agents.llm import LLMResponse, ScriptedClient
from app.agents.spreading import spread_document
from app.calc import template
from app.calc.template import compute_statement, template_lines
from app.core.config import get_settings
from app.domain.credit import Borrower
from app.domain.documents_service import ingest_pdf
from app.domain.facts_service import current_fact
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from tests.agents.test_spreading_vc import CUR, PERIOD, PRIOR_FYE_CASH, ROWS, _answer, _spread

SAAS = ("saas.mrr", "saas.arr", "saas.customers")
SAAS_ROWS = [("saas.mrr", "400"), ("saas.arr", "4,800"), ("saas.customers", "120")]


@pytest.fixture()
def vc(db, tmp_path, monkeypatch):
    monkeypatch.setenv("FILE_STORE_DIR", str(tmp_path))
    get_settings.cache_clear()
    b = Borrower(code="VCS", name="Quillfeather Labs, Inc.", template_id="vc-1")
    db.add(b)
    db.flush()
    yield b
    get_settings.cache_clear()


def test_the_saas_lines_are_optional_and_in_no_total_for_vc_1_only():
    by_key = {line.key: line for line in template_lines("vc-1")}
    assert all(by_key[k].optional and not by_key[k].computed for k in SAAS)
    used = {c for line in by_key.values() if line.computed for _, c in line.formula}
    assert not used & set(SAAS)
    assert not any(line.optional for line in template_lines("ci-1"))


def test_a_saas_statement_with_no_lines_printed_is_no_error_and_no_zero():
    result = compute_statement({}, statements=["saas"], template_id="vc-1")
    assert result.errors == [] and not set(SAAS) & set(result.values)


def test_a_monthly_pack_with_no_saas_lines_finalises_with_those_keys_null(db, vc, monkeypatch):
    monkeypatch.setitem(ROWS, 3, [r for r in ROWS[3] if not r[0].startswith("saas.")])
    result = _spread(db, vc, _answer())
    assert result.status == "spread", (result.failed_checks, result.unverified)
    for key in SAAS:
        assert current_fact(db, vc.id, key, PERIOD, 0) is None  # null: no fact, and no zero
    assert current_fact(db, vc.id, "bs.vc_total_assets", PERIOD, 0).value == D("8200000")


def test_listing_the_saas_lines_as_absent_files_no_zero(db, vc, monkeypatch):
    monkeypatch.setitem(ROWS, 3, [r for r in ROWS[3] if not r[0].startswith("saas.")])
    answer = _answer()
    answer["absent_keys"] = list(SAAS)
    result = _spread(db, vc, answer)
    assert result.status == "spread", result.failed_checks
    for key in SAAS:
        assert current_fact(db, vc.id, key, PERIOD, 0) is None


def test_the_saas_lines_printed_in_a_pack_are_still_stored(db, vc):
    result = _spread(db, vc, _answer())
    assert result.status == "spread"
    assert current_fact(db, vc.id, "saas.arr", PERIOD, 0).value == D("4800000")
    assert current_fact(db, vc.id, "saas.customers", PERIOD, 0).value == D("120")  # a count, never scaled


def _mrr_pdf() -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, invariant=1)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(72, 740, "Quillfeather Labs, Inc.")
    c.setFont("Helvetica", 9)
    c.drawString(72, 726, f"MRR and ARR report, as of {CUR} (in thousands)")
    c.drawRightString(440, 706, CUR)
    y = 688
    for key, figure in SAAS_ROWS:
        c.drawString(72, y, template.ALL_LINE_BY_KEY[key].label)
        c.drawRightString(440, y, figure)
        y -= 15
    c.drawString(72, 40, "SYNTHETIC - FOR DEMONSTRATION")
    c.showPage()
    c.save()
    return buf.getvalue()


def test_an_mrr_report_spread_stores_the_saas_lines(db, vc):
    cells = [{"key": k, "page": 1, "printed_figure": f, "printed_label": template.ALL_LINE_BY_KEY[k].label,
              "column_header": CUR} for k, f in SAAS_ROWS]
    answer = {"scale_statement": "(in thousands)", "scale_page": 1, "cells": cells, "comparative_cells": [],
              "absent_keys": [], "notes": []}
    doc = ingest_pdf(db, borrower_id=vc.id, data=_mrr_pdf(), file_name="mrr-oct.pdf", doc_type="mrr_report",
                     doc_type_source="system", period_end=PERIOD)
    llm = ScriptedClient([LLMResponse(content=[{"type": "text", "text": json.dumps(answer)}], stop_reason="end_turn")])
    result = spread_document(db, borrower=vc, document=doc, period_end=PERIOD, months=1, cycle=None, llm=llm,
                             prior_fye_cash=PRIOR_FYE_CASH)
    assert result.failed_checks == [] and result.status == "spread", (result.failed_checks, result.unverified)
    assert current_fact(db, vc.id, "saas.mrr", PERIOD, 0).value == D("400000")
    assert current_fact(db, vc.id, "saas.arr", PERIOD, 0).value == D("4800000")
    assert current_fact(db, vc.id, "saas.customers", PERIOD, 0).value == D("120")
