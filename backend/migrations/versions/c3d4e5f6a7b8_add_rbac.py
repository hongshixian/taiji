"""RBAC: roles + permissions + role_permissions + users.role_id

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-31 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


# ─── 与 app.permissions 同步（migration 不能 import app，必须复刻一份）──
PERMISSIONS_REGISTRY = {
    "user:read": "查看用户列表",
    "user:write": "创建 / 编辑用户",
    "user:delete": "删除用户",
    "role:assign": "为用户分配角色",
    "role:read": "查看角色列表",
    "role:write": "创建 / 编辑角色（含权限分配）",
    "role:delete": "删除非系统角色",
    "task:read": "查看自己的任务",
    "task:create": "创建任务",
    "task:delete:any": "删除任意用户的任务",
    "system:audit": "查看审计日志",
}

SYSTEM_ROLES = {
    "admin": {
        "name": "admin",
        "description": "系统管理员（全部权限）",
        "permissions": list(PERMISSIONS_REGISTRY.keys()),  # 全部权限
    },
    "user": {
        "name": "user",
        "description": "普通用户（创建并查看自己的任务）",
        "permissions": ["task:read", "task:create"],
    },
    "guest": {
        "name": "guest",
        "description": "访客（只读）",
        "permissions": ["task:read"],
    },
}


def upgrade():
    # ─── 1. 建表 ────────────────────────────────────
    op.create_table(
        "permissions",
        sa.Column("code", sa.String(length=64), primary_key=True),
        sa.Column("description", sa.String(length=200), nullable=False),
    )
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_roles_name", "roles", ["name"], unique=True)
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_code", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_code"], ["permissions.code"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_code"),
    )

    # ─── 2. seed permissions ────────────────────────
    permissions_tbl = table("permissions",
                            column("code", sa.String),
                            column("description", sa.String))
    op.bulk_insert(
        permissions_tbl,
        [{"code": code, "description": desc} for code, desc in PERMISSIONS_REGISTRY.items()],
    )

    # ─── 3. seed 系统角色 + 关联权限 ───────────────
    roles_tbl = table("roles",
                      column("id", sa.Integer),
                      column("name", sa.String),
                      column("description", sa.String),
                      column("is_system", sa.Boolean))
    role_perms_tbl = table("role_permissions",
                           column("role_id", sa.Integer),
                           column("permission_code", sa.String))

    bind = op.get_bind()
    for idx, (name, info) in enumerate(SYSTEM_ROLES.items(), start=1):
        op.bulk_insert(roles_tbl, [{
            "id": idx,
            "name": name,
            "description": info["description"],
            "is_system": True,
        }])
        op.bulk_insert(role_perms_tbl, [
            {"role_id": idx, "permission_code": p} for p in info["permissions"]
        ])

    # ─── 4. users 加 role_id 外键 ─────────────────
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("role_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_users_role_id_roles", "roles", ["role_id"], ["id"]
        )
        batch_op.create_index("ix_users_role_id", ["role_id"])

    # ─── 5. 映射现有 users.role 字符串到 role_id ────
    # 查 roles 表得到 name → id 的映射
    result = bind.execute(sa.text("SELECT id, name FROM roles")).fetchall()
    name_to_id = {row.name: row.id for row in result}
    for role_name, role_id in name_to_id.items():
        bind.execute(
            sa.text("UPDATE users SET role_id = :rid WHERE role = :rname"),
            {"rid": role_id, "rname": role_name},
        )
    # 任何未匹配的（旧数据脏值）兜底为 user 角色
    if "user" in name_to_id:
        bind.execute(
            sa.text("UPDATE users SET role_id = :rid WHERE role_id IS NULL"),
            {"rid": name_to_id["user"]},
        )


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_role_id")
        batch_op.drop_constraint("fk_users_role_id_roles", type_="foreignkey")
        batch_op.drop_column("role_id")
    op.drop_table("role_permissions")
    op.drop_index("ix_roles_name", table_name="roles")
    op.drop_table("roles")
    op.drop_table("permissions")
