"""Alembic environment: reads the database URL from settings and the schema from the models."""
from alembic import context
from app import models
from app.core.config import get_settings
from sqlalchemy import create_engine

target_metadata = models.Base.metadata


def run_migrations_online() -> None:
    url = context.get_x_argument(as_dictionary=True).get("url") or get_settings().database_url
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
