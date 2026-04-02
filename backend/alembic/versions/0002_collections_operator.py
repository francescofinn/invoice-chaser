"""add collections operator tables

Revision ID: 0002_collections_operator
Revises: 0001_initial
Create Date: 2026-04-02 00:15:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0002_collections_operator"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

    op.create_table(
        "collection_cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("risk_level", sa.String(), nullable=True),
        sa.Column("risk_summary", sa.Text(), nullable=True),
        sa.Column("next_action_key", sa.String(), nullable=True),
        sa.Column("next_action_label", sa.String(), nullable=True),
        sa.Column("next_action_reason", sa.Text(), nullable=True),
        sa.Column("draft_subject", sa.String(), nullable=True),
        sa.Column("draft_body", sa.Text(), nullable=True),
        sa.Column("last_client_reply", sa.Text(), nullable=True),
        sa.Column("last_reply_classification", sa.String(), nullable=True),
        sa.Column("last_contacted_at", sa.DateTime(), nullable=True),
        sa.Column("queued_follow_up_date", sa.Date(), nullable=True),
        sa.Column("last_analyzed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_id"),
    )
    op.create_index(op.f("ix_collection_cases_id"), "collection_cases", ["id"], unique=False)
    op.create_index(op.f("ix_collection_cases_invoice_id"), "collection_cases", ["invoice_id"], unique=False)

    op.create_table(
        "collection_commitments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("commitment_type", sa.String(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_collection_commitments_id"), "collection_commitments", ["id"], unique=False)
    op.create_index(
        op.f("ix_collection_commitments_invoice_id"),
        "collection_commitments",
        ["invoice_id"],
        unique=False,
    )

    op.create_table(
        "collection_activity",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("activity_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("payload_json", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_collection_activity_id"), "collection_activity", ["id"], unique=False)
    op.create_index(op.f("ix_collection_activity_invoice_id"), "collection_activity", ["invoice_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_collection_activity_invoice_id"), table_name="collection_activity")
    op.drop_index(op.f("ix_collection_activity_id"), table_name="collection_activity")
    op.drop_table("collection_activity")
    op.drop_index(op.f("ix_collection_commitments_invoice_id"), table_name="collection_commitments")
    op.drop_index(op.f("ix_collection_commitments_id"), table_name="collection_commitments")
    op.drop_table("collection_commitments")
    op.drop_index(op.f("ix_collection_cases_invoice_id"), table_name="collection_cases")
    op.drop_index(op.f("ix_collection_cases_id"), table_name="collection_cases")
    op.drop_table("collection_cases")
