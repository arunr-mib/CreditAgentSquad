"""A venture client's monthly documents can be filed (the book's seed and intake both need these types)."""
import pymupdf
from app.domain.credit import Borrower
from app.domain.documents import DOCUMENT_TYPES
from app.domain.documents_service import ingest_pdf

NEW = ("monthly_financials", "mrr_report", "bank_statement", "term_sheet", "investor_update")


def tiny_pdf() -> bytes:
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Management financial statements for the month ended October 31, 2026")
    return doc.tobytes()


def test_the_monthly_types_are_document_types():
    assert set(NEW) <= set(DOCUMENT_TYPES) and "compliance_certificate" in DOCUMENT_TYPES


def test_a_monthly_document_can_be_filed_by_type(db):
    b = Borrower(code="DOC1", name="Mosswell Robotics", template_id="vc-1")
    db.add(b)
    db.flush()
    for doc_type in NEW:
        doc = ingest_pdf(db, borrower_id=b.id, data=tiny_pdf(), file_name=f"{doc_type}.pdf", doc_type=doc_type,
                         doc_type_source="system", source="seed", actor=("system", "seed"))
        assert doc.doc_type == doc_type
