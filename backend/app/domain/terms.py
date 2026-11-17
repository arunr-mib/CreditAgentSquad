"""Covenant terms: versioned, effective-dated, approved by a second person, never overwritten."""
from sqlalchemy import CheckConstraint, Index, Integer, UniqueConstraint

from app.core.db import Base, CreatedMixin, IdMixin
from app.domain.common import (
    Any,
    Date,
    DateTime,
    Mapped,
    String,
    date,
    datetime,
    fk,
    json_col,
    mapped_column,
    uuid,
)


class TermsVersion(Base, IdMixin, CreatedMixin):
    __tablename__ = "terms_versions"
    __table_args__ = (
        UniqueConstraint("facility_id", "version"),
        CheckConstraint("status IN ('proposed','approved','superseded','rejected')", name="status"),
        CheckConstraint(
            "status NOT IN ('approved','superseded') OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)",
            name="approved_has_approver",
        ),
        # only one approved, open-ended version per loan
        Index(
            "uq_terms_one_open_approved", "facility_id", unique=True,
            postgresql_where="status = 'approved' AND effective_to IS NULL",
        ),
    )

    facility_id: Mapped[uuid.UUID] = fk("facilities.id")
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="proposed")
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    terms: Mapped[dict[str, Any]] = json_col()
    source_document_ids: Mapped[list[str]] = json_col(default=list)
    warnings: Mapped[list[Any] | None] = json_col(nullable=True)  # None = never checked; [] = checked, clean
    prepared_by_type: Mapped[str] = mapped_column(String(16), default="agent")  # agent | user | seed
    prepared_by_id: Mapped[str] = mapped_column(String(64), default="")
    approved_by: Mapped[uuid.UUID | None] = fk("users.id", nullable=True, index=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    agent_run_id: Mapped[uuid.UUID | None] = fk("agent_runs.id", nullable=True)


class ReportingObligation(Base, IdMixin, CreatedMixin):
    """One dated instance of a reporting requirement: the calendar is built from these."""

    __tablename__ = "reporting_obligations"
    __table_args__ = (UniqueConstraint("facility_id", "requirement_id", "period_end"),)

    borrower_id: Mapped[uuid.UUID] = fk("borrowers.id")
    facility_id: Mapped[uuid.UUID] = fk("facilities.id")
    terms_version_id: Mapped[uuid.UUID | None] = fk("terms_versions.id", nullable=True)
    requirement_id: Mapped[str] = mapped_column(String(64))
    document_type: Mapped[str] = mapped_column(String(48))
    period_end: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(16), default="due")  # due | received | overdue | waived
    received_document_id: Mapped[uuid.UUID | None] = fk("documents.id", nullable=True)
    received_date: Mapped[date | None] = mapped_column(Date, nullable=True)
