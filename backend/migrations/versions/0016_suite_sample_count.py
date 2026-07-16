"""add sample_count to benchmark_suite_states

Revision ID: 0016_suite_sample_count
Revises: 0015_benchmark_permissions
Create Date: 2026-07-16 01:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "0016_suite_sample_count"
down_revision = "0015_benchmark_permissions"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("benchmark_suite_states") as batch:
        batch.add_column(sa.Column("sample_count", sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table("benchmark_suite_states") as batch:
        batch.drop_column("sample_count")
