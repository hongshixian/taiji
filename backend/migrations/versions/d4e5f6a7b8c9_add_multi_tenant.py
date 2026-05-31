"""multi-tenant: add tenants table + tenant_id on users/analyze_tasks + is_superuser

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-31 15:00:00.000000

数据迁移策略：
- 建 tenants 表 + seed default + guest 两个系统租户
- 现有所有 users 和 analyze_tasks 全部归入 default 租户（保护现有数据）
- 第一个 admin 自动获得 is_superuser=true（保证有人能管理 tenants）
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # ─── 1. 建 tenants 表 ────────────────────────────
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("plan", sa.String(length=20), nullable=False, server_default="free"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)

    # ─── 2. seed 系统租户 ────────────────────────────
    tenants_tbl = table("tenants",
                        column("id", sa.Integer),
                        column("slug", sa.String),
                        column("name", sa.String),
                        column("plan", sa.String),
                        column("is_active", sa.Boolean),
                        column("is_system", sa.Boolean))
    op.bulk_insert(tenants_tbl, [
        {"id": 1, "slug": "default", "name": "默认组织",
         "plan": "enterprise", "is_active": True, "is_system": True},
        {"id": 2, "slug": "guest", "name": "访客租户",
         "plan": "free", "is_active": True, "is_system": True},
    ])

    # ─── 3. users 加 tenant_id + is_superuser ───────
    # 先以 nullable=True 加列（SQLite 不能直接给已有数据加 NOT NULL）
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("tenant_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("is_superuser", sa.Boolean(),
                                       nullable=False, server_default=sa.text("0")))

    # 把现有所有 users 归到 default tenant
    bind.execute(sa.text("UPDATE users SET tenant_id = 1 WHERE tenant_id IS NULL"))

    # 把第一个 admin 设为 superuser（保证有人能管 tenants）
    bind.execute(sa.text(
        "UPDATE users SET is_superuser = 1 "
        "WHERE id = (SELECT MIN(id) FROM users WHERE role = 'admin')"
    ))

    # 改为 NOT NULL + 加 FK + 调整唯一约束
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("tenant_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key("fk_users_tenant_id_tenants", "tenants",
                                    ["tenant_id"], ["id"])
        batch_op.create_index("ix_users_tenant_id", ["tenant_id"])
        # 老的全局唯一约束 → tenant 内唯一
        # SQLite 上原表 username UNIQUE 是 column-level 隐式约束，batch_alter_table 会重建表，
        # 老的列约束在 model 里去掉后会被丢弃，这里只新增联合约束
        batch_op.create_unique_constraint("uq_users_tenant_username",
                                          ["tenant_id", "username"])
        batch_op.create_unique_constraint("uq_users_tenant_email",
                                          ["tenant_id", "email"])

    # ─── 4. analyze_tasks 加 tenant_id ──────────────
    with op.batch_alter_table("analyze_tasks") as batch_op:
        batch_op.add_column(sa.Column("tenant_id", sa.Integer(), nullable=True))

    # 现有任务归 default tenant
    bind.execute(sa.text("UPDATE analyze_tasks SET tenant_id = 1 WHERE tenant_id IS NULL"))

    with op.batch_alter_table("analyze_tasks") as batch_op:
        batch_op.alter_column("tenant_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key("fk_analyze_tasks_tenant_id_tenants", "tenants",
                                    ["tenant_id"], ["id"])
        batch_op.create_index("ix_analyze_tasks_tenant_id", ["tenant_id"])


def downgrade():
    with op.batch_alter_table("analyze_tasks") as batch_op:
        batch_op.drop_index("ix_analyze_tasks_tenant_id")
        batch_op.drop_constraint("fk_analyze_tasks_tenant_id_tenants", type_="foreignkey")
        batch_op.drop_column("tenant_id")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("uq_users_tenant_email", type_="unique")
        batch_op.drop_constraint("uq_users_tenant_username", type_="unique")
        batch_op.drop_index("ix_users_tenant_id")
        batch_op.drop_constraint("fk_users_tenant_id_tenants", type_="foreignkey")
        batch_op.drop_column("is_superuser")
        batch_op.drop_column("tenant_id")

    op.drop_index("ix_tenants_slug", table_name="tenants")
    op.drop_table("tenants")
