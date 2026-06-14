"""Add red_team_tasks table

Revision ID: 0008_red_team_tasks
Revises: 0007_benchmark_tasks
Create Date: 2026-06-14 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "0008_red_team_tasks"
down_revision = "0007_benchmark_tasks"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "red_team_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("task_name", sa.String(100), nullable=False),
        sa.Column("target_model_name", sa.String(200), nullable=False),
        sa.Column("target_model_endpoint", sa.String(500)),
        sa.Column("target_model_api_key", sa.String(500)),
        sa.Column("attack_method", sa.String(100), nullable=False),
        sa.Column("attack_config", sa.JSON()),
        sa.Column("result", sa.JSON()),
    )


def downgrade():
    op.drop_table("red_team_tasks")
