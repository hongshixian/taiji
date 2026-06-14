"""Add benchmark_tasks table

Revision ID: 0007_benchmark_tasks
Revises: 0006_task_cascade
Create Date: 2026-06-14 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "0007_benchmark_tasks"
down_revision = "0006_task_cascade"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "benchmark_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("task_name", sa.String(100), nullable=False),
        sa.Column("model_name", sa.String(200), nullable=False),
        sa.Column("model_endpoint", sa.String(500)),
        sa.Column("model_api_key", sa.String(500)),
        sa.Column("benchmark_suite", sa.String(100), nullable=False),
        sa.Column("benchmark_config", sa.JSON()),
        sa.Column("result", sa.JSON()),
    )


def downgrade():
    op.drop_table("benchmark_tasks")
