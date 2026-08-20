"""make Taiji authoritative for users, tenants and memberships

Revision ID: 0021_local_identity
Revises: 0020_iam_event_ledger
Create Date: 2026-08-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0021_local_identity"
down_revision = "0020_iam_event_ledger"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    bind.execute(sa.text(
        "UPDATE tenants SET tenant_type = CASE "
        "WHEN slug LIKE 'personal-%' THEN 'personal' ELSE 'enterprise' END "
        "WHERE tenant_type IS NULL OR tenant_type NOT IN ('personal', 'enterprise')"
    ))

    with op.batch_alter_table("users") as batch:
        batch.drop_index("ix_users_iam_user_id")
        batch.drop_column("last_synced_at")
        batch.drop_column("last_iam_tenant_id")
        batch.drop_column("iam_user_id")

    with op.batch_alter_table("tenants") as batch:
        batch.drop_index("ix_tenants_keycloak_org_id")
        batch.drop_index("ix_tenants_iam_tenant_id")
        batch.drop_column("last_synced_at")
        batch.drop_column("lifecycle_status")
        batch.drop_column("keycloak_org_id")
        batch.drop_column("iam_tenant_id")
        batch.alter_column(
            "tenant_type",
            existing_type=sa.String(length=20),
            nullable=False,
            server_default="enterprise",
        )

    with op.batch_alter_table("tenant_memberships") as batch:
        batch.drop_column("last_synced_at")
        batch.drop_column("sync_version")
        batch.drop_column("iam_role")

    op.drop_table("iam_aggregate_cursors")
    op.drop_index("ix_iam_event_receipts_status", table_name="iam_event_receipts")
    op.drop_index("ix_iam_event_receipts_aggregate_id", table_name="iam_event_receipts")
    op.drop_index("ix_iam_event_receipts_event_type", table_name="iam_event_receipts")
    op.drop_index("ix_iam_event_receipts_event_id", table_name="iam_event_receipts")
    op.drop_table("iam_event_receipts")
    op.drop_index("ix_iam_migration_records_status", table_name="iam_migration_records")
    op.drop_index("ix_iam_migration_records_entity_type", table_name="iam_migration_records")
    op.drop_table("iam_migration_records")


def downgrade():
    raise RuntimeError("0021_local_identity is an architecture boundary and cannot be downgraded")
