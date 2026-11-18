"""Alembic environment: reads the database URL from settings and the schema from the models."""
from alembic import context
from app import models
from app.core.config import get_settings
from app.core.db import make_engine

target_metadata = models.Base.metadata


def run_migrations_online() -> None:
    url = context.get_x_argument(as_dictionary=True).get("url") or get_settings().owner_database_url
    engine = make_engine(url)  # the same schema setting the application uses
    with engine.connect() as connection:
        schema = get_settings().db_schema.strip()
        if schema:
            connection.exec_driver_sql(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
            connection.commit()
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
