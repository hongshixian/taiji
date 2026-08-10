"""add IAM migration checkpoints

Revision ID: 0018_iam_migration
Revises: 0017_iam_projection
Create Date: 2026-08-10 18:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0018_iam_migration"
down_revision = "0017_iam_projection"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "iam_migration_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=24), nullable=False),
        sa.Column("local_id", sa.String(length=64), nullable=False),
        sa.Column("stable_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("keycloak_id", sa.String(length=64), nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("last_attempted_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_type", "local_id", name="uq_iam_migration_entity"),
        sa.UniqueConstraint("entity_type", "stable_id", name="uq_iam_migration_stable_id"),
    )
    op.create_index(
        "ix_iam_migration_records_entity_type",
        "iam_migration_records",
        ["entity_type"],
    )
    op.create_index(
        "ix_iam_migration_records_status",
        "iam_migration_records",
        ["status"],
    )


def downgrade():
    op.drop_index("ix_iam_migration_records_status", table_name="iam_migration_records")
    op.drop_index("ix_iam_migration_records_entity_type", table_name="iam_migration_records")
    op.drop_table("iam_migration_records")
