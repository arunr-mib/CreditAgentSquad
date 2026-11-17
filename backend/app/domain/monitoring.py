"""The monitoring cycle: one borrower, one period, tracked stage by stage."""
from sqlalchemy import Index, Integer, UniqueConstraint

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

STAGES = (
    "awaiting_package", "intake", "spreading", "covenant_testing", "borrowing_base", "signals",
    "review_prep", "in_review", "actions_open", "closed",
)
STAGE_STATUSES = ("pending", "running", "needs_person", "done", "skipped", "failed")
COVENANT_OUTCOMES = ("compliant", "compliant_variance", "breach", "breach_reported_compliant", "cannot_test")
RECOMMENDATIONS = ("resolve", "escalate", "request", "abstain")


class Cycle(Base, IdMixin, CreatedMixin):
    __tablename__ = "cycles"
    __table_args__ = (UniqueConstraint("borrower_id", "period_end", "cycle_type"),)

    borrower_id: Mapped[uuid.UUID] = fk("borrowers.id")
    period_end: Mapped[date] = mapped_column(Date, index=True)
    months: Mapped[int] = mapped_column(Integer, default=3)
    cycle_type: Mapped[str] = mapped_column(String(16), default="quarterly")  # quarterly | annual | monthly
    stage: Mapped[str] = mapped_column(String(24), default="awaiting_package")
    status: Mapped[str] = mapped_column(String(16), default="open")  # open | closed
    origin: Mapped[str] = mapped_column(String(16), default="live")  # live | seeded (history from ground truth)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary: Mapped[dict[str, Any]] = json_col(default=dict)


class CycleStage(Base, IdMixin):
    __tablename__ = "cycle_stages"
    __table_args__ = (UniqueConstraint("cycle_id", "stage"),)

    cycle_id: Mapped[uuid.UUID] = fk("cycles.id")
    stage: Mapped[str] = mapped_column(String(24))
    position: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detail: Mapped[dict[str, Any]] = json_col(default=dict)


class Job(Base, IdMixin, CreatedMixin):
    """Work queue on Postgres. Workers claim rows with FOR UPDATE SKIP LOCKED."""

    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_claim", "status", "run_after"),)

    kind: Mapped[str] = mapped_column(String(64))
    cycle_id: Mapped[uuid.UUID | None] = fk("cycles.id", nullable=True)
    payload: Mapped[dict[str, Any]] = json_col(default=dict)
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued | running | done | failed
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=2)
    run_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class WorkItem(Base, IdMixin, CreatedMixin):
    """An exception: one specific question for a person, with evidence and allowed decisions."""

    __tablename__ = "work_items"

    borrower_id: Mapped[uuid.UUID] = fk("borrowers.id")
    facility_id: Mapped[uuid.UUID | None] = fk("facilities.id", nullable=True)
    cycle_id: Mapped[uuid.UUID | None] = fk("cycles.id", nullable=True)
    stage: Mapped[str | None] = mapped_column(String(24), nullable=True)
    item_type: Mapped[str] = mapped_column(String(48), index=True)
    severity: Mapped[str] = mapped_column(String(12), default="medium")  # low | medium | high | critical
    title: Mapped[str] = mapped_column(String(240))
    question: Mapped[str] = mapped_column(Text)
    allowed_decisions: Mapped[list[str]] = json_col(default=list)
    evidence: Mapped[dict[str, Any]] = json_col(default=dict)  # fact ids, document pages, calc ids, test ids
    recommendation: Mapped[dict[str, Any] | None] = json_col(nullable=True)  # the agent's, if any
    guardrail_notes: Mapped[list[Any]] = json_col(default=list)
    blocks_stage: Mapped[bool] = mapped_column(default=True)
    requires_second_person: Mapped[bool] = mapped_column(default=False)
    required_permission: Mapped[str] = mapped_column(String(32), default="decide_work_item")
    prepared_by_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    assigned_to: Mapped[uuid.UUID | None] = fk("users.id", nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="open", index=True)  # open | decided | dismissed
    decision: Mapped[str | None] = mapped_column(String(48), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[uuid.UUID | None] = fk("users.id", nullable=True, index=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    agent_run_id: Mapped[uuid.UUID | None] = fk("agent_runs.id", nullable=True)


class CovenantTest(Base, IdMixin, CreatedMixin):
    __tablename__ = "covenant_tests"
    __table_args__ = (Index("ix_covenant_tests_lookup", "facility_id", "covenant_id", "period_end"),)

    borrower_id: Mapped[uuid.UUID] = fk("borrowers.id")
    facility_id: Mapped[uuid.UUID] = fk("facilities.id")
    cycle_id: Mapped[uuid.UUID | None] = fk("cycles.id", nullable=True)
    terms_version_id: Mapped[uuid.UUID | None] = fk("terms_versions.id", nullable=True)
    covenant_id: Mapped[str] = mapped_column(String(64))
    covenant_name: Mapped[str] = mapped_column(String(160))
    period_end: Mapped[date] = mapped_column(Date)
    calc_run_id: Mapped[uuid.UUID | None] = fk("calc_runs.id", nullable=True)
    value_fact_id: Mapped[uuid.UUID | None] = fk("facts.id", nullable=True)
    value: Mapped[Decimal | None] = money()
    threshold: Mapped[Decimal | None] = money()
    operator: Mapped[str | None] = mapped_column(String(4), nullable=True)
    unit: Mapped[str] = mapped_column(String(12), default="ratio")
    passed: Mapped[bool | None] = mapped_column(nullable=True)
    headroom: Mapped[Decimal | None] = money()
    headroom_pct: Mapped[Decimal | None] = money()
    reported_value: Mapped[Decimal | None] = money()
    reported_in_compliance: Mapped[bool | None] = mapped_column(nullable=True)
    reported_fact_id: Mapped[uuid.UUID | None] = fk("facts.id", nullable=True, index=False)
    outcome: Mapped[str] = mapped_column(String(32))
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    origin: Mapped[str] = mapped_column(String(16), default="live")  # live | seeded
    superseded: Mapped[bool] = mapped_column(default=False)


class BorrowingBaseReview(Base, IdMixin, CreatedMixin):
    __tablename__ = "borrowing_base_reviews"

    borrower_id: Mapped[uuid.UUID] = fk("borrowers.id")
    facility_id: Mapped[uuid.UUID] = fk("facilities.id")
    cycle_id: Mapped[uuid.UUID | None] = fk("cycles.id", nullable=True)
    terms_version_id: Mapped[uuid.UUID | None] = fk("terms_versions.id", nullable=True)
    period_end: Mapped[date] = mapped_column(Date)
    calc_run_id: Mapped[uuid.UUID | None] = fk("calc_runs.id", nullable=True)
    computed: Mapped[dict[str, Any]] = json_col(default=dict)
    certificate: Mapped[dict[str, Any]] = json_col(default=dict)
    differences: Mapped[list[Any]] = json_col(default=list)
    availability: Mapped[Decimal | None] = money()
    over_advance: Mapped[Decimal | None] = money()
    outcome: Mapped[str] = mapped_column(String(32), default="agrees")  # agrees | mismatch | over_advance | cannot_compute
    origin: Mapped[str] = mapped_column(String(16), default="live")


class Signal(Base, IdMixin, CreatedMixin):
    __tablename__ = "signals"

    borrower_id: Mapped[uuid.UUID] = fk("borrowers.id")
    cycle_id: Mapped[uuid.UUID | None] = fk("cycles.id", nullable=True)
    period_end: Mapped[date] = mapped_column(Date)
    rule_id: Mapped[str] = mapped_column(String(64), index=True)
    rule_version: Mapped[str] = mapped_column(String(24))
    severity: Mapped[str] = mapped_column(String(12))
    basis: Mapped[dict[str, Any]] = json_col(default=dict)  # values compared, their periods and fact ids
    explanation: Mapped[dict[str, Any] | None] = json_col(nullable=True)  # agent text with fact references
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="open")  # open | acknowledged | closed
    acknowledged_by: Mapped[uuid.UUID | None] = fk("users.id", nullable=True, index=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    origin: Mapped[str] = mapped_column(String(16), default="live")
