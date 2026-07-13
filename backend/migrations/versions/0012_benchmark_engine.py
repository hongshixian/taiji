"""Refactor benchmark_tasks for inspect_evals engine + add task.progress

Revision ID: 0012_benchmark_engine
Revises: 0011_remove_default_tenant
Create Date: 2026-07-13 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "0012_benchmark_engine"
down_revision = "0011_remove_default_tenant"
branch_labels = None
depends_on = None


def upgrade():
    # 1) tasks 表加 progress 列
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("progress", sa.JSON(), nullable=True))

    # 2) 重建 benchmark_tasks 表（无历史包袱，直接 drop & create）
    op.drop_table("benchmark_tasks")
    op.create_table(
        "benchmark_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"),
                  nullable=False, index=True),
        sa.Column("task_id", sa.Integer(),
                  sa.ForeignKey("tasks.id", ondelete="CASCADE"),
                  nullable=False, unique=True, index=True),
        sa.Column("task_name", sa.String(100), nullable=False),
        sa.Column("notes", sa.String(500)),
        sa.Column("engine", sa.String(50), nullable=False,
                  server_default="inspect_evals"),
        sa.Column("benchmark_suite", sa.String(100), nullable=False),
        sa.Column("target_model_id", sa.Integer(),
                  sa.ForeignKey("model_configs.id", ondelete="RESTRICT"),
                  nullable=False, index=True),
        sa.Column("judge_model_id", sa.Integer(),
                  sa.ForeignKey("model_configs.id", ondelete="RESTRICT"),
                  nullable=True, index=True),
        sa.Column("benchmark_config", sa.JSON()),
        sa.Column("result", sa.JSON()),
    )


def downgrade():
    op.drop_table("benchmark_tasks")
    op.create_table(
        "benchmark_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"),
                  nullable=False, index=True),
        sa.Column("task_id", sa.Integer(),
                  sa.ForeignKey("tasks.id", ondelete="CASCADE"),
                  nullable=False, unique=True, index=True),
        sa.Column("task_name", sa.String(100), nullable=False),
        sa.Column("model_name", sa.String(200), nullable=False),
        sa.Column("model_endpoint", sa.String(500)),
        sa.Column("model_api_key", sa.String(500)),
        sa.Column("benchmark_suite", sa.String(100), nullable=False),
        sa.Column("benchmark_config", sa.JSON()),
        sa.Column("result", sa.JSON()),
    )
    with op.batch_alter_table("tasks") as batch:
        batch.drop_column("progress")
