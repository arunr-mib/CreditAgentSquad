import io
from decimal import Decimal as D

import pytest
from app.domain.credit import Borrower
from app.domain.documents_service import DocumentRefused, get_page, ingest_pdf
from app.guardrails.quotes import quote_on_page, verify_cell
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def statement_pdf() -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, invariant=1)
    c.setFont("Helvetica", 10)
    c.drawRightString(440, 700, "September 30, 2026")
    c.drawRightString(560, 700, "September 30, 2025")
    for y, label, cur, prior in [(680, "Net revenue", "$ 48,250", "$ 45,100"),
                                 (665, "Cost of goods sold", "(33,775)", "(31,120)"),
                                 (650, "Gross profit", "14,475", "13,980")]:
        c.drawString(72, y, label)
        c.drawRightString(440, y, cur)
        c.drawRightString(560, y, prior)
    c.drawString(72, 60, "SYNTHETIC - FOR DEMONSTRATION")
    c.showPage()
    c.showPage()  # a blank page stands in for an image-only page
    c.save()
    return buf.getvalue()


@pytest.fixture()
def borrower(db):
    b = Borrower(code="T-001", name="Test Borrower")
    db.add(b)
    db.flush()
    return b


def test_ingest_indexes_pages_and_words_so_cells_can_be_verified(db, borrower, tmp_path, monkeypatch):
    monkeypatch.setenv("FILE_STORE_DIR", str(tmp_path))
    from app.core.config import get_settings
    get_settings.cache_clear()
    doc = ingest_pdf(db, borrower_id=borrower.id, data=statement_pdf(), file_name="q3.pdf",
                     doc_type="interim_statements", doc_type_source="system")
    get_settings.cache_clear()
    assert doc.page_count == 2 and doc.status == "indexed" and doc.meta["image_only_pages"] == [2]
    page = get_page(db, doc.id, 1)
    assert page.has_text and quote_on_page(page.text, "synthetic - for demonstration")
    check = verify_cell(page.words, printed_figure="(33,775)", printed_label="Cost of goods sold",
                        column_header="September 30, 2026")
    assert check.ok and check.value == D("-33775")
    prior = verify_cell(page.words, printed_figure="45,100", printed_label="Net revenue",
                        column_header="September 30, 2026")
    assert prior.status == "column_unconfirmed"
    assert get_page(db, doc.id, 2).has_text is False


def test_non_pdf_and_unknown_type_are_refused(db, borrower):
    with pytest.raises(DocumentRefused):
        ingest_pdf(db, borrower_id=borrower.id, data=b"hello", file_name="x.txt")
    with pytest.raises(DocumentRefused):
        ingest_pdf(db, borrower_id=borrower.id, data=statement_pdf(), file_name="x.pdf", doc_type="memo")
