"""add IAM event idempotency ledger

Revision ID: 0020_iam_event_ledger
Revises: 0019_fixed_iam_permissions
Create Date: 2026-08-11 08:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0020_iam_event_ledger"
down_revision = "0019_fixed_iam_permissions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "iam_event_receipts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("aggregate_kind", sa.String(length=32), nullable=False),
        sa.Column("aggregate_id", sa.String(length=100), nullable=False),
        sa.Column("aggregate_version", sa.BigInteger(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_iam_event_receipts_event_id", "iam_event_receipts", ["event_id"], unique=True
    )
    op.create_index(
        "ix_iam_event_receipts_event_type", "iam_event_receipts", ["event_type"]
    )
    op.create_index(
        "ix_iam_event_receipts_aggregate_id", "iam_event_receipts", ["aggregate_id"]
    )
    op.create_index(
        "ix_iam_event_receipts_status", "iam_event_receipts", ["status"]
    )

    op.create_table(
        "iam_aggregate_cursors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("aggregate_kind", sa.String(length=32), nullable=False),
        sa.Column("aggregate_id", sa.String(length=100), nullable=False),
        sa.Column("aggregate_version", sa.BigInteger(), nullable=False),
        sa.Column("last_event_id", sa.String(length=36), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "aggregate_kind", "aggregate_id", name="uq_iam_aggregate_cursor"
        ),
    )


def downgrade():
    op.drop_table("iam_aggregate_cursors")
    op.drop_index("ix_iam_event_receipts_status", table_name="iam_event_receipts")
    op.drop_index("ix_iam_event_receipts_aggregate_id", table_name="iam_event_receipts")
    op.drop_index("ix_iam_event_receipts_event_type", table_name="iam_event_receipts")
    op.drop_index("ix_iam_event_receipts_event_id", table_name="iam_event_receipts")
    op.drop_table("iam_event_receipts")
