"""OIDC management routes proxy IAM and update local projections."""

from uuid import uuid4

from app import db
from app.models.tenant import Tenant
from app.models.tenant_membership import TenantMembership
from app.models.user import User
from app.models.role import Role
from app.services.iam_client import IamClient
from tests.test_oidc_auth import (
    ENTERPRISE_ID,
    IAM_USER_ID,
    _identity,
    _login,
    oidc_app,
    oidc_client,
)


BOB_ID = "44444444-4444-4444-4444-444444444444"


def _member_payload(
    user_id=BOB_ID,
    username="bob",
    email="bob@example.com",
    role="member",
    active=True,
):
    return {
        "id": user_id,
        "keycloak_subject": f"kc-{username}",
        "username": username,
        "email": email,
        "email_verified": False,
        "enabled": True,
        "active": active,
        "role": role if active else None,
        "owner": False,
    }


def _alice_payload(role="tenant_admin"):
    return _member_payload(
        user_id=IAM_USER_ID,
        username="alice",
        email="alice@example.com",
        role=role,
    )


def _login_enterprise_admin(client, monkeypatch, platform_admin=False):
    identity = _identity(enterprise_role="tenant_admin", platform_admin=platform_admin)
    monkeypatch.setattr(IamClient, "list_my_tenants", lambda _self, _token: identity)
    csrf = _login(client)
    response = client.post(
        "/api/v1/auth/switch-tenant",
        json={"tenant_id": ENTERPRISE_ID},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    return csrf


def test_member_list_projects_external_iam_users(oidc_client, oidc_app, monkeypatch):
    _login_enterprise_admin(oidc_client, monkeypatch)
    monkeypatch.setattr(
        IamClient,
        "list_members",
        lambda _self, _token, _tenant: {
            "members": [_alice_payload(), _member_payload()]
        },
    )

    response = oidc_client.get("/api/v1/admin/users")

    assert response.status_code == 200
    body = response.get_json()["data"]
    assert body["total"] == 2
    assert {item["username"] for item in body["items"]} == {"alice", "bob"}
    with oidc_app.app_context():
        bob = User.query.filter_by(iam_user_id=BOB_ID).one()
        assert bob.password_hash is None
        tenant = Tenant.query.filter_by(iam_tenant_id=ENTERPRISE_ID).one()
        membership = TenantMembership.query.filter_by(
            tenant_id=tenant.id, user_id=bob.id
        ).one()
        assert membership.iam_role == "member"


def test_member_invite_update_and_deactivate_use_controlled_api(
    oidc_client, oidc_app, monkeypatch
):
    csrf = _login_enterprise_admin(oidc_client, monkeypatch)
    monkeypatch.setattr(
        IamClient,
        "add_member",
        lambda _self, _token, _tenant, payload: {
            "invitation_id": "invite-1",
            "email": payload["identifier"],
            "status": "pending",
        },
    )
    invited = oidc_client.post(
        "/api/v1/admin/users",
        json={"identifier": "new@example.com", "role": "member"},
        headers={"X-CSRF-Token": csrf},
    )
    assert invited.status_code == 202
    assert invited.get_json()["data"]["kind"] == "invitation"

    with oidc_app.app_context():
        tenant = Tenant.query.filter_by(iam_tenant_id=ENTERPRISE_ID).one()
        bob = User(
            username="bob",
            email="bob@example.com",
            password_hash=None,
            iam_user_id=BOB_ID,
            keycloak_subject="kc-bob",
        )
        db.session.add(bob)
        db.session.flush()
        user_role = Role.query.filter_by(tenant_id=None, name="user").one().id
        membership = TenantMembership(
            tenant_id=tenant.id,
            user_id=bob.id,
            role_id=user_role,
            iam_role="member",
        )
        db.session.add(membership)
        db.session.commit()
        bob_local_id = bob.id

    monkeypatch.setattr(
        IamClient,
        "update_member",
        lambda _self, _token, _tenant, _user, payload: _member_payload(
            role=payload.get("role", "member"),
            active=payload.get("active", True),
        ),
    )
    updated = oidc_client.put(
        f"/api/v1/admin/users/{bob_local_id}",
        json={"role": "tenant_admin"},
        headers={"X-CSRF-Token": csrf},
    )
    assert updated.status_code == 200
    assert updated.get_json()["data"]["role"] == "tenant_admin"

    monkeypatch.setattr(
        IamClient,
        "deactivate_member",
        lambda _self, _token, _tenant, _user: _member_payload(active=False),
    )
    removed = oidc_client.delete(
        f"/api/v1/admin/users/{bob_local_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert removed.status_code == 200
    with oidc_app.app_context():
        membership = TenantMembership.query.filter_by(user_id=bob_local_id).one()
        assert membership.is_active is False
        assert db.session.get(User, bob_local_id) is not None


def test_oidc_member_edit_rejects_global_identity_fields(oidc_client, monkeypatch):
    csrf = _login_enterprise_admin(oidc_client, monkeypatch)

    response = oidc_client.put(
        "/api/v1/admin/users/999",
        json={"email": "changed@example.com"},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 400
    assert "只允许修改成员角色和成员状态" in response.get_json()["message"]


def test_oidc_member_edit_rejects_string_boolean(oidc_client, oidc_app, monkeypatch):
    csrf = _login_enterprise_admin(oidc_client, monkeypatch)
    with oidc_app.app_context():
        user_id = User.query.filter_by(iam_user_id=IAM_USER_ID).one().id

    response = oidc_client.put(
        f"/api/v1/admin/users/{user_id}",
        json={"active": "false"},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 400
    assert "必须是布尔值" in response.get_json()["message"]


def test_shared_projection_change_invalidates_session_permissions(
    oidc_client, oidc_app, monkeypatch
):
    _login_enterprise_admin(oidc_client, monkeypatch)
    with oidc_app.app_context():
        membership = TenantMembership.query.join(User).filter(
            User.iam_user_id == IAM_USER_ID,
            TenantMembership.tenant.has(iam_tenant_id=ENTERPRISE_ID),
        ).one()
        membership.role = Role.query.filter_by(tenant_id=None, name="user").one()
        membership.iam_role = "member"
        db.session.commit()

    downgraded = _identity(enterprise_role="member")
    monkeypatch.setattr(IamClient, "list_my_tenants", lambda _self, _token: downgraded)
    response = oidc_client.get("/api/v1/admin/users")

    assert response.status_code == 403


def test_personal_space_rejects_member_management(oidc_client, monkeypatch):
    monkeypatch.setattr(
        IamClient,
        "list_my_tenants",
        lambda _self, _token: _identity(),
    )
    _login(oidc_client)

    response = oidc_client.get("/api/v1/admin/users")

    assert response.status_code == 409
    assert "个人空间" in response.get_json()["message"]


def test_platform_admin_tenant_and_admin_operations_project_locally(
    oidc_client, oidc_app, monkeypatch
):
    csrf = _login_enterprise_admin(oidc_client, monkeypatch, platform_admin=True)
    new_tenant_id = str(uuid4())
    monkeypatch.setattr(
        IamClient,
        "create_tenant",
        lambda _self, _token, payload, _key: {
            "id": new_tenant_id,
            "keycloak_org_id": "kc-new-tenant",
            "alias": f"enterprise-{new_tenant_id}",
            "name": payload["name"],
            "tenant_type": "enterprise",
            "lifecycle_status": "active",
            "enabled": True,
            "protected": False,
            "role": None,
        },
    )
    created = oidc_client.post(
        "/api/v1/superadmin/tenants",
        json={"name": "New Co", "initial_admin": "alice"},
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": "test-create-tenant"},
    )
    assert created.status_code == 201
    assert created.get_json()["data"]["iam_tenant_id"] == new_tenant_id

    alice_admin = {
        "id": IAM_USER_ID,
        "keycloak_subject": "keycloak-sub-alice",
        "username": "alice",
        "email": "alice@example.com",
        "enabled": True,
        "platform_admin": True,
    }
    monkeypatch.setattr(
        IamClient,
        "list_platform_admins",
        lambda _self, _token: {"platform_admins": [alice_admin]},
    )
    listed = oidc_client.get("/api/v1/superadmin/superusers")
    assert listed.status_code == 200
    assert listed.get_json()["data"][0]["is_superuser"] is True

    bob_admin = {
        **_member_payload(),
        "platform_admin": True,
    }
    monkeypatch.setattr(
        IamClient,
        "grant_platform_admin",
        lambda _self, _token, _identifier: bob_admin,
    )
    granted = oidc_client.post(
        "/api/v1/superadmin/superusers",
        json={"identifier": "bob"},
        headers={"X-CSRF-Token": csrf},
    )
    assert granted.status_code == 200
    bob_local_id = granted.get_json()["data"]["id"]

    monkeypatch.setattr(
        IamClient,
        "revoke_platform_admin",
        lambda _self, _token, _user: {**bob_admin, "platform_admin": False},
    )
    revoked = oidc_client.delete(
        f"/api/v1/superadmin/superusers/{bob_local_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert revoked.status_code == 200
    with oidc_app.app_context():
        assert User.query.filter_by(iam_user_id=BOB_ID).one().is_superuser is False
