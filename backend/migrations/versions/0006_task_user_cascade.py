"""Add CASCADE on task user_id FK

Revision ID: 0006_task_cascade
Revises: 0005_admin_desc
Create Date: 2026-06-02 15:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "0006_task_cascade"
down_revision = "0005_admin_role_desc"
branch_labels = None
depends_on = None


def upgrade():
    """SQLite 不支持 ALTER FK，需要重建 tasks 表"""
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        _upgrade_sqlite()
    else:
        # PostgreSQL / MySQL: 直接 drop 再 add FK
        op.drop_constraint("fk_tasks_user_id", "tasks", type_="foreignkey")
        op.create_foreign_key("fk_tasks_user_id", "tasks", "users", ["user_id"], ["id"], ondelete="CASCADE")


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        _downgrade_sqlite()
    else:
        op.drop_constraint("fk_tasks_user_id", "tasks", type_="foreignkey")
        op.create_foreign_key("fk_tasks_user_id", "tasks", "users", ["user_id"], ["id"])


def _upgrade_sqlite():
    """SQLite: 重建 tasks 表以添加 ON DELETE CASCADE"""
    # 1. 创建新表
    op.execute("PRAGMA foreign_keys=OFF")
    try:
        op.create_table(
            "tasks_new",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("task_type", sa.String(80), nullable=False, index=True),
            sa.Column("status", sa.String(20), nullable=False, index=True, server_default=sa.text("'pending'")),
            sa.Column("error_message", sa.Text()),
            sa.Column("log_path", sa.String(500)),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("started_at", sa.DateTime()),
            sa.Column("completed_at", sa.DateTime()),
        )
        # 2. 复制数据
        op.execute(
            "INSERT INTO tasks_new (id, tenant_id, user_id, task_type, status, error_message, log_path, created_at, started_at, completed_at) "
            "SELECT id, tenant_id, user_id, task_type, status, error_message, log_path, created_at, started_at, completed_at FROM tasks"
        )
        # 3. 删旧表，重命名
        op.drop_table("tasks")
        op.rename_table("tasks_new", "tasks")
    finally:
        op.execute("PRAGMA foreign_keys=ON")


def _downgrade_sqlite():
    """回滚：重建 tasks 表去掉 ON DELETE CASCADE"""
    op.execute("PRAGMA foreign_keys=OFF")
    try:
        op.create_table(
            "tasks_new",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
            sa.Column("task_type", sa.String(80), nullable=False, index=True),
            sa.Column("status", sa.String(20), nullable=False, index=True, server_default=sa.text("'pending'")),
            sa.Column("error_message", sa.Text()),
            sa.Column("log_path", sa.String(500)),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("started_at", sa.DateTime()),
            sa.Column("completed_at", sa.DateTime()),
        )
        op.execute(
            "INSERT INTO tasks_new (id, tenant_id, user_id, task_type, status, error_message, log_path, created_at, started_at, completed_at) "
            "SELECT id, tenant_id, user_id, task_type, status, error_message, log_path, created_at, started_at, completed_at FROM tasks"
        )
        op.drop_table("tasks")
        op.rename_table("tasks_new", "tasks")
    finally:
        op.execute("PRAGMA foreign_keys=ON")
