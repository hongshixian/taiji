"""Add tasks.celery_task_id for task cancellation

Revision ID: 0013_task_celery_id
Revises: 0012_benchmark_engine
Create Date: 2026-07-15 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "0013_task_celery_id"
down_revision = "0012_benchmark_engine"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("celery_task_id", sa.String(64), nullable=True))


def downgrade():
    with op.batch_alter_table("tasks") as batch:
        batch.drop_column("celery_task_id")
