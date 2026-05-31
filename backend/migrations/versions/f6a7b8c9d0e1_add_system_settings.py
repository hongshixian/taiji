"""add platform system settings

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-05-31 18:30:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(length=100), primary_key=True),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    settings = table(
        "system_settings",
        column("key", sa.String),
        column("value", sa.JSON),
        column("description", sa.String),
    )
    op.bulk_insert(settings, [{
        "key": "public.default_registration_tenant_slug",
        "value": "guest",
        "description": "新注册用户默认加入的租户 slug",
    }])


def downgrade():
    op.drop_table("system_settings")
