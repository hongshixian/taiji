"""Add benchmark_suite_states table

Revision ID: 0014_benchmark_suite_states
Revises: 0013_task_celery_id
Create Date: 2026-07-16 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "0014_benchmark_suite_states"
down_revision = "0013_task_celery_id"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "benchmark_suite_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("suite_key", sa.String(100), nullable=False, index=True),
        # NULL 表示继承 yaml 默认（not disabled）；True/False 为显式覆盖 → 无 server_default
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("last_check_status", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("last_check_error", sa.Text()),
        sa.Column("last_check_at", sa.DateTime()),
        sa.Column("last_check_ms", sa.Integer()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "suite_key", name="uq_suite_state_tenant_key"),
    )


def downgrade():
    op.drop_table("benchmark_suite_states")
