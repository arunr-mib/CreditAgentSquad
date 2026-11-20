"""Spreadsheets are documents: one text page per sheet, every line citing its cell."""
import hashlib

import pytest
from app.domain.credit import Borrower
from app.domain.documents import DocumentPage
from app.domain.documents_service import DocumentRefused, ingest_document
from app.domain.spreadsheets import spreadsheet_pages
from sqlalchemy import select

from evals.book import generate_book


@pytest.fixture(scope="module")
def export(tmp_path_factory) -> bytes:
    root = generate_book(tmp_path_factory.mktemp("sheet-book") / "out", "innovation")
    return (root / "documents/stripple-tech/mrr_export.xlsx").read_bytes()


@pytest.fixture()
def borrower(db, tmp_path, monkeypatch):
    monkeypatch.setenv("FILE_STORE_DIR", str(tmp_path))
    from app.core.config import get_settings
    get_settings.cache_clear()
    b = Borrower(code="T-001", name="Test Borrower")
    db.add(b)
    db.flush()
    yield b
    get_settings.cache_clear()


def test_each_sheet_becomes_a_page_of_cell_cited_lines(export):
    pages = spreadsheet_pages(export, "mrr_export.xlsx")
    assert pages and all(p.lines for p in pages)
    assert all("!" in line and " | " in line for p in pages for line in p.lines)
    assert all(line.split(" | ")[0].split("!")[1] in p.cells for p in pages for line in p.lines)


def test_the_export_is_ingested_as_a_document_with_cell_level_text(db, borrower, export):
    doc = ingest_document(db, borrower_id=borrower.id, data=export, file_name="mrr_export.xlsx")
    pages = db.execute(select(DocumentPage).where(DocumentPage.document_id == doc.id)).scalars().all()
    assert doc.file_name.endswith(".xlsx") and doc.meta["format"] == "xlsx" and doc.page_count == len(pages)
    assert doc.storage_path.endswith(".xlsx") and doc.sha256 == hashlib.sha256(export).hexdigest()
    assert all(p.words == [] and p.has_text and "!" in p.text for p in pages)


def test_a_csv_is_ingested_as_one_sheet_and_garbage_is_refused(db, borrower):
    doc = ingest_document(db, borrower_id=borrower.id, data=b"Month,MRR\n2025-01,100\n", file_name="m.csv")
    assert doc.meta["format"] == "csv" and doc.page_count == 1
    for data, name in ((b"MZ\x00\x00", "x.exe"), (b"MZ\x00\x00", "x.xlsx"), (b"not a pdf", "x.pdf")):
        with pytest.raises(DocumentRefused):
            ingest_document(db, borrower_id=borrower.id, data=data, file_name=name)


def test_the_export_is_held_with_one_question_and_never_filed(innovation_cycle):
    from app.domain.documents import Document
    from app.domain.monitoring import WorkItem

    db, row, _cycle = innovation_cycle("stripple-tech", through="spreading")
    sheet = db.execute(select(Document).where(Document.borrower_id == row.id,
                                              Document.file_name == "mrr_export.xlsx")).scalar_one()
    assert sheet.doc_type is None and sheet.meta["format"] == "xlsx"
    held = db.execute(select(WorkItem).where(WorkItem.borrower_id == row.id,
                                             WorkItem.item_type == "intake.unclassified")).scalars().all()
    assert len(held) == 1 and "mrr_export.xlsx" in held[0].title
