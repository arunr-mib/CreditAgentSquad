"""Policy, evaluation results and application settings (including the simulated clock)."""
from app.core.db import Base, CreatedMixin, IdMixin
from app.domain.common import Any, Mapped, String, Text, fk, json_col, mapped_column, uuid


class Policy(Base, IdMixin, CreatedMixin):
    """Versioned policy document: autonomy levels, tolerances and thresholds. Never edited in place."""

    __tablename__ = "policies"

    name: Mapped[str] = mapped_column(String(48), index=True)  # autonomy | tolerances | signals
    version: Mapped[int] = mapped_column()
    content: Mapped[dict[str, Any]] = json_col()
    active: Mapped[bool] = mapped_column(default=True)
    changed_by: Mapped[uuid.UUID | None] = fk("users.id", nullable=True, index=False)
    reason: Mapped[str] = mapped_column(Text, default="")


class EvalRun(Base, IdMixin, CreatedMixin):
    __tablename__ = "eval_runs"

    suite: Mapped[str] = mapped_column(String(64))
    mode: Mapped[str] = mapped_column(String(12))  # recorded | live
    commit: Mapped[str] = mapped_column(String(64), default="")
    results: Mapped[dict[str, Any]] = json_col(default=dict)
    gate_passed: Mapped[bool | None] = mapped_column(nullable=True)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict[str, Any]] = json_col()
