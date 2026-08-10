from uuid import uuid4

from werkzeug.security import generate_password_hash

from app import db
from app.models.iam_migration_record import IamMigrationRecord
from app.models.role import Role
from app.models.tenant import Tenant
from app.models.tenant_membership import TenantMembership
from app.models.user import User
from app.services.iam_migration_service import (
    LegacyIamMigrator,
    MigrationApiError,
)


class FakeMigrationApi:
    def __init__(self, fail_user_once=False):
        self.calls = []
        self.fail_user_once = fail_user_once
        self.failed_user = False
        self.users = set()
        self.tenants = set()

    def migrate_tenant(self, tenant_id, payload):
        self.calls.append(("tenant", tenant_id, payload))
        self.tenants.add(tenant_id)
        return {
            "id": tenant_id,
            "keycloak_org_id": f"kc-org-{tenant_id}",
            "tenant_type": "enterprise",
            "lifecycle_status": "active" if payload["enabled"] else "disabled",
            "protected": payload["protectedTenant"],
        }

    def migrate_user(self, user_id, payload):
        self.calls.append(("user", user_id, payload))
        if self.fail_user_once and not self.failed_user:
            self.failed_user = True
            raise MigrationApiError(503, "iam_unavailable", "temporary")
        self.users.add(user_id)
        personal_id = str(uuid4())
        return {
            "id": user_id,
            "keycloak_subject": f"kc-user-{user_id}",
            "personal_tenant": {
                "id": personal_id,
                "keycloak_org_id": f"kc-personal-{user_id}",
                "alias": f"personal-{user_id}",
                "name": f"{payload['username']} 的个人空间",
                "tenant_type": "personal",
                "lifecycle_status": "active",
                "enabled": True,
                "protected": True,
                "role": "tenant_admin",
            },
        }

    def migrate_membership(self, tenant_id, user_id, payload):
        self.calls.append(("membership", tenant_id, user_id, payload))
        if tenant_id not in self.tenants or user_id not in self.users:
            raise MigrationApiError(404, "dependency_missing", "dependency missing")
        return {"keycloak_subject": f"kc-user-{user_id}", **payload}


def _legacy_dataset():
    Tenant.query.filter_by(slug="default").delete()
    guest = Tenant.query.filter_by(slug="guest").one()
    custom_role = Role(
        tenant_id=guest.id,
        name="legacy-editor",
        description="legacy",
        is_system=False,
    )
    user = User(
        username="admin",
        email="admin@example.com",
        password_hash=generate_password_hash("OldPassword1!"),
        is_active=True,
        is_superuser=True,
    )
    db.session.add_all([custom_role, user])
    db.session.flush()
    membership = TenantMembership(
        tenant_id=guest.id,
        user_id=user.id,
        role_id=custom_role.id,
        is_active=True,
        is_owner=True,
    )
    db.session.add(membership)
    db.session.commit()
    return guest.id, user.id, membership.id


def test_preflight_rejects_unsupported_hash(app):
    with app.app_context():
        _, user_id, _ = _legacy_dataset()
        user = db.session.get(User, user_id)
        user.password_hash = "md5$unsafe$value"
        db.session.commit()

        report = LegacyIamMigrator.preflight()

        assert not report.ok
        assert any("密码摘要格式不受支持" in error for error in report.errors)


def test_custom_admin_role_is_not_promoted_to_tenant_admin(app):
    with app.app_context():
        tenant_id, _, membership_id = _legacy_dataset()
        membership = db.session.get(TenantMembership, membership_id)
        membership.is_owner = False
        membership.role.name = "admin"
        system_admin = Role.query.filter_by(tenant_id=None, name="admin").one()
        second = User(
            username="owner",
            email="owner@example.com",
            password_hash=generate_password_hash("OwnerPassword1!"),
            is_active=True,
        )
        db.session.add(second)
        db.session.flush()
        db.session.add(TenantMembership(
            tenant_id=tenant_id,
            user_id=second.id,
            role_id=system_admin.id,
            is_active=True,
        ))
        db.session.commit()

        report = LegacyIamMigrator(FakeMigrationApi()).run()

        assert report.ok
        migrated = db.session.get(TenantMembership, membership_id)
        assert migrated.iam_role == "member"
        assert migrated.role.name == "user"


def test_migration_is_checkpointed_and_idempotent(app):
    with app.app_context():
        tenant_id, user_id, membership_id = _legacy_dataset()
        old_hash = db.session.get(User, user_id).password_hash
        api = FakeMigrationApi()

        report = LegacyIamMigrator(api).run()

        assert report.ok
        assert report.migrated == {"tenants": 1, "users": 1, "memberships": 1}
        user = db.session.get(User, user_id)
        tenant = db.session.get(Tenant, tenant_id)
        membership = db.session.get(TenantMembership, membership_id)
        assert user.password_hash == old_hash
        assert user.iam_user_id and user.keycloak_subject
        assert tenant.iam_tenant_id and tenant.keycloak_org_id
        assert tenant.tenant_type == "enterprise"
        assert tenant.is_protected is True
        assert membership.iam_role == "tenant_admin"
        assert membership.role.name == "admin"
        assert Tenant.query.filter_by(tenant_type="personal").count() == 1
        assert TenantMembership.query.count() == 2
        user_call = next(call for call in api.calls if call[0] == "user")
        assert user_call[2]["linkExisting"] is True
        assert user_call[2]["legacyPasswordHash"] == old_hash
        assert IamMigrationRecord.query.filter_by(status="succeeded").count() == 3

        calls_before = len(api.calls)
        rerun = LegacyIamMigrator(api).run()
        assert rerun.ok
        assert len(api.calls) == calls_before
        assert rerun.skipped == {"tenants": 1, "users": 1, "memberships": 1}


def test_failed_entities_can_resume_without_recreating_tenant(app):
    with app.app_context():
        _legacy_dataset()
        api = FakeMigrationApi(fail_user_once=True)

        first = LegacyIamMigrator(api).run()

        assert not first.ok
        assert first.migrated["tenants"] == 1
        assert IamMigrationRecord.query.filter_by(
            entity_type="user", status="failed"
        ).one().attempts == 1

        second = LegacyIamMigrator(api).run()

        assert second.ok
        assert second.skipped["tenants"] == 1
        assert second.migrated["users"] == 1
        assert second.migrated["memberships"] == 1
        assert IamMigrationRecord.query.filter_by(
            entity_type="user", status="succeeded"
        ).one().attempts == 2


def test_cli_defaults_to_read_only_preflight(app):
    with app.app_context():
        _legacy_dataset()

    result = app.test_cli_runner().invoke(args=["iam-migrate"])

    assert result.exit_code == 0
    assert '"mode": "dry-run"' in result.output
    with app.app_context():
        assert IamMigrationRecord.query.count() == 0


def test_preflight_reports_outdated_schema(app):
    with app.app_context():
        db.session.execute(db.text("DROP TABLE iam_migration_records"))
        db.session.commit()

        report = LegacyIamMigrator.preflight()

        assert not report.ok
        assert report.counts == {}
        assert any("flask db upgrade" in error for error in report.errors)
