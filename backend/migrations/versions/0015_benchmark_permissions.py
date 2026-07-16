"""add benchmark:read/write permissions to admin and user roles

Revision ID: 0015_benchmark_permissions
Revises: 0014_benchmark_suite_states
Create Date: 2026-07-16 00:10:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

revision = "0015_benchmark_permissions"
down_revision = "0014_benchmark_suite_states"
branch_labels = None
depends_on = None

NEW_PERMISSIONS = {
    "benchmark:read":  "查看 Benchmark 资产与状态",
    "benchmark:write": "管理 Benchmark 启用状态与可达性检测",
}

# admin (id=1) and user (id=2) both get both
ROLE_GRANTS = [1, 2]


def upgrade():
    bind = op.get_bind()

    permissions_t = table(
        "permissions",
        column("code", sa.String),
        column("description", sa.String),
    )
    role_permissions_t = table(
        "role_permissions",
        column("role_id", sa.Integer),
        column("permission_code", sa.String),
    )

    # 1. Insert new permissions — skip codes already present (re-entrant safe)
    existing_codes = {
        row[0]
        for row in bind.execute(
            sa.text("SELECT code FROM permissions WHERE code LIKE 'benchmark:%'")
        )
    }
    new_perms = [
        {"code": code, "description": desc}
        for code, desc in NEW_PERMISSIONS.items()
        if code not in existing_codes
    ]
    if new_perms:
        op.bulk_insert(permissions_t, new_perms)

    # 2. Grant to target roles — skip pairs already present
    existing_grants = {
        (row[0], row[1])
        for row in bind.execute(
            sa.text(
                "SELECT role_id, permission_code FROM role_permissions "
                "WHERE permission_code LIKE 'benchmark:%'"
            )
        )
    }
    new_grants = [
        {"role_id": role_id, "permission_code": code}
        for role_id in ROLE_GRANTS
        for code in NEW_PERMISSIONS
        if (role_id, code) not in existing_grants
    ]
    if new_grants:
        op.bulk_insert(role_permissions_t, new_grants)


def downgrade():
    bind = op.get_bind()
    bind.execute(
        sa.text("DELETE FROM role_permissions WHERE permission_code LIKE 'benchmark:%'")
    )
    bind.execute(
        sa.text("DELETE FROM permissions WHERE code LIKE 'benchmark:%'")
    )
