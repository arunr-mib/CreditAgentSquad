"""Agent versions, runs and steps: the full trace of what each agent read, called and returned."""
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


class AgentSpecRecord(Base, IdMixin, CreatedMixin):
    """Registered agent version. Together these rows are the model inventory."""

    __tablename__ = "agent_specs"
    __table_args__ = (UniqueConstraint("name", "version"),)

    name: Mapped[str] = mapped_column(String(48))
    version: Mapped[str] = mapped_column(String(24))
    model: Mapped[str] = mapped_column(String(64))
    effort: Mapped[str] = mapped_column(String(12))
    max_steps: Mapped[int] = mapped_column(Integer)
    tools: Mapped[list[str]] = json_col(default=list)
    prompt_sha256: Mapped[str] = mapped_column(String(64))
    spec_sha256: Mapped[str] = mapped_column(String(64))
    purpose: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(default=True)


class AgentRun(Base, IdMixin, CreatedMixin):
    __tablename__ = "agent_runs"

    agent_name: Mapped[str] = mapped_column(String(48), index=True)
    agent_version: Mapped[str] = mapped_column(String(24))
    model: Mapped[str] = mapped_column(String(64))
    served_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    task: Mapped[str] = mapped_column(String(64))
    borrower_id: Mapped[uuid.UUID | None] = fk("borrowers.id", nullable=True)
    facility_id: Mapped[uuid.UUID | None] = fk("facilities.id", nullable=True)
    cycle_id: Mapped[uuid.UUID | None] = fk("cycles.id", nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    scope: Mapped[dict[str, Any]] = json_col(default=dict)
    status: Mapped[str] = mapped_column(String(16), default="running")  # running | completed | abstained | failed | refused
    steps_count: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, default=0)
    llm_mode: Mapped[str] = mapped_column(String(12), default="recorded")
    raw_output: Mapped[dict[str, Any] | None] = json_col(nullable=True)  # the model's answer before guardrails
    output: Mapped[dict[str, Any] | None] = json_col(nullable=True)  # the answer after guardrails
    guardrail_notes: Mapped[list[Any]] = json_col(default=list)  # [{layer, check, action, detail}]
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_by_type: Mapped[str] = mapped_column(String(16), default="system")
    started_by_id: Mapped[str] = mapped_column(String(64), default="system")


class AgentStep(Base, IdMixin, CreatedMixin):
    __tablename__ = "agent_steps"
    __table_args__ = (UniqueConstraint("run_id", "n"),)

    run_id: Mapped[uuid.UUID] = fk("agent_runs.id")
    n: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(16))  # model | tool | guardrail | note
    name: Mapped[str] = mapped_column(String(64))
    input_summary: Mapped[str] = mapped_column(Text, default="")
    output_summary: Mapped[str] = mapped_column(Text, default="")
    detail: Mapped[dict[str, Any]] = json_col(default=dict)
    refused: Mapped[bool] = mapped_column(default=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Lesson(Base, IdMixin, CreatedMixin):
    """A person's written reasoning from an override or approval, reused as precedent."""

    __tablename__ = "analyst_lessons"

    borrower_id: Mapped[uuid.UUID | None] = fk("borrowers.id", nullable=True)
    work_item_id: Mapped[uuid.UUID | None] = fk("work_items.id", nullable=True)
    topic: Mapped[str] = mapped_column(String(48), index=True)  # work item type or covenant archetype
    tag: Mapped[str | None] = mapped_column(String(48), nullable=True)
    text: Mapped[str] = mapped_column(Text)
    written_by: Mapped[uuid.UUID] = fk("users.id", index=False)
