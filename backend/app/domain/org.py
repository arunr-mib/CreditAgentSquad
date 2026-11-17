"""People who use the workspace, and their sign-in sessions."""
from sqlalchemy import Boolean

from app.core.db import Base, CreatedMixin, IdMixin
from app.domain.common import DateTime, Mapped, String, datetime, fk, mapped_column, uuid


class User(Base, IdMixin, CreatedMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(120), default="")
    role: Mapped[str] = mapped_column(String(32))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    external_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)  # for single sign-on later


class UserSession(Base, IdMixin, CreatedMixin):
    __tablename__ = "user_sessions"

    user_id: Mapped[uuid.UUID] = fk("users.id")
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
