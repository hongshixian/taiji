"""task log path

Revision ID: 0004_task_log_path
Revises: 0003_audit_logs
Create Date: 2026-06-02 14:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "0004_task_log_path"
down_revision = "0003_audit_logs"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tasks", sa.Column("log_path", sa.String(length=500), nullable=True))


def downgrade():
    op.drop_column("tasks", "log_path")
