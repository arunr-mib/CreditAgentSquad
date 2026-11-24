"""Facts: every number the product shows, with where it came from. Facts are never edited."""
from sqlalchemy import BigInteger, CheckConstraint, Identity, Index, Integer

from app.core.db import Base, CreatedMixin, IdMixin
from app.domain.common import (
    Any,
    Date,
    DateTime,
    Decimal,
    Mapped,
    String,
    Text,
    date,
    datetime,
    fk,
    json_col,
    mapped_column,
    money,
    uuid,
)

FACT_KINDS = ("extracted", "calculated", "system", "manual", "seeded")
FACT_STATUSES = ("proposed", "verified", "confirmed", "rejected", "superseded")
# A fact may be used in a calculation when a person or code has cleared it.
USABLE_STATUSES = ("verified", "confirmed")


class Fact(Base, IdMixin, CreatedMixin):
    __tablename__ = "facts"
    __table_args__ = (
        CheckConstraint("kind IN ('extracted','calculated','system','manual','seeded')", name="kind"),
        CheckConstraint(
            "status IN ('proposed','verified','confirmed','rejected','superseded')", name="status"
        ),
        CheckConstraint(
            "kind <> 'extracted' OR (document_id IS NOT NULL AND page IS NOT NULL AND quote IS NOT NULL)",
            name="extracted_has_source",
        ),
        CheckConstraint("kind <> 'calculated' OR calc_run_id IS NOT NULL", name="calculated_has_calc"),
        CheckConstraint(
            "kind <> 'manual' OR (entered_by IS NOT NULL AND reason IS NOT NULL)", name="manual_has_person"
        ),
        Index("ix_facts_lookup", "borrower_id", "key", "period_end", "months"),
    )

    # the order facts were written in, assigned by the database. "The latest fact" is decided by
    # this, never by a timestamp: see docs/lessons/latest-means-a-sequence-not-a-timestamp.md
    seq: Mapped[int] = mapped_column(BigInteger, Identity(), unique=True)
    borrower_id: Mapped[uuid.UUID] = fk("borrowers.id")
    facility_id: Mapped[uuid.UUID | None] = fk("facilities.id", nullable=True)
    key: Mapped[str] = mapped_column(String(96))  # template line, metric, or reported item
    period_end: Mapped[date] = mapped_column(Date)
    months: Mapped[int] = mapped_column(Integer, default=0)  # 0 = point in time; 3, 6, 9, 12 = year to date
    value: Mapped[Decimal] = money(nullable=False)
    unit: Mapped[str] = mapped_column(String(12), default="usd")  # usd | ratio | days | pct | count
    kind: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="proposed")
    # extracted
    document_id: Mapped[uuid.UUID | None] = fk("documents.id", nullable=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bbox: Mapped[list[float] | None] = json_col(nullable=True)
    quote: Mapped[str | None] = mapped_column(Text, nullable=True)  # the figure exactly as printed
    label_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # the row label as printed
    scale_as_reported: Mapped[int | None] = mapped_column(Integer, nullable=True)
    agent_run_id: Mapped[uuid.UUID | None] = fk("agent_runs.id", nullable=True)
    # calculated
    calc_run_id: Mapped[uuid.UUID | None] = fk("calc_runs.id", nullable=True)
    # system of record
    connector: Mapped[str | None] = mapped_column(String(48), nullable=True)
    record_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    as_of: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # entered by a person
    entered_by: Mapped[uuid.UUID | None] = fk("users.id", nullable=True, index=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # history
    supersedes_fact_id: Mapped[uuid.UUID | None] = fk("facts.id", nullable=True)
    confirmed_by: Mapped[uuid.UUID | None] = fk("users.id", nullable=True, index=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class CalcRun(Base, IdMixin, CreatedMixin):
    __tablename__ = "calc_runs"

    borrower_id: Mapped[uuid.UUID] = fk("borrowers.id")
    formula_key: Mapped[str] = mapped_column(String(96), index=True)
    formula_version: Mapped[str] = mapped_column(String(32))
    terms_version_id: Mapped[uuid.UUID | None] = fk("terms_versions.id", nullable=True)
    period_end: Mapped[date] = mapped_column(Date)
    inputs: Mapped[list[Any]] = json_col(default=list)  # [{name, key, period_end, months, fact_id, value}]
    outputs: Mapped[dict[str, Any]] = json_col(default=dict)
    trace: Mapped[dict[str, Any]] = json_col(default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    engine_version: Mapped[str] = mapped_column(String(32))
    created_by_type: Mapped[str] = mapped_column(String(16), default="system")  # user | agent | system
    created_by_id: Mapped[str] = mapped_column(String(64), default="system")
