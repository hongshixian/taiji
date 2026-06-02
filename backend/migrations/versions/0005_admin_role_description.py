"""admin role description

Revision ID: 0005_admin_role_desc
Revises: 0004_task_log_path
Create Date: 2026-06-02 15:00:00.000000
"""
from alembic import op


revision = "0005_admin_role_desc"
down_revision = "0004_task_log_path"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        UPDATE roles
        SET description = '管理员（全部权限）'
        WHERE tenant_id IS NULL AND name = 'admin' AND is_system = TRUE
    """)


def downgrade():
    op.execute("""
        UPDATE roles
        SET description = '系统管理员（全部权限）'
        WHERE tenant_id IS NULL AND name = 'admin' AND is_system = TRUE
    """)
