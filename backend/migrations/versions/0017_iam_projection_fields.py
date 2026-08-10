"""add IAM projection fields

Revision ID: 0017_iam_projection
Revises: 0016_suite_sample_count
Create Date: 2026-08-10 15:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0017_iam_projection"
down_revision = "0016_suite_sample_count"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch:
        batch.alter_column("password_hash", existing_type=sa.String(length=256), nullable=True)
        batch.add_column(sa.Column("iam_user_id", sa.String(length=36), nullable=True))
        batch.add_column(sa.Column("keycloak_subject", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("last_iam_tenant_id", sa.String(length=36), nullable=True))
        batch.add_column(sa.Column("last_synced_at", sa.DateTime(), nullable=True))
        batch.create_index("ix_users_iam_user_id", ["iam_user_id"], unique=True)
        batch.create_index("ix_users_keycloak_subject", ["keycloak_subject"], unique=True)

    with op.batch_alter_table("tenants") as batch:
        batch.add_column(sa.Column("iam_tenant_id", sa.String(length=36), nullable=True))
        batch.add_column(sa.Column("keycloak_org_id", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("tenant_type", sa.String(length=20), nullable=True))
        batch.add_column(sa.Column("lifecycle_status", sa.String(length=20), nullable=True))
        batch.add_column(sa.Column("is_protected", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        batch.add_column(sa.Column("last_synced_at", sa.DateTime(), nullable=True))
        batch.create_index("ix_tenants_iam_tenant_id", ["iam_tenant_id"], unique=True)
        batch.create_index("ix_tenants_keycloak_org_id", ["keycloak_org_id"], unique=True)

    with op.batch_alter_table("tenant_memberships") as batch:
        batch.add_column(sa.Column("iam_role", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("sync_version", sa.BigInteger(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("last_synced_at", sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table("tenant_memberships") as batch:
        batch.drop_column("last_synced_at")
        batch.drop_column("sync_version")
        batch.drop_column("iam_role")

    with op.batch_alter_table("tenants") as batch:
        batch.drop_index("ix_tenants_keycloak_org_id")
        batch.drop_index("ix_tenants_iam_tenant_id")
        batch.drop_column("last_synced_at")
        batch.drop_column("is_protected")
        batch.drop_column("lifecycle_status")
        batch.drop_column("tenant_type")
        batch.drop_column("keycloak_org_id")
        batch.drop_column("iam_tenant_id")

    op.execute("UPDATE users SET password_hash = '!iam-only' WHERE password_hash IS NULL")
    with op.batch_alter_table("users") as batch:
        batch.drop_index("ix_users_keycloak_subject")
        batch.drop_index("ix_users_iam_user_id")
        batch.drop_column("last_synced_at")
        batch.drop_column("last_iam_tenant_id")
        batch.drop_column("keycloak_subject")
        batch.drop_column("iam_user_id")
        batch.alter_column("password_hash", existing_type=sa.String(length=256), nullable=False)
