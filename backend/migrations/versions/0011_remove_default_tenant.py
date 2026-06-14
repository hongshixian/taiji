"""remove default tenant, migrate memberships to guest

Revision ID: 0011_remove_default_tenant
Revises: 0010_model_permissions
Create Date: 2026-06-14 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

revision = "0011_remove_default_tenant"
down_revision = "0010_model_permissions"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # 找到 default 和 guest 租户的 id
    default_row = conn.execute(text("SELECT id FROM tenants WHERE slug = 'default'")).fetchone()
    guest_row = conn.execute(text("SELECT id FROM tenants WHERE slug = 'guest'")).fetchone()

    if default_row and guest_row:
        default_id = default_row[0]
        guest_id = guest_row[0]

        # 把 default 下的 membership 迁移到 guest，已存在的跳过（避免 unique 冲突）
        conn.execute(text("""
            UPDATE tenant_memberships
            SET tenant_id = :guest_id
            WHERE tenant_id = :default_id
              AND user_id NOT IN (
                  SELECT user_id FROM tenant_memberships WHERE tenant_id = :guest_id
              )
        """), {"guest_id": guest_id, "default_id": default_id})

        # 删除仍留在 default 的 membership（即上面跳过的重复项）
        conn.execute(text(
            "DELETE FROM tenant_memberships WHERE tenant_id = :default_id"
        ), {"default_id": default_id})

        # 删除 default 租户本身
        conn.execute(text(
            "DELETE FROM tenants WHERE id = :default_id"
        ), {"default_id": default_id})


def downgrade():
    # 不支持回滚（租户删除不可逆）
    pass
