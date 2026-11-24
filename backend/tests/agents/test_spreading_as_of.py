"""An MRR report or bank statement is read for the period only when its own stated date is the period."""
import io
import json

import pytest
from app.agents.llm import LLMResponse, ScriptedClient
from app.agents.spreading import spread_document
from app.core.config import get_settings
from app.domain.credit import Borrower
from app.domain.documents_service import ingest_pdf
from app.domain.facts import Fact
from app.domain.facts_service import current_fact
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import select
from tests.agents.test_spreading_vc import CUR, PERIOD

AUG = "August 31, 2026"


@pytest.fixture()
def vc(db, tmp_path, monkeypatch):
    monkeypatch.setenv("FILE_STORE_DIR", str(tmp_path))
    get_settings.cache_clear()
    b = Borrower(code="ASO", name="Quillfeather Labs, Inc.", template_id="vc-1")
    db.add(b)
    db.flush()
    yield b
    get_settings.cache_clear()


def _mrr(header_date: str, mention: str | None = None) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, invariant=1)
    c.setFont("Helvetica", 9)
    c.drawString(72, 740, "Quillfeather Labs, Inc.")
    c.drawString(72, 726, "MONTHLY RECURRING REVENUE REPORT")
    c.drawString(72, 712, f"For the month ended {header_date}")
    c.drawString(72, 690, "Metric")
    c.drawRightString(440, 690, f"As of {header_date}")
    c.drawString(72, 674, "Monthly recurring revenue")
    c.drawRightString(440, 674, "$400")
    c.drawString(72, 640, "Trailing months")
    c.drawString(72, 626, "Month")
    c.drawRightString(300, 626, "MRR")
    c.drawRightString(440, 626, "Customers")
    c.drawString(72, 612, "August 2026")
    c.drawRightString(300, 612, "$380")
    c.drawRightString(440, 612, "110")
    if mention:
        c.drawString(72, 560, mention)
    c.drawString(72, 40, "SYNTHETIC - FOR DEMONSTRATION")
    c.showPage()
    c.save()
    return buf.getvalue()


def _read(db, vc, pdf, figure, label="Monthly recurring revenue", doc_type="mrr_report", key="saas.mrr"):
    cell = {"key": key, "page": 1, "printed_figure": figure, "printed_label": label, "column_header": CUR}
    answer = {"scale_statement": "", "scale_page": 0, "cells": [cell], "comparative_cells": [],
              "absent_keys": [], "notes": []}
    doc = ingest_pdf(db, borrower_id=vc.id, data=pdf, file_name="x.pdf", doc_type=doc_type,
                     doc_type_source="system", period_end=PERIOD)
    llm = ScriptedClient([LLMResponse(content=[{"type": "text", "text": json.dumps(answer)}], stop_reason="end_turn")])
    return spread_document(db, borrower=vc, document=doc, period_end=PERIOD, months=1, cycle=None, llm=llm,
                           prior_fye_cash=None)


def test_the_period_mrr_is_read(db, vc):
    result = _read(db, vc, _mrr(CUR), "$400")
    assert result.status == "spread", (result.failed_checks, result.unverified)
    assert current_fact(db, vc.id, "saas.mrr", PERIOD, 0).value == 400


def test_a_trend_table_prior_month_figure_is_not_verified_as_the_period(db, vc):
    result = _read(db, vc, _mrr(CUR), "$380")
    assert result.status != "spread"
    fact = current_fact(db, vc.id, "saas.mrr", PERIOD, 0)
    assert fact is None or fact.status != "verified"


def test_a_page_dated_another_month_that_mentions_the_period_is_refused_and_stores_nothing(db, vc):
    result = _read(db, vc, _mrr(AUG, mention=f"Restated through {CUR}."), "$400")
    assert result.status != "spread"
    assert [i.item_type for i in result.work_items] and "wrong_document" in result.work_items[0].allowed_decisions
    assert db.execute(select(Fact).where(Fact.borrower_id == vc.id, Fact.key == "saas.mrr")).first() is None


def _bank(closing: str, mention: str | None = None) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, invariant=1)
    c.setFont("Helvetica", 9)
    c.drawString(72, 740, "Quillfeather Labs, Inc.")
    c.drawString(72, 726, "BANK STATEMENT - OPERATING ACCOUNT")
    c.drawString(72, 712, f"Statement period: July 1, 2026 to {closing}")
    c.drawString(72, 690, "Balance")
    c.drawRightString(440, 690, f"At {closing}")
    c.drawString(72, 674, "Total operating accounts (unrestricted)")
    c.drawRightString(440, 674, "$900")
    if mention:
        c.drawString(72, 560, mention)
    c.drawString(72, 40, "SYNTHETIC - FOR DEMONSTRATION")
    c.showPage()
    c.save()
    return buf.getvalue()


def test_a_bank_statement_closing_in_another_month_is_refused_and_stores_no_fact(db, vc):
    """The statement's own closing date is July 31; the period is the current month, which the page only mentions."""
    result = _read(db, vc, _bank("July 31, 2026", mention=f"Next statement closes {CUR}."), "$900",
                   label="Total operating accounts (unrestricted)", doc_type="bank_statement",
                   key="bank.cash_unrestricted")
    assert result.status != "spread"
    assert [i.item_type for i in result.work_items] and "wrong_document" in result.work_items[0].allowed_decisions
    assert db.execute(select(Fact).where(Fact.borrower_id == vc.id, Fact.key == "bank.cash_unrestricted")).first() is None
