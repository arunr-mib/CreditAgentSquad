"""a runtime role that can append to the ledger but cannot rewrite it

The application connected as the owner of its tables. An owner can disable the append-only
trigger on `ledger_events`, edit an event, recompute the hash chain and re-enable the trigger,
and the chain then verifies. The application now runs as a login that is a member of
`squad_runtime`: it may read and write the working tables, may only SELECT and INSERT on
`ledger_events`, and owns nothing, so it cannot alter the table or its triggers. Migrations keep
running as the owner.

Creating a role needs CREATEROLE. Where the migrating role lacks it (a single-role development
database) the role is not created and a warning says so; create it as a superuser and run
`python -m app.cli grant-runtime-role` as the owner.

Revision ID: 0003
Revises: 0002
"""
import warnings

from alembic import op
from app.core.config import get_settings
from app.core.ledger import RUNTIME_ROLE, runtime_role_sql
from sqlalchemy import text

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    exists = bind.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": RUNTIME_ROLE}).first()
    if not exists:
        may_create = bind.execute(text(
            "SELECT rolsuper OR rolcreaterole FROM pg_roles WHERE rolname = current_user")).scalar()
        if not may_create:
            warnings.warn(
                f"role {RUNTIME_ROLE} was not created: this database user may not create roles. The "
                "application can still rewrite its own ledger while it connects as the table owner. Create "
                f"the role as a superuser (CREATE ROLE {RUNTIME_ROLE} NOLOGIN) and run "
                "`python -m app.cli grant-runtime-role` as the owner.", stacklevel=1)
            return
        op.execute(f"CREATE ROLE {RUNTIME_ROLE} NOLOGIN")
    op.execute(runtime_role_sql(schema=get_settings().db_schema.strip() or "public"))


def downgrade() -> None:
    bind = op.get_bind()
    if not bind.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": RUNTIME_ROLE}).first():
        return
    op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM {RUNTIME_ROLE}")
    op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM {RUNTIME_ROLE}")
    op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {RUNTIME_ROLE}")
    op.execute(f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {RUNTIME_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {RUNTIME_ROLE}")
    # the role itself is left in place: it is shared by every database in the server
