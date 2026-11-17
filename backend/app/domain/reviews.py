"""Portfolio review: review sheets, commentary, meetings, actions, packages and snapshots."""
from sqlalchemy import Integer, UniqueConstraint

from app.core.db import Base, CreatedMixin, IdMixin
from app.domain.common import (
    Any,
    Date,
    DateTime,
    Mapped,
    String,
    Text,
    date,
    datetime,
    fk,
    json_col,
    mapped_column,
    uuid,
)


class ReviewMeeting(Base, IdMixin, CreatedMixin):
    __tablename__ = "review_meetings"

    title: Mapped[str] = mapped_column(String(200))
    meeting_date: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    phase: Mapped[str] = mapped_column(String(12), default="before")  # before | during | after | closed
    chair_id: Mapped[uuid.UUID | None] = fk("users.id", nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class ReviewSheet(Base, IdMixin, CreatedMixin):
    __tablename__ = "review_sheets"
    __table_args__ = (UniqueConstraint("cycle_id"),)

    borrower_id: Mapped[uuid.UUID] = fk("borrowers.id")
    cycle_id: Mapped[uuid.UUID] = fk("cycles.id")
    meeting_id: Mapped[uuid.UUID | None] = fk("review_meetings.id", nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft | ready | reviewed | released
    content: Mapped[dict[str, Any]] = json_col(default=dict)  # structured sections referencing fact ids
    changes_since_last: Mapped[list[Any]] = json_col(default=list)
    approved_by: Mapped[uuid.UUID | None] = fk("users.id", nullable=True, index=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Commentary(Base, IdMixin, CreatedMixin):
    """Versioned commentary. Agent drafts are marked as such until a person approves them."""

    __tablename__ = "commentary"

    borrower_id: Mapped[uuid.UUID] = fk("borrowers.id")
    review_sheet_id: Mapped[uuid.UUID | None] = fk("review_sheets.id", nullable=True)
    section: Mapped[str] = mapped_column(String(48))  # summary | performance | covenants | collateral | risks | outlook | note
    version: Mapped[int] = mapped_column(Integer, default=1)
    body: Mapped[str] = mapped_column(Text)  # text with {{fact:<id>}} references; code renders figures
    fact_ids: Mapped[list[str]] = json_col(default=list)
    author_type: Mapped[str] = mapped_column(String(8))  # agent | user
    author_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft | approved | superseded
    approved_by: Mapped[uuid.UUID | None] = fk("users.id", nullable=True, index=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    agent_run_id: Mapped[uuid.UUID | None] = fk("agent_runs.id", nullable=True)


class Action(Base, IdMixin, CreatedMixin):
    __tablename__ = "actions"

    borrower_id: Mapped[uuid.UUID] = fk("borrowers.id")
    cycle_id: Mapped[uuid.UUID | None] = fk("cycles.id", nullable=True)
    meeting_id: Mapped[uuid.UUID | None] = fk("review_meetings.id", nullable=True)
    work_item_id: Mapped[uuid.UUID | None] = fk("work_items.id", nullable=True)
    title: Mapped[str] = mapped_column(String(240))
    detail: Mapped[str] = mapped_column(Text, default="")
    owner_id: Mapped[uuid.UUID | None] = fk("users.id", nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="open")  # open | in_progress | done | cancelled
    escalated: Mapped[bool] = mapped_column(default=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closing_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    raised_by: Mapped[uuid.UUID | None] = fk("users.id", nullable=True, index=False)


class Package(Base, IdMixin, CreatedMixin):
    __tablename__ = "packages"

    title: Mapped[str] = mapped_column(String(240))
    scope: Mapped[str] = mapped_column(String(16))  # borrower | portfolio | meeting
    borrower_id: Mapped[uuid.UUID | None] = fk("borrowers.id", nullable=True)
    meeting_id: Mapped[uuid.UUID | None] = fk("review_meetings.id", nullable=True)
    period_end: Mapped[date] = mapped_column(Date)
    trigger: Mapped[str] = mapped_column(String(12), default="on_demand")  # on_demand | scheduled
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft | generated | released
    files: Mapped[list[Any]] = json_col(default=list)  # [{format, path, sha256, fact_ids}]
    snapshot_id: Mapped[uuid.UUID | None] = fk("snapshots.id", nullable=True)
    prepared_by_id: Mapped[str] = mapped_column(String(64), default="system")
    released_by: Mapped[uuid.UUID | None] = fk("users.id", nullable=True, index=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Snapshot(Base, IdMixin, CreatedMixin):
    """Frozen copy of everything behind a released package, kept for audit as of a date."""

    __tablename__ = "snapshots"

    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scope: Mapped[str] = mapped_column(String(16))
    borrower_id: Mapped[uuid.UUID | None] = fk("borrowers.id", nullable=True)
    content: Mapped[dict[str, Any]] = json_col(default=dict)
    sha256: Mapped[str] = mapped_column(String(64))


class PackageSchedule(Base, IdMixin, CreatedMixin):
    __tablename__ = "package_schedules"

    title: Mapped[str] = mapped_column(String(240))
    scope: Mapped[str] = mapped_column(String(16))
    borrower_id: Mapped[uuid.UUID | None] = fk("borrowers.id", nullable=True)
    cadence: Mapped[str] = mapped_column(String(16))  # monthly | quarterly
    days_after_period_end: Mapped[int] = mapped_column(Integer, default=60)
    formats: Mapped[list[str]] = json_col(default=list)
    active: Mapped[bool] = mapped_column(default=True)
    next_run: Mapped[date | None] = mapped_column(Date, nullable=True)
