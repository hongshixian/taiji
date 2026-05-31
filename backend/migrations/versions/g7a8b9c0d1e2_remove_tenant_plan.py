"""remove tenant plan column

Revision ID: g7a8b9c0d1e2
Revises: f6a7b8c9d0e1
Create Date: 2026-05-31 20:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "g7a8b9c0d1e2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("tenants", "plan")


def downgrade():
    op.add_column("tenants", sa.Column("plan", sa.String(length=20), nullable=False, server_default="free"))
