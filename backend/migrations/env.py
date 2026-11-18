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
            # IF NOT EXISTS still needs the right to create schemas, which a least-privilege login
            # given an existing schema does not have: look first
            exists = connection.exec_driver_sql(
                "SELECT 1 FROM pg_namespace WHERE nspname = %s", (schema,)).first()
            if not exists:
                connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            connection.commit()
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
