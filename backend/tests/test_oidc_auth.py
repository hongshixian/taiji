"""OIDC BFF tests with Taiji-owned tenants and authorization."""

from cachelib import SimpleCache
import pytest
from urllib.parse import parse_qs, urlsplit

from app import create_app, db, oauth
from app.models.tenant import Tenant
from app.models.tenant_membership import TenantMembership
from app.models.user import User
from app.services.auth_service import add_tenant_member
from app.services.tenant_service import create_enterprise_tenant
from config import TestConfig
from tests.conftest import _seed_rbac, _seed_tenants


class OidcTestConfig(TestConfig):
    AUTH_MODE = "oidc"
    SESSION_TYPE = "cachelib"
    SESSION_CACHELIB = SimpleCache(default_timeout=7200)
    SESSION_COOKIE_SECURE = False
    TAIJI_PUBLIC_URL = "http://localhost"
    TAIJI_PUBLIC_URLS = ("http://localhost", "https://evaluation.fangcunleap.com")
    IAM_PUBLIC_URL = "http://localhost/iam"
    IAM_INTERNAL_URL = "http://keycloak:8080/iam"


@pytest.fixture
def oidc_app(monkeypatch):
    app = create_app(config_obj=OidcTestConfig)
    with app.app_context():
        db.create_all()
        _seed_tenants()
        _seed_rbac()

    token = {
        "access_token": "server-only-access-token",
        "refresh_token": "server-only-refresh-token",
        "id_token": "server-only-id-token",
        "expires_at": 4102444800,
        "userinfo": {
            "sub": "keycloak-sub-alice",
            "preferred_username": "alice",
            "email": "alice@example.com",
        },
    }
    monkeypatch.setattr(oauth.keycloak, "authorize_access_token", lambda: token)
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def oidc_client(oidc_app):
    return oidc_app.test_client()


def _login(client):
    response = client.get("/api/v1/auth/callback")
    assert response.status_code == 302
    with client.session_transaction() as browser_session:
        return browser_session["csrf_token"]


def test_callback_creates_local_user_and_personal_workspace(oidc_client, oidc_app):
    _login(oidc_client)

    response = oidc_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["keycloak_subject"] == "keycloak-sub-alice"
    assert data["role"] == "tenant_admin"
    assert data["current_tenant"]["type"] == "personal"
    assert data["tenants"] == [{
        "enabled": True,
        "id": data["current_tenant"]["id"],
        "local_id": data["current_tenant"]["id"],
        "name": "alice 的个人空间",
        "role": "tenant_admin",
        "slug": f"personal-{data['id']}",
        "tenant_type": "personal",
    }]

    cookie = response.headers.get("Set-Cookie", "")
    assert "server-only-access-token" not in cookie
    assert "server-only-refresh-token" not in cookie
    assert "server-only-id-token" not in cookie
    with oidc_app.app_context():
        user = User.query.filter_by(keycloak_subject="keycloak-sub-alice").one()
        membership = TenantMembership.query.filter_by(user_id=user.id).one()
        assert membership.tenant.tenant_type == "personal"
        assert membership.is_owner is True
        assert membership.role.name == "admin"


def test_switch_tenant_uses_local_membership_and_requires_csrf(oidc_client, oidc_app):
    csrf = _login(oidc_client)
    with oidc_app.app_context():
        enterprise = create_enterprise_tenant("Acme", "alice")
        enterprise_id = enterprise.id

    rejected = oidc_client.post(
        "/api/v1/auth/switch-tenant", json={"tenant_id": enterprise_id}
    )
    assert rejected.status_code == 403

    response = oidc_client.post(
        "/api/v1/auth/switch-tenant",
        json={"tenant_id": enterprise_id},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["role"] == "tenant_admin"
    assert oidc_client.get("/api/v1/auth/me").get_json()["data"]["current_tenant"]["id"] == enterprise_id


def test_refresh_reloads_local_role_change(oidc_client, oidc_app):
    csrf = _login(oidc_client)
    with oidc_app.app_context():
        enterprise = Tenant(slug="tenant-acme", name="Acme", tenant_type="enterprise")
        db.session.add(enterprise)
        db.session.flush()
        user = User.query.filter_by(username="alice").one()
        add_tenant_member(enterprise.id, user.username, "member")
        enterprise_id = enterprise.id

    response = oidc_client.post(
        "/api/v1/auth/switch-tenant",
        json={"tenant_id": enterprise_id},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.get_json()["data"]["role"] == "member"

    with oidc_app.app_context():
        membership = TenantMembership.query.filter_by(tenant_id=enterprise_id).one()
        admin_role = next(role for role in membership.role.__class__.query.all() if role.name == "admin")
        membership.role_id = admin_role.id
        db.session.commit()

    response = oidc_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.get_json()["data"]["role"] == "tenant_admin"


def test_platform_admin_role_only_bootstraps_local_authority(oidc_client, oidc_app, monkeypatch):
    token = oauth.keycloak.authorize_access_token()
    token["userinfo"]["realm_access"] = {"roles": ["platform_admin"]}
    monkeypatch.setattr(oauth.keycloak, "authorize_access_token", lambda: token)
    _login(oidc_client)

    with oidc_app.app_context():
        user = User.query.filter_by(username="alice").one()
        assert user.is_superuser is True
        user.is_superuser = False
        db.session.commit()

    oidc_client.post("/api/v1/auth/logout", headers={
        "X-CSRF-Token": oidc_client.get("/api/v1/auth/me").get_json()["data"]["csrf_token"]
    })
    _login(oidc_client)
    with oidc_app.app_context():
        assert User.query.filter_by(username="alice").one().is_superuser is False


def test_absolute_session_timeout_fails_closed(oidc_client):
    _login(oidc_client)
    with oidc_client.session_transaction() as browser_session:
        browser_session["created_at"] = 0
    assert oidc_client.get("/api/v1/auth/me").status_code == 401


def test_logout_clears_session_and_returns_keycloak_end_session_url(oidc_client):
    csrf = _login(oidc_client)
    response = oidc_client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert response.status_code == 200
    logout_url = response.get_json()["data"]["logout_url"]
    assert logout_url.startswith("http://localhost/iam/realms/fangcun/")
    assert "id_token_hint=server-only-id-token" in logout_url
    assert oidc_client.get("/api/v1/auth/me").status_code == 401


def test_login_uses_allowed_request_domain_for_callback(oidc_client):
    response = oidc_client.get(
        "/api/v1/auth/login", base_url="https://evaluation.fangcunleap.com"
    )
    assert response.status_code == 302
    query = parse_qs(urlsplit(response.location).query)
    assert query["redirect_uri"] == [
        "https://evaluation.fangcunleap.com/api/v1/auth/callback"
    ]


def test_login_rejects_unconfigured_request_domain(oidc_client):
    response = oidc_client.get(
        "/api/v1/auth/login", base_url="https://untrusted.example.com"
    )
    assert response.status_code == 400
    assert response.get_json()["message"] == "当前访问域名未配置为平台登录域名"


def test_runtime_never_claims_unbound_legacy_account(oidc_client, oidc_app):
    with oidc_app.app_context():
        db.session.add(User(
            username="alice",
            email="legacy-alice@example.com",
            password_hash="legacy-password-hash",
        ))
        db.session.commit()

    response = oidc_client.get("/api/v1/auth/callback")
    assert response.status_code == 409
    assert response.get_json()["code"] == 30010
    with oidc_app.app_context():
        assert User.query.count() == 1
        assert User.query.one().keycloak_subject is None
