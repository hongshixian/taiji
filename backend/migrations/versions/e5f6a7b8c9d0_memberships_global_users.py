"""memberships: make users global and move tenant roles to memberships

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-31 17:20:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    op.create_table(
        "tenant_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_owner", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.UniqueConstraint("user_id", "tenant_id", name="uq_membership_user_tenant"),
    )
    op.create_index("ix_tenant_memberships_tenant_id", "tenant_memberships", ["tenant_id"])
    op.create_index("ix_tenant_memberships_user_id", "tenant_memberships", ["user_id"])
    op.create_index("ix_tenant_memberships_role_id", "tenant_memberships", ["role_id"])

    user_role_id = bind.execute(
        sa.text("SELECT id FROM roles WHERE name = 'user'")
    ).scalar()
    admin_role_id = bind.execute(
        sa.text("SELECT id FROM roles WHERE name = 'admin'")
    ).scalar()

    users = bind.execute(sa.text(
        "SELECT id, tenant_id, role_id, role FROM users ORDER BY id"
    )).fetchall()
    for row in users:
        role_id = row.role_id or user_role_id
        is_owner = bool(admin_role_id and role_id == admin_role_id)
        bind.execute(sa.text(
            "INSERT INTO tenant_memberships "
            "(tenant_id, user_id, role_id, is_active, is_owner) "
            "VALUES (:tenant_id, :user_id, :role_id, 1, :is_owner)"
        ), {
            "tenant_id": row.tenant_id,
            "user_id": row.id,
            "role_id": role_id,
            "is_owner": is_owner,
        })

    # Existing installations may contain same usernames/emails across tenants.
    # Users are now global, so make duplicates deterministic before adding uniques.
    _dedupe_column(bind, "username")
    _dedupe_column(bind, "email")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("uq_users_tenant_email", type_="unique")
        batch_op.drop_constraint("uq_users_tenant_username", type_="unique")
        batch_op.drop_index("ix_users_tenant_id")
        batch_op.drop_constraint("fk_users_tenant_id_tenants", type_="foreignkey")
        batch_op.drop_index("ix_users_role_id")
        batch_op.drop_constraint("fk_users_role_id_roles", type_="foreignkey")
        batch_op.drop_column("tenant_id")
        batch_op.drop_column("role_id")
        batch_op.drop_column("role")
        batch_op.create_unique_constraint("uq_users_username", ["username"])
        batch_op.create_unique_constraint("uq_users_email", ["email"])


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("role", sa.String(length=20),
                                      nullable=False, server_default="user"))
        batch_op.add_column(sa.Column("role_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("tenant_id", sa.Integer(), nullable=True))
        batch_op.drop_constraint("uq_users_email", type_="unique")
        batch_op.drop_constraint("uq_users_username", type_="unique")
        batch_op.create_foreign_key("fk_users_role_id_roles", "roles", ["role_id"], ["id"])
        batch_op.create_index("ix_users_role_id", ["role_id"])
        batch_op.create_foreign_key("fk_users_tenant_id_tenants", "tenants", ["tenant_id"], ["id"])
        batch_op.create_index("ix_users_tenant_id", ["tenant_id"])

    bind = op.get_bind()
    bind.execute(sa.text(
        "UPDATE users SET "
        "tenant_id = (SELECT tenant_id FROM tenant_memberships "
        "             WHERE user_id = users.id ORDER BY id LIMIT 1), "
        "role_id = (SELECT role_id FROM tenant_memberships "
        "           WHERE user_id = users.id ORDER BY id LIMIT 1)"
    ))
    bind.execute(sa.text(
        "UPDATE users SET role = COALESCE((SELECT name FROM roles "
        "WHERE roles.id = users.role_id), 'user')"
    ))
    bind.execute(sa.text("UPDATE users SET tenant_id = 1 WHERE tenant_id IS NULL"))

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("tenant_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_unique_constraint("uq_users_tenant_username", ["tenant_id", "username"])
        batch_op.create_unique_constraint("uq_users_tenant_email", ["tenant_id", "email"])

    op.drop_index("ix_tenant_memberships_role_id", table_name="tenant_memberships")
    op.drop_index("ix_tenant_memberships_user_id", table_name="tenant_memberships")
    op.drop_index("ix_tenant_memberships_tenant_id", table_name="tenant_memberships")
    op.drop_table("tenant_memberships")


def _dedupe_column(bind, column_name: str):
    rows = bind.execute(sa.text(
        f"SELECT id, {column_name} AS value FROM users ORDER BY id"
    )).fetchall()
    seen = set()
    for row in rows:
        value = row.value
        if value not in seen:
            seen.add(value)
            continue
        if column_name == "email" and "@" in value:
            local, domain = value.rsplit("@", 1)
            new_value = f"{local}+{row.id}@{domain}"
        else:
            new_value = f"{value}-{row.id}"
        while new_value in seen:
            new_value = f"{new_value}-{row.id}"
        bind.execute(
            sa.text(f"UPDATE users SET {column_name} = :value WHERE id = :id"),
            {"value": new_value, "id": row.id},
        )
        seen.add(new_value)
