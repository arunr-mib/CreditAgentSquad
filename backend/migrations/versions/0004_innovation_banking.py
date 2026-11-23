"""borrower template and funding events

Adds `borrowers.template_id` (ci-1 commercial and industrial, vc-1 venture) and the
`funding_events` table. The ledger guards are untouched. The runtime role's default privileges
(migration 0003) cover the new table; the explicit grant below makes that true on a database
whose defaults were set by a different owner.

Revision ID: 0004
Revises: 0003
"""
import sqlalchemy as sa
from alembic import op
from app.core.config import get_settings
from app.core.ledger import runtime_role_name, runtime_role_sql
from sqlalchemy.dialects import postgresql

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("borrowers", sa.Column("template_id", sa.String(length=8), server_default="ci-1", nullable=False))
    op.create_check_constraint(op.f("ck_borrowers_template_id"), "borrowers", "template_id IN ('ci-1','vc-1')")
    op.create_table(
        "funding_events",
        sa.Column("borrower_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("amount", sa.Numeric(20, 2), nullable=False),
        sa.Column("expected_close", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("evidence_document_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"),
                  nullable=False),
        sa.CheckConstraint("kind IN ('equity_round','extension','milestone_tranche','venture_debt')",
                           name=op.f("ck_funding_events_kind")),
        sa.CheckConstraint("status IN ('expected','signed','closed','slipped')",
                           name=op.f("ck_funding_events_status")),
        sa.ForeignKeyConstraint(["borrower_id"], ["borrowers.id"],
                                name=op.f("fk_funding_events_borrower_id_borrowers")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_funding_events")),
    )
    op.create_index(op.f("ix_funding_events_borrower_id"), "funding_events", ["borrower_id"], unique=False)
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": runtime_role_name()}).first():
        op.execute(runtime_role_sql(runtime_role_name(), schema=get_settings().db_schema.strip() or "public"))


def downgrade() -> None:
    op.drop_index(op.f("ix_funding_events_borrower_id"), table_name="funding_events")
    op.drop_table("funding_events")
    op.drop_constraint(op.f("ck_borrowers_template_id"), "borrowers", type_="check")
    op.drop_column("borrowers", "template_id")
