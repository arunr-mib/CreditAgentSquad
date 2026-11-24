"""Documents received from borrowers, kept page by page so every figure can cite its place."""
from sqlalchemy import Integer, UniqueConstraint

from app.core.db import Base, CreatedMixin, IdMixin
from app.domain.common import (
    Any,
    Date,
    Mapped,
    String,
    Text,
    date,
    fk,
    json_col,
    mapped_column,
    uuid,
)

DOCUMENT_TYPES = (
    "credit_agreement", "amendment", "waiver", "annual_statements", "interim_statements",
    "compliance_certificate", "borrowing_base_certificate", "receivables_aging", "tax_return",
    "monthly_financials", "mrr_report", "bank_statement", "term_sheet", "investor_update", "other",
)


class Document(Base, IdMixin, CreatedMixin):
    __tablename__ = "documents"

    borrower_id: Mapped[uuid.UUID] = fk("borrowers.id")
    facility_id: Mapped[uuid.UUID | None] = fk("facilities.id", nullable=True)
    title: Mapped[str] = mapped_column(String(300))
    file_name: Mapped[str] = mapped_column(String(300))
    storage_path: Mapped[str] = mapped_column(String(500))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    doc_type: Mapped[str | None] = mapped_column(String(48), nullable=True)  # set by Intake, confirmed by code or a person
    doc_type_source: Mapped[str] = mapped_column(String(16), default="unclassified")  # agent | person | system | unclassified
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    received_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # agreements and amendments
    source: Mapped[str] = mapped_column(String(32), default="upload")  # upload | connector | seed
    status: Mapped[str] = mapped_column(String(24), default="received")  # received | indexed | image_only | rejected
    meta: Mapped[dict[str, Any]] = json_col(default=dict)
    uploaded_by: Mapped[uuid.UUID | None] = fk("users.id", nullable=True, index=False)


class DocumentPage(Base, IdMixin):
    __tablename__ = "document_pages"
    __table_args__ = (UniqueConstraint("document_id", "page_number"),)

    document_id: Mapped[uuid.UUID] = fk("documents.id")
    page_number: Mapped[int] = mapped_column(Integer)  # 1-based
    text: Mapped[str] = mapped_column(Text, default="")
    words: Mapped[list[Any]] = json_col(default=list)  # [[x0, y0, x1, y1, "word"], ...] in PDF points
    width: Mapped[float] = mapped_column(default=0.0)
    height: Mapped[float] = mapped_column(default=0.0)
    has_text: Mapped[bool] = mapped_column(default=True)
