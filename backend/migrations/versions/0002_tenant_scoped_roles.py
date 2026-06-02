"""tenant scoped custom roles

Revision ID: 0002_tenant_roles
Revises: 0001_initial
Create Date: 2026-06-02 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_tenant_roles"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        _upgrade_sqlite()
        return

    op.drop_index("ix_roles_name", table_name="roles")
    op.drop_constraint("roles_name_key", "roles", type_="unique")
    op.add_column("roles", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_roles_tenant_id_tenants", "roles", "tenants", ["tenant_id"], ["id"])
    op.create_index("ix_roles_tenant_id", "roles", ["tenant_id"])
    op.create_index("ix_roles_name", "roles", ["name"])
    if bind.dialect.name in {"postgresql", "sqlite"}:
        op.create_index(
            "uq_roles_system_name",
            "roles",
            ["name"],
            unique=True,
            postgresql_where=sa.text("tenant_id IS NULL"),
            sqlite_where=sa.text("tenant_id IS NULL"),
        )
    op.create_unique_constraint("uq_roles_tenant_name", "roles", ["tenant_id", "name"])


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        _downgrade_sqlite()
        return

    op.drop_constraint("uq_roles_tenant_name", "roles", type_="unique")
    if bind.dialect.name in {"postgresql", "sqlite"}:
        op.drop_index("uq_roles_system_name", table_name="roles")
    op.drop_index("ix_roles_name", table_name="roles")
    op.drop_index("ix_roles_tenant_id", table_name="roles")
    op.drop_constraint("fk_roles_tenant_id_tenants", "roles", type_="foreignkey")
    op.drop_column("roles", "tenant_id")
    op.create_index("ix_roles_name", "roles", ["name"], unique=True)
    op.create_unique_constraint("roles_name_key", "roles", ["name"])


def _upgrade_sqlite():
    op.execute("PRAGMA foreign_keys=OFF")
    op.execute("""
        CREATE TABLE roles_new (
            id INTEGER NOT NULL,
            tenant_id INTEGER,
            name VARCHAR(50) NOT NULL,
            description VARCHAR(200),
            is_system BOOLEAN NOT NULL DEFAULT 0,
            created_at DATETIME,
            updated_at DATETIME,
            PRIMARY KEY (id),
            FOREIGN KEY(tenant_id) REFERENCES tenants (id),
            CONSTRAINT uq_roles_tenant_name UNIQUE (tenant_id, name)
        )
    """)
    op.execute("""
        INSERT INTO roles_new (id, tenant_id, name, description, is_system, created_at, updated_at)
        SELECT id, NULL, name, description, is_system, created_at, updated_at
        FROM roles
    """)
    op.execute("DROP TABLE roles")
    op.execute("ALTER TABLE roles_new RENAME TO roles")
    op.create_index("ix_roles_name", "roles", ["name"])
    op.create_index("ix_roles_tenant_id", "roles", ["tenant_id"])
    op.create_index(
        "uq_roles_system_name",
        "roles",
        ["name"],
        unique=True,
        sqlite_where=sa.text("tenant_id IS NULL"),
    )
    op.execute("PRAGMA foreign_keys=ON")


def _downgrade_sqlite():
    op.execute("PRAGMA foreign_keys=OFF")
    op.execute("""
        CREATE TABLE roles_old (
            id INTEGER NOT NULL,
            name VARCHAR(50) NOT NULL,
            description VARCHAR(200),
            is_system BOOLEAN NOT NULL DEFAULT 0,
            created_at DATETIME,
            updated_at DATETIME,
            PRIMARY KEY (id),
            UNIQUE (name)
        )
    """)
    op.execute("""
        INSERT INTO roles_old (id, name, description, is_system, created_at, updated_at)
        SELECT id, name, description, is_system, created_at, updated_at
        FROM roles
        WHERE tenant_id IS NULL
    """)
    op.execute("DROP TABLE roles")
    op.execute("ALTER TABLE roles_old RENAME TO roles")
    op.create_index("ix_roles_name", "roles", ["name"], unique=True)
    op.execute("PRAGMA foreign_keys=ON")
