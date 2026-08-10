"""IAM projection reconciliation and event idempotency tests."""

from datetime import datetime, timezone
import uuid

from app.models.audit_log import AuditLog
from app.models.iam_event_receipt import IamAggregateCursor, IamEventReceipt
from app.models.tenant import Tenant
from app.models.tenant_membership import TenantMembership
from app.models.user import User
from app.services.iam_reconciliation_service import process_event, reconcile_all


TENANT_ID = "10000000-0000-0000-0000-000000000001"
USER_ID = "20000000-0000-0000-0000-000000000001"
SUBJECT = "30000000-0000-0000-0000-000000000001"


class FakeIamClient:
    def __init__(self):
        self.tenants = [_tenant_payload()]
        self.members = {TENANT_ID: [_member_payload()]}
        self.admins = [_admin_payload()]
        self.tenant_calls = 0

    def reconciliation_tenants(self):
        self.tenant_calls += 1
        return self.tenants

    def reconciliation_members(self, tenant_id):
        return self.members.get(tenant_id, [])

    def reconciliation_platform_admins(self):
        return self.admins


def test_full_reconciliation_projects_and_deactivates_snapshot(app):
    remote = FakeIamClient()
    with app.app_context():
        result = reconcile_all(remote)
        assert result == {"tenants": 1, "memberships": 1, "platform_admins": 1}

        tenant = Tenant.query.filter_by(iam_tenant_id=TENANT_ID).one()
        user = User.query.filter_by(iam_user_id=USER_ID).one()
        membership = TenantMembership.query.filter_by(
            tenant_id=tenant.id, user_id=user.id
        ).one()
        assert tenant.is_active is True
        assert membership.is_active is True
        assert membership.iam_role == "tenant_admin"
        assert user.is_superuser is True

        remote.members[TENANT_ID] = []
        remote.admins = []
        reconcile_all(remote)
        assert TenantMembership.query.filter_by(id=membership.id).one().is_active is False
        assert User.query.filter_by(id=user.id).one().is_superuser is False
        assert AuditLog.query.filter_by(action="iam.reconciliation.completed").count() == 2


def test_event_is_deduplicated_and_older_version_is_ignored(app):
    remote = FakeIamClient()
    current = _event(version=20)
    with app.app_context():
        assert process_event(current, remote) == "processed"
        calls = remote.tenant_calls
        assert process_event(current, remote) == "duplicate"
        assert remote.tenant_calls == calls

        assert process_event(_event(version=10), remote) == "ignored"
        assert remote.tenant_calls == calls
        assert IamEventReceipt.query.filter_by(status="processed").count() == 1
        assert IamEventReceipt.query.filter_by(status="ignored").count() == 1
        cursor = IamAggregateCursor.query.one()
        assert cursor.aggregate_version == 20


def test_equal_aggregate_version_is_still_reconciled(app):
    remote = FakeIamClient()
    with app.app_context():
        assert process_event(_event(version=20), remote) == "processed"
        calls = remote.tenant_calls
        assert process_event(_event(version=20), remote) == "processed"
        assert remote.tenant_calls == calls + 1


def test_event_rejects_wrong_realm_before_writing_receipt(app):
    event = _event(version=1)
    event["realm"] = "another-realm"
    with app.app_context():
        try:
            process_event(event, FakeIamClient())
        except ValueError as exc:
            assert "different realm" in str(exc)
        else:
            raise AssertionError("wrong-realm event was accepted")
        assert IamEventReceipt.query.count() == 0


def _tenant_payload():
    return {
        "id": TENANT_ID,
        "keycloak_org_id": "org-1",
        "alias": "enterprise-one",
        "name": "Enterprise One",
        "tenant_type": "enterprise",
        "lifecycle_status": "active",
        "enabled": True,
        "protected": False,
        "role": None,
    }


def _member_payload():
    return {
        "id": USER_ID,
        "keycloak_subject": SUBJECT,
        "username": "iam-admin",
        "email": "iam-admin@example.test",
        "enabled": True,
        "active": True,
        "role": "tenant_admin",
        "owner": False,
    }


def _admin_payload():
    return {**_member_payload(), "platform_admin": True}


def _event(*, version: int):
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": "iam.tenant.updated.v1",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "realm": "fangcun",
        "aggregate_id": TENANT_ID,
        "aggregate_version": version,
        "data": {},
    }
