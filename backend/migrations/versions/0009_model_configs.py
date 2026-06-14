"""Add model_configs table

Revision ID: 0009_model_configs
Revises: 0008_red_team_tasks
Create Date: 2026-06-14 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "0009_model_configs"
down_revision = "0008_red_team_tasks"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "model_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("model_name", sa.String(200), nullable=False),
        sa.Column("api_base_url", sa.String(500), nullable=False),
        sa.Column("api_protocol", sa.String(50), nullable=False, server_default="openai"),
        sa.Column("api_key", sa.String(500)),
        sa.Column("description", sa.String(500)),
        sa.Column("extra_params", sa.JSON()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("model_configs")
