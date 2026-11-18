"""Database engine, session factory and the declarative base shared by every model."""
import uuid
from collections.abc import Iterator
from datetime import datetime

from sqlalchemy import DateTime, MetaData, create_engine, event, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


class IdMixin:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class CreatedMixin:
    # clock_timestamp(), not now(): now() is the transaction's start time, so every row written in
    # one transaction would carry the same instant and "the latest" would be a coin toss
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())


_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def make_engine(url: str | None = None):
    """An engine for `url` (default: the application's database) with the configured schema and
    pooling applied. Migrations use this too, so tables are created where the application looks."""
    settings = get_settings()
    options = {"poolclass": NullPool} if settings.db_pool.strip().lower() == "null" else {"pool_pre_ping": True}
    engine = create_engine(url or settings.database_url, **options)
    schema = settings.db_schema.strip()
    if schema:
        if not schema.replace("_", "").isalnum():
            raise ValueError("DB_SCHEMA must be letters, digits and underscores")

        @event.listens_for(engine, "connect")
        def _use_schema(connection, _record):  # every new connection looks in the schema first
            with connection.cursor() as cursor:
                cursor.execute(f'SET search_path TO "{schema}"')
            connection.commit()
    return engine


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        _engine = make_engine()
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, committed by the caller."""
    get_engine()
    assert _SessionLocal is not None
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
