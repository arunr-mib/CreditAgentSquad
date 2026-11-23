"""covenant test note

Adds the nullable `covenant_tests.note` (for example `not_meaningful_cash_flow_positive`, a runway
test that passes because the borrower is not burning cash). The runtime role grants are re-run as
in 0004.

Revision ID: 0005
Revises: 0004
"""
import sqlalchemy as sa
from alembic import op
from app.core.config import get_settings
from app.core.ledger import runtime_role_name, runtime_role_sql

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("covenant_tests", sa.Column("note", sa.String(length=64), nullable=True))
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": runtime_role_name()}).first():
        op.execute(runtime_role_sql(runtime_role_name(), schema=get_settings().db_schema.strip() or "public"))


def downgrade() -> None:
    op.drop_column("covenant_tests", "note")
