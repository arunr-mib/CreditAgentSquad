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
    return (root / "documents/cindrel-tech/mrr_export.xlsx").read_bytes()


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

    db, row, _cycle = innovation_cycle("cindrel-tech", through="spreading")
    sheet = db.execute(select(Document).where(Document.borrower_id == row.id,
                                              Document.file_name == "mrr_export.xlsx")).scalar_one()
    assert sheet.doc_type is None and sheet.meta["format"] == "xlsx"
    held = db.execute(select(WorkItem).where(WorkItem.borrower_id == row.id,
                                             WorkItem.item_type == "intake.unclassified")).scalars().all()
    assert len(held) == 1 and "mrr_export.xlsx" in held[0].title


def _workbook(build) -> bytes:
    import io

    from openpyxl import Workbook
    wb = Workbook()
    build(wb)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_caps_refuse_oversized_files_with_a_plain_reason(db, borrower):
    import io
    import zipfile

    from app.domain import spreadsheets

    def many_sheets(wb):
        for i in range(spreadsheets.MAX_SHEETS + 1):
            wb.create_sheet(f"s{i}")

    for data, name, why in (
        (_workbook(many_sheets), "a.xlsx", "sheets"),
        (_workbook(lambda wb: wb.active.__setitem__("A20001", "x")), "b.xlsx", "rows"),
        (_workbook(lambda wb: wb.active.__setitem__("GT1", "x")), "c.xlsx", "columns"),
    ):
        with pytest.raises(DocumentRefused, match=why):
            ingest_document(db, borrower_id=borrower.id, data=data, file_name=name)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("big.xml", b"0" * (101 * 1024 * 1024))
    with pytest.raises(DocumentRefused, match="too large"):
        ingest_document(db, borrower_id=borrower.id, data=buf.getvalue(), file_name="d.xlsx")


def test_a_declared_huge_dimension_is_refused_without_reading_the_rows():
    import io
    import zipfile

    sheet = ('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
             '<dimension ref="A1:B1000000"/><sheetData/></worksheet>')
    base = _workbook(lambda wb: wb.active.__setitem__("A1", "x"))
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(base)) as zin, zipfile.ZipFile(out, "w") as zout:
        for item in zin.infolist():
            zout.writestr(item, sheet if item.filename == "xl/worksheets/sheet1.xml" else zin.read(item.filename))
    with pytest.raises(Exception, match="rows"):
        spreadsheet_pages(out.getvalue(), "e.xlsx")


def test_formulas_without_a_value_dates_and_numbers_are_worded_canonically():
    import datetime

    def build(wb):
        ws = wb.active
        ws["A1"], ws["B1"], ws["C1"] = "Total", "=1+2", 12.50
        ws["A2"], ws["B2"] = "Day", datetime.datetime(2025, 1, 31)
        ws["A3"], ws["B3"] = "Count", 4.0

    page = spreadsheet_pages(_workbook(build), "f.xlsx")[0]
    assert "Sheet!B1" not in page.lines
    assert any(line.endswith("| =1+2 (formula, not calculated)") for line in page.lines)
    assert page.uncalculated == ["B1"]
    assert "Sheet!C1 | Total | 12.5" in "\n".join(page.lines).replace(page.name, "Sheet")
    assert any(line.endswith("| Day | 2025-01-31") for line in page.lines)
    assert any(line.endswith("| Count | 4") for line in page.lines)


def test_csv_delimiters_encodings_and_binary_are_handled():
    semi = spreadsheet_pages(b"Month;MRR\n2025-01;100\n", "a.csv")[0]
    tab = spreadsheet_pages(b"Month\tMRR\n2025-01\t100\n", "b.csv")[0]
    assert semi.lines == tab.lines and semi.lines[-1].endswith("| 2025-01 | 100")
    cp = spreadsheet_pages("Caf\xe9,MRR\nx,1\n".encode("cp1252"), "c.csv")[0]
    assert any("Caf\xe9" in line or "Caf" in line for line in cp.lines)
    from app.domain.spreadsheets import SpreadsheetRefused
    with pytest.raises(SpreadsheetRefused):
        spreadsheet_pages(b"a,b\n\x00\x01,2\n", "d.csv")


def test_a_pdf_only_agent_raises_a_question_for_a_spreadsheet_and_stores_nothing(db, borrower):
    from app.agents.certificate import read_certificate
    from app.domain.facts import Fact
    from app.domain.monitoring import WorkItem

    class Boom:
        def complete(self, *a, **k):
            raise AssertionError("a spreadsheet must never reach the model")

    from datetime import date
    doc = ingest_document(db, borrower_id=borrower.id, data=b"a,b\nx,1\n", file_name="cert.csv")

    class T:
        covenants: list = []
    result = read_certificate(db, borrower=borrower, document=doc, period_end=date(2026, 10, 31), terms=T(),
                              cycle=None, llm=Boom())
    items = db.execute(select(WorkItem).where(WorkItem.borrower_id == borrower.id)).scalars().all()
    assert len(items) == 1 and items[0].allowed_decisions == ["request_new_document", "key_by_hand"]
    assert items[0].item_type == "document.spreadsheet_unreadable"
    assert "spreadsheet" in items[0].question and result.unverified and not result.stored
    assert db.execute(select(Fact).where(Fact.borrower_id == borrower.id)).first() is None


def test_the_collateral_agent_raises_a_question_for_a_spreadsheet_and_stores_nothing(db, borrower):
    from datetime import date

    from app.agents.collateral import read_collateral
    from app.domain.facts import Fact
    from app.domain.monitoring import WorkItem

    class Boom:
        def complete(self, *a, **k):
            raise AssertionError("a spreadsheet must never reach the model")

    doc = ingest_document(db, borrower_id=borrower.id, data=b"a,b\nx,1\n", file_name="bbc.csv")
    result = read_collateral(db, borrower=borrower, document=doc, period_end=date(2026, 10, 31), cycle=None, llm=Boom())
    items = db.execute(select(WorkItem).where(WorkItem.borrower_id == borrower.id)).scalars().all()
    # a borrowing base has no manual entry, so a person may only ask for a new document
    assert len(items) == 1 and items[0].allowed_decisions == ["request_new_document"]
    assert items[0].item_type == "document.spreadsheet_unreadable" and "spreadsheet" in items[0].question
    assert result.unverified == [{"what": "document", "reason": "spreadsheet"}]
    assert db.execute(select(Fact).where(Fact.borrower_id == borrower.id)).first() is None


def _sheet_item(db, borrower, stage, doc_type=None):
    from app.domain import hooks
    from app.domain.documents_service import spreadsheet_unreadable_item
    doc = ingest_document(db, borrower_id=borrower.id, data=b"a,b\nx,1\n", file_name=f"{stage}.csv")
    doc.doc_type = doc_type
    item = spreadsheet_unreadable_item(db, borrower=borrower, document=doc, cycle=None, stage=stage, agent="test")
    from app.domain.org import User
    user = User(name="P", email=f"p-{stage}-{doc_type}@example.test", role="analyst", password_hash="x")
    db.add(user)
    db.flush()
    return hooks, doc, item, user


@pytest.mark.parametrize("stage,doc_type", [("spreading", None), ("covenant_testing", "compliance_certificate"),
                                            ("covenant_testing", "credit_agreement"), ("borrowing_base", None)])
def test_a_new_document_sets_the_sheet_aside_at_every_stage(db, borrower, stage, doc_type):
    hooks, doc, item, user = _sheet_item(db, borrower, stage, doc_type)
    assert item.item_type == "document.spreadsheet_unreadable" and item.item_type != "spread.image_only"
    hooks.on_spreadsheet_decision(db, item, user, "request_new_document", "send a PDF")
    assert doc.status == "rejected"


def test_keying_by_hand_goes_to_the_stage_that_met_the_sheet(db, borrower, monkeypatch):
    """Spreading keys the spread; a credit agreement's sheet means entering terms; a certificate's means keyed
    certificate figures; a borrowing base has no manual entry and does not offer it."""
    seen = []
    from app.domain import hooks
    monkeypatch.setattr(hooks, "on_spread_decision", lambda db, item, user, d, r: seen.append(("spread", d)))
    monkeypatch.setattr(hooks, "on_terms_extraction_decision", lambda db, item, user, d, r: seen.append(("terms", d)))
    monkeypatch.setattr(hooks, "_certificate_keyed_by_hand", lambda db, item, user, doc: seen.append(("certificate", None)))
    for stage, doc_type in (("spreading", None), ("covenant_testing", "credit_agreement"),
                            ("covenant_testing", "amendment"), ("covenant_testing", "compliance_certificate")):
        _, _, item, user = _sheet_item(db, borrower, stage, doc_type)
        assert "key_by_hand" in item.allowed_decisions
        hooks.on_spreadsheet_decision(db, item, user, "key_by_hand", "keyed")
    assert seen == [("spread", "key_by_hand"), ("terms", "board_by_hand"), ("terms", "board_by_hand"),
                    ("certificate", None)]
    _, _, bb, user = _sheet_item(db, borrower, "borrowing_base")
    assert bb.allowed_decisions == ["request_new_document"]
    with pytest.raises(ValueError, match="cannot be keyed"):
        hooks.on_spreadsheet_decision(db, bb, user, "key_by_hand", "keyed")


def test_keyed_certificate_figures_are_required_before_the_decision_is_accepted(db, borrower):
    hooks, doc, item, user = _sheet_item(db, borrower, "covenant_testing", "compliance_certificate")
    with pytest.raises(ValueError, match="cycle|keyed"):
        hooks.on_spreadsheet_decision(db, item, user, "key_by_hand", "keyed")


def test_empty_cells_that_are_iterated_count_against_a_cap(monkeypatch):
    from app.domain import spreadsheets

    def wide(wb):
        wb.active["A1"] = "x"
        wb.active["J50"] = "y"  # 500 cells iterated, 2 filled
    data = _workbook(wide)
    assert spreadsheet_pages(data, "w.xlsx")  # fine under the real cap
    monkeypatch.setattr(spreadsheets, "MAX_ITERATED_CELLS", 100)
    with pytest.raises(spreadsheets.SpreadsheetRefused, match="cells"):
        spreadsheet_pages(data, "w.xlsx")


def test_openpyxl_parses_workbooks_with_defusedxml():
    import openpyxl.xml
    assert openpyxl.xml.DEFUSEDXML is True
