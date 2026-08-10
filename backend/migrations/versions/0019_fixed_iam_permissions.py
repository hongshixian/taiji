"""replace local user and role management permissions with fixed IAM membership permissions

Revision ID: 0019_fixed_iam_permissions
Revises: 0018_iam_migration
Create Date: 2026-08-11 00:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0019_fixed_iam_permissions"
down_revision = "0018_iam_migration"
branch_labels = None
depends_on = None


NEW_PERMISSIONS = {
    "member:read": "查看当前租户成员",
    "member:write": "邀请成员并修改固定身份角色",
    "member:remove": "停用当前租户成员身份",
}

OLD_ADMIN_PERMISSIONS = {
    "user:read", "user:write", "user:delete", "role:assign",
    "role:read", "role:write", "role:delete",
}


def upgrade():
    bind = op.get_bind()
    for code, description in NEW_PERMISSIONS.items():
        statement = sa.text(
            "INSERT INTO permissions (code, description) "
            "SELECT :code, :description WHERE NOT EXISTS "
            "(SELECT 1 FROM permissions WHERE code = :code)"
        ).bindparams(
            sa.bindparam("code", type_=sa.String(100)),
            sa.bindparam("description", type_=sa.String(255)),
        )
        bind.execute(statement, {"code": code, "description": description})

    _grant("admin", set(NEW_PERMISSIONS))
    _revoke("admin", OLD_ADMIN_PERMISSIONS)
    _grant("user", {"task:delete:any"})
    _revoke("user", {"benchmark:write"})

    bind.execute(sa.text(
        "UPDATE permissions SET description = '查看租户内全部任务' "
        "WHERE code = 'task:read'"
    ))
    bind.execute(sa.text(
        "UPDATE permissions SET description = '管理租户内任意成员的任务' "
        "WHERE code = 'task:delete:any'"
    ))
    bind.execute(sa.text(
        "UPDATE roles SET description = '租户管理员' "
        "WHERE tenant_id IS NULL AND name = 'admin'"
    ))
    bind.execute(sa.text(
        "UPDATE roles SET description = '租户成员' "
        "WHERE tenant_id IS NULL AND name = 'user'"
    ))


def downgrade():
    bind = op.get_bind()
    _grant("admin", OLD_ADMIN_PERMISSIONS)
    _revoke("admin", set(NEW_PERMISSIONS))
    _revoke("user", {"task:delete:any"})
    _grant("user", {"benchmark:write"})
    bind.execute(sa.text(
        "DELETE FROM permissions WHERE code IN "
        "('member:read', 'member:write', 'member:remove')"
    ))
    bind.execute(sa.text(
        "UPDATE permissions SET description = '查看自己的任务' WHERE code = 'task:read'"
    ))
    bind.execute(sa.text(
        "UPDATE permissions SET description = '删除任意用户的任务' "
        "WHERE code = 'task:delete:any'"
    ))
    bind.execute(sa.text(
        "UPDATE roles SET description = '管理员（全部权限）' "
        "WHERE tenant_id IS NULL AND name = 'admin'"
    ))
    bind.execute(sa.text(
        "UPDATE roles SET description = '普通用户（创建并查看自己的任务）' "
        "WHERE tenant_id IS NULL AND name = 'user'"
    ))


def _grant(role_name: str, codes: set[str]):
    bind = op.get_bind()
    for code in codes:
        statement = sa.text(
            "INSERT INTO role_permissions (role_id, permission_code) "
            "SELECT roles.id, :code FROM roles "
            "WHERE roles.tenant_id IS NULL AND roles.name = :role_name "
            "AND NOT EXISTS (SELECT 1 FROM role_permissions rp "
            "WHERE rp.role_id = roles.id AND rp.permission_code = :code)"
        ).bindparams(
            sa.bindparam("role_name", type_=sa.String(50)),
            sa.bindparam("code", type_=sa.String(100)),
        )
        bind.execute(statement, {"role_name": role_name, "code": code})


def _revoke(role_name: str, codes: set[str]):
    if not codes:
        return
    bind = op.get_bind()
    statement = sa.text(
        "DELETE FROM role_permissions WHERE role_id IN "
        "(SELECT id FROM roles WHERE tenant_id IS NULL AND name = :role_name) "
        "AND permission_code IN :codes"
    ).bindparams(
        sa.bindparam("role_name", type_=sa.String(50)),
        sa.bindparam("codes", expanding=True, type_=sa.String(100)),
    )
    bind.execute(statement, {
        "role_name": role_name,
        "codes": sorted(codes),
    })
