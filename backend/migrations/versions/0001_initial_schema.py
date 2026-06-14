"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-01 23:20:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import column, table


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


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
    1: {
        "name": "admin",
        "description": "管理员（全部权限）",
        "permissions": list(PERMISSIONS_REGISTRY.keys()),
    },
    2: {
        "name": "user",
        "description": "普通用户（创建并查看自己的任务）",
        "permissions": ["task:read", "task:create"],
    },
    3: {
        "name": "guest",
        "description": "访客（只读）",
        "permissions": ["task:read"],
    },
}


def upgrade():
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=256), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("tokens_revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "permissions",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_roles_name", "roles", ["name"], unique=True)

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_code", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["permission_code"], ["permissions.code"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_code"),
    )

    op.create_table(
        "tenant_memberships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_owner", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "tenant_id", name="uq_membership_user_tenant"),
    )
    op.create_index("ix_tenant_memberships_role_id", "tenant_memberships", ["role_id"])
    op.create_index("ix_tenant_memberships_tenant_id", "tenant_memberships", ["tenant_id"])
    op.create_index("ix_tenant_memberships_user_id", "tenant_memberships", ["user_id"])

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("task_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_task_type", "tasks", ["task_type"])
    op.create_index("ix_tasks_tenant_id", "tasks", ["tenant_id"])
    op.create_index("ix_tasks_user_id", "tasks", ["user_id"])

    op.create_table(
        "webpage_analysis_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("keywords", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id"),
    )
    op.create_index("ix_webpage_analysis_tasks_task_id", "webpage_analysis_tasks", ["task_id"])
    op.create_index("ix_webpage_analysis_tasks_tenant_id", "webpage_analysis_tasks", ["tenant_id"])

    op.create_table(
        "csv_quality_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("task_name", sa.String(length=100), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("content_sample", sa.Text(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id"),
    )
    op.create_index("ix_csv_quality_tasks_task_id", "csv_quality_tasks", ["task_id"])
    op.create_index("ix_csv_quality_tasks_tenant_id", "csv_quality_tasks", ["tenant_id"])

    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("key"),
    )

    _seed_initial_data()


def downgrade():
    op.drop_table("system_settings")
    op.drop_index("ix_csv_quality_tasks_tenant_id", table_name="csv_quality_tasks")
    op.drop_index("ix_csv_quality_tasks_task_id", table_name="csv_quality_tasks")
    op.drop_table("csv_quality_tasks")
    op.drop_index("ix_webpage_analysis_tasks_tenant_id", table_name="webpage_analysis_tasks")
    op.drop_index("ix_webpage_analysis_tasks_task_id", table_name="webpage_analysis_tasks")
    op.drop_table("webpage_analysis_tasks")
    op.drop_index("ix_tasks_user_id", table_name="tasks")
    op.drop_index("ix_tasks_tenant_id", table_name="tasks")
    op.drop_index("ix_tasks_task_type", table_name="tasks")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_table("tasks")
    op.drop_index("ix_tenant_memberships_user_id", table_name="tenant_memberships")
    op.drop_index("ix_tenant_memberships_tenant_id", table_name="tenant_memberships")
    op.drop_index("ix_tenant_memberships_role_id", table_name="tenant_memberships")
    op.drop_table("tenant_memberships")
    op.drop_table("role_permissions")
    op.drop_index("ix_roles_name", table_name="roles")
    op.drop_table("roles")
    op.drop_table("permissions")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
    op.drop_index("ix_tenants_slug", table_name="tenants")
    op.drop_table("tenants")


def _seed_initial_data():
    tenants = table(
        "tenants",
        column("id", sa.Integer),
        column("slug", sa.String),
        column("name", sa.String),
        column("is_active", sa.Boolean),
        column("is_system", sa.Boolean),
    )
    op.bulk_insert(tenants, [
        {"id": 1, "slug": "guest", "name": "访客租户", "is_active": True, "is_system": True},
    ])

    permissions = table(
        "permissions",
        column("code", sa.String),
        column("description", sa.String),
    )
    op.bulk_insert(
        permissions,
        [{"code": code, "description": desc} for code, desc in PERMISSIONS_REGISTRY.items()],
    )

    roles = table(
        "roles",
        column("id", sa.Integer),
        column("name", sa.String),
        column("description", sa.String),
        column("is_system", sa.Boolean),
    )
    role_permissions = table(
        "role_permissions",
        column("role_id", sa.Integer),
        column("permission_code", sa.String),
    )
    for role_id, info in SYSTEM_ROLES.items():
        op.bulk_insert(roles, [{
            "id": role_id,
            "name": info["name"],
            "description": info["description"],
            "is_system": True,
        }])
        op.bulk_insert(role_permissions, [
            {"role_id": role_id, "permission_code": code}
            for code in info["permissions"]
        ])

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
