"""Borrowers and their loans. The schema says `facility`; the workspace says "loan"."""
from sqlalchemy import CheckConstraint, Integer

from app.core.db import Base, CreatedMixin, IdMixin
from app.domain.common import (
    Any,
    Date,
    Decimal,
    Mapped,
    String,
    date,
    fk,
    json_col,
    mapped_column,
    money,
    uuid,
)


class Borrower(Base, IdMixin, CreatedMixin):
    __tablename__ = "borrowers"
    __table_args__ = (CheckConstraint("template_id IN ('ci-1','vc-1')", name="template_id"),)

    code: Mapped[str] = mapped_column(String(32), unique=True)  # stable id from the system of record
    name: Mapped[str] = mapped_column(String(200))
    industry: Mapped[str] = mapped_column(String(120), default="")
    naics: Mapped[str] = mapped_column(String(12), default="")
    fiscal_year_end_month: Mapped[int] = mapped_column(Integer, default=12)
    risk_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    relationship_manager_id: Mapped[uuid.UUID | None] = fk("users.id", nullable=True)
    analyst_id: Mapped[uuid.UUID | None] = fk("users.id", nullable=True)
    profile: Mapped[dict[str, Any]] = json_col(default=dict)
    # which monitoring template applies: ci-1 commercial and industrial, vc-1 venture
    template_id: Mapped[str] = mapped_column(String(8), server_default="ci-1")


class Facility(Base, IdMixin, CreatedMixin):
    __tablename__ = "facilities"

    borrower_id: Mapped[uuid.UUID] = fk("borrowers.id")
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    facility_type: Mapped[str] = mapped_column(String(32))  # revolver | term_loan
    commitment: Mapped[Decimal] = money(nullable=False)
    has_borrowing_base: Mapped[bool] = mapped_column(default=False)
    origination_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    maturity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    profile: Mapped[dict[str, Any]] = json_col(default=dict)
