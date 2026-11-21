"""Receive a PDF, keep the file, and index it page by page with word positions.

Word positions are what let code find a quoted figure on its page and draw the highlight.
"""
import hashlib
import uuid
from datetime import date
from pathlib import Path

import pymupdf
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import ledger
from app.core.config import get_settings
from app.domain.credit import Borrower
from app.domain.documents import DOCUMENT_TYPES, Document, DocumentPage
from app.domain.spreadsheets import SpreadsheetRefused, spreadsheet_pages

MIN_TEXT_CHARS = 20  # a page with less text than this is treated as an image


class DocumentRefused(Exception):
    pass


def _store(data: bytes, sha: str, suffix: str = ".pdf") -> str:
    root = Path(get_settings().file_store_dir)
    path = root / sha[:2] / f"{sha}{suffix}"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(data)
    return str(path)


def ingest_pdf(
    db: Session,
    *,
    borrower_id: uuid.UUID,
    data: bytes,
    file_name: str,
    title: str | None = None,
    facility_id: uuid.UUID | None = None,
    doc_type: str | None = None,
    doc_type_source: str = "unclassified",
    period_end: date | None = None,
    received_date: date | None = None,
    effective_date: date | None = None,
    source: str = "upload",
    uploaded_by: uuid.UUID | None = None,
    actor: tuple[str, str] = ("system", "intake"),
) -> Document:
    if not data.startswith(b"%PDF"):
        raise DocumentRefused("Only PDF files are accepted.")
    if doc_type is not None and doc_type not in DOCUMENT_TYPES:
        raise DocumentRefused(f"Unknown document type {doc_type!r}.")
    sha = hashlib.sha256(data).hexdigest()
    try:
        pdf = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        raise DocumentRefused(f"The file could not be read as a PDF: {exc}") from exc

    doc = Document(
        borrower_id=borrower_id, facility_id=facility_id, title=title or file_name, file_name=file_name,
        storage_path=_store(data, sha), sha256=sha, page_count=pdf.page_count, doc_type=doc_type,
        doc_type_source=doc_type_source if doc_type else "unclassified", period_end=period_end,
        received_date=received_date, effective_date=effective_date, source=source, uploaded_by=uploaded_by)
    db.add(doc)
    db.flush()

    image_pages: list[int] = []
    for index, page in enumerate(pdf, start=1):
        text = page.get_text("text")
        words = [[round(w[0], 2), round(w[1], 2), round(w[2], 2), round(w[3], 2), w[4]]
                 for w in page.get_text("words")]
        has_text = len(text.strip()) >= MIN_TEXT_CHARS
        if not has_text:
            image_pages.append(index)
        db.add(DocumentPage(document_id=doc.id, page_number=index, text=text, words=words,
                            width=float(page.rect.width), height=float(page.rect.height), has_text=has_text))
    pdf.close()
    doc.meta = {"image_only_pages": image_pages}
    doc.status = "image_only" if image_pages and len(image_pages) == doc.page_count else "indexed"
    ledger.record(db, actor_type=actor[0], actor_id=actor[1], action="document.received",
                  entity_type="document", entity_id=doc.id,
                  payload={"borrower_id": borrower_id, "file_name": file_name, "sha256": sha,
                           "pages": doc.page_count, "image_only_pages": image_pages, "source": source})
    db.flush()
    return doc


def ingest_document(db: Session, *, borrower_id: uuid.UUID, data: bytes, file_name: str, **kwargs) -> Document:
    """A PDF, an .xlsx workbook or a .csv file. Anything else is refused."""
    name = file_name.lower()
    if data.startswith(b"%PDF"):
        return ingest_pdf(db, borrower_id=borrower_id, data=data, file_name=file_name, **kwargs)
    if name.endswith(".csv") or (name.endswith(".xlsx") and data[:2] == b"PK"):
        return _ingest_sheets(db, borrower_id=borrower_id, data=data, file_name=file_name, **kwargs)
    raise DocumentRefused("Only PDF, Excel (.xlsx) and CSV files are accepted.")


def _ingest_sheets(
    db: Session, *, borrower_id: uuid.UUID, data: bytes, file_name: str, title: str | None = None,
    facility_id: uuid.UUID | None = None, doc_type: str | None = None,
    doc_type_source: str = "unclassified", period_end: date | None = None, received_date: date | None = None,
    effective_date: date | None = None, source: str = "upload", uploaded_by: uuid.UUID | None = None,
    actor: tuple[str, str] = ("system", "intake"),
) -> Document:
    if doc_type is not None and doc_type not in DOCUMENT_TYPES:
        raise DocumentRefused(f"Unknown document type {doc_type!r}.")
    kind = "csv" if file_name.lower().endswith(".csv") else "xlsx"
    try:
        sheets = spreadsheet_pages(data, file_name)
    except SpreadsheetRefused as exc:
        raise DocumentRefused(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise DocumentRefused(f"The file could not be read as a spreadsheet: {exc}") from exc
    if not sheets:
        raise DocumentRefused("The spreadsheet has no sheets.")
    sha = hashlib.sha256(data).hexdigest()
    doc = Document(
        borrower_id=borrower_id, facility_id=facility_id, title=title or file_name, file_name=file_name,
        storage_path=_store(data, sha, f".{kind}"), sha256=sha, page_count=len(sheets), doc_type=doc_type,
        doc_type_source=doc_type_source if doc_type else "unclassified", period_end=period_end,
        received_date=received_date, effective_date=effective_date, source=source, uploaded_by=uploaded_by)
    db.add(doc)
    db.flush()
    for index, sheet in enumerate(sheets, start=1):
        db.add(DocumentPage(document_id=doc.id, page_number=index, text="\n".join(sheet.lines), words=[],
                            width=0.0, height=0.0, has_text=bool(sheet.lines)))
    doc.meta = {"image_only_pages": [], "format": kind, "sheets": [s.name for s in sheets],
                "formulas_not_calculated": [f"{s.name}!{ref}" for s in sheets for ref in s.uncalculated]}
    doc.status = "indexed"
    ledger.record(db, actor_type=actor[0], actor_id=actor[1], action="document.received",
                  entity_type="document", entity_id=doc.id,
                  payload={"borrower_id": borrower_id, "file_name": file_name, "sha256": sha, "pages": doc.page_count,
                           "image_only_pages": [], "format": kind, "source": source})
    db.flush()
    return doc


def get_page(db: Session, document_id: uuid.UUID, page_number: int) -> DocumentPage | None:
    return db.execute(select(DocumentPage).where(
        DocumentPage.document_id == document_id, DocumentPage.page_number == page_number)).scalar_one_or_none()


_FALLBACK: dict[str, Path] | None = None


def _fallback_file(sha256: str) -> Path | None:
    """The file with this content hash in the read-only fallback folder, if one is configured."""
    global _FALLBACK
    root = get_settings().file_fallback_dir
    if not root:
        return None
    if _FALLBACK is None:
        _FALLBACK = {hashlib.sha256(path.read_bytes()).hexdigest(): path for path in Path(root).rglob("*") if path.suffix.lower() in (".pdf", ".xlsx", ".csv")}
    return _FALLBACK.get(sha256)


def read_file(doc: Document) -> bytes:
    path = Path(doc.storage_path)
    if not path.exists():
        fallback = _fallback_file(doc.sha256)
        if fallback is not None:
            return fallback.read_bytes()
    return path.read_bytes()


def is_spreadsheet(doc: Document) -> bool:
    return (doc.meta or {}).get("format") in ("xlsx", "csv")


def spreadsheet_unreadable_item(db: Session, *, borrower: Borrower, document: Document, cycle, stage: str,
                                agent: str, facility_id: uuid.UUID | None = None):
    """No agent reads figures from a spreadsheet yet: a person is asked for a PDF or to key the figures."""
    from app.domain.work_items import raise_item

    return raise_item(
        db, borrower_id=borrower.id, facility_id=facility_id, cycle_id=cycle.id if cycle else None, stage=stage,
        item_type="spread.image_only", severity="medium",
        title=f"{document.file_name} is a spreadsheet and cannot be read for figures yet",
        question="This spreadsheet can't be read for figures yet; ask for a PDF or key the figures by hand?",
        allowed_decisions=["request_new_document", "key_by_hand"], required_permission="confirm_spread",
        evidence={"document_id": str(document.id), "format": document.meta.get("format"), "reason": "spreadsheet"},
        actor=("agent", agent), dedupe_key=f"spreadsheet.unreadable:{document.id}")
