"""OIDC BFF session and IAM projection tests."""

from cachelib import SimpleCache
import pytest
from urllib.parse import parse_qs, urlsplit

from app import create_app, db, oauth
from app.models.tenant import Tenant
from app.models.tenant_membership import TenantMembership
from app.models.user import User
from app.services.iam_client import IamClient
from config import TestConfig
from tests.conftest import _seed_rbac, _seed_tenants


IAM_USER_ID = "11111111-1111-1111-1111-111111111111"
PERSONAL_ID = "22222222-2222-2222-2222-222222222222"
ENTERPRISE_ID = "33333333-3333-3333-3333-333333333333"


class OidcTestConfig(TestConfig):
    AUTH_MODE = "oidc"
    SESSION_TYPE = "cachelib"
    SESSION_CACHELIB = SimpleCache(default_timeout=7200)
    SESSION_COOKIE_SECURE = False
    TAIJI_PUBLIC_URL = "http://localhost"
    TAIJI_PUBLIC_URLS = ("http://localhost", "https://evaluation.fangcunleap.com")


def _identity(personal_role="tenant_admin", enterprise_role="member", platform_admin=False):
    return {
        "user_id": IAM_USER_ID,
        "platform_admin": platform_admin,
        "tenants": [
            {
                "id": PERSONAL_ID,
                "keycloak_org_id": "kc-personal",
                "alias": "personal-alice",
                "name": "alice 的个人空间",
                "tenant_type": "personal",
                "lifecycle_status": "active",
                "enabled": True,
                "role": personal_role,
            },
            {
                "id": ENTERPRISE_ID,
                "keycloak_org_id": "kc-enterprise",
                "alias": "acme",
                "name": "Acme",
                "tenant_type": "enterprise",
                "lifecycle_status": "active",
                "enabled": True,
                "role": enterprise_role,
            },
        ],
    }


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
    monkeypatch.setattr(IamClient, "list_my_tenants", lambda _self, _token: _identity())
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


def test_callback_creates_server_session_and_only_projects_selected_tenant(oidc_client, oidc_app):
    _login(oidc_client)

    response = oidc_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["iam_user_id"] == IAM_USER_ID
    assert data["current_tenant"]["iam_id"] == PERSONAL_ID
    assert {item["id"] for item in data["tenants"]} == {PERSONAL_ID, ENTERPRISE_ID}
    assert next(item for item in data["tenants"] if item["id"] == ENTERPRISE_ID)["local_id"] is None

    cookie = response.headers.get("Set-Cookie", "")
    assert "server-only-access-token" not in cookie
    assert "server-only-refresh-token" not in cookie
    assert "server-only-id-token" not in cookie
    with oidc_app.app_context():
        assert User.query.filter_by(iam_user_id=IAM_USER_ID).count() == 1
        assert Tenant.query.filter_by(iam_tenant_id=PERSONAL_ID).count() == 1
        assert Tenant.query.filter_by(iam_tenant_id=ENTERPRISE_ID).count() == 0


def test_switch_tenant_requires_csrf_and_projects_on_demand(oidc_client, oidc_app):
    csrf = _login(oidc_client)

    rejected = oidc_client.post(
        "/api/v1/auth/switch-tenant", json={"tenant_id": ENTERPRISE_ID}
    )
    assert rejected.status_code == 403

    response = oidc_client.post(
        "/api/v1/auth/switch-tenant",
        json={"tenant_id": ENTERPRISE_ID},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["role"] == "member"
    with oidc_app.app_context():
        tenant = Tenant.query.filter_by(iam_tenant_id=ENTERPRISE_ID).one()
        membership = TenantMembership.query.filter_by(tenant_id=tenant.id).one()
        assert membership.iam_role == "member"


def test_identity_refresh_reprojects_role_change(oidc_client, oidc_app, monkeypatch):
    csrf = _login(oidc_client)
    response = oidc_client.post(
        "/api/v1/auth/switch-tenant",
        json={"tenant_id": ENTERPRISE_ID},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200

    monkeypatch.setattr(
        IamClient,
        "list_my_tenants",
        lambda _self, _token: _identity(enterprise_role="tenant_admin"),
    )
    response = oidc_client.post(
        "/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf}
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["role"] == "tenant_admin"
    with oidc_app.app_context():
        tenant = Tenant.query.filter_by(iam_tenant_id=ENTERPRISE_ID).one()
        membership = TenantMembership.query.filter_by(tenant_id=tenant.id).one()
        assert membership.iam_role == "tenant_admin"


def test_absolute_session_timeout_fails_closed(oidc_client):
    _login(oidc_client)
    with oidc_client.session_transaction() as browser_session:
        browser_session["created_at"] = 0

    response = oidc_client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_logout_clears_session_and_returns_keycloak_end_session_url(oidc_client):
    csrf = _login(oidc_client)

    response = oidc_client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 200
    logout_url = response.get_json()["data"]["logout_url"]
    assert "/protocol/openid-connect/logout?" in logout_url
    assert "id_token_hint=server-only-id-token" in logout_url
    assert "post_logout_redirect_uri=" in logout_url
    assert oidc_client.get("/api/v1/auth/me").status_code == 401


def test_login_uses_allowed_request_domain_for_callback(oidc_client):
    response = oidc_client.get(
        "/api/v1/auth/login",
        base_url="https://evaluation.fangcunleap.com",
    )

    assert response.status_code == 302
    query = parse_qs(urlsplit(response.location).query)
    assert query["redirect_uri"] == [
        "https://evaluation.fangcunleap.com/api/v1/auth/callback"
    ]


def test_login_rejects_unconfigured_request_domain(oidc_client):
    response = oidc_client.get(
        "/api/v1/auth/login",
        base_url="https://untrusted.example.com",
    )

    assert response.status_code == 400
    assert response.get_json()["message"] == "当前访问域名未配置为平台登录域名"


def test_callback_and_logout_stay_on_allowed_request_domain(oidc_client):
    origin = "https://evaluation.fangcunleap.com"
    callback = oidc_client.get("/api/v1/auth/callback", base_url=origin)
    assert callback.status_code == 302
    assert callback.location == f"{origin}/"
    with oidc_client.session_transaction(base_url=origin) as browser_session:
        csrf = browser_session["csrf_token"]

    response = oidc_client.post(
        "/api/v1/auth/logout",
        base_url=origin,
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 200
    logout_url = response.get_json()["data"]["logout_url"]
    query = parse_qs(urlsplit(logout_url).query)
    assert query["post_logout_redirect_uri"] == [f"{origin}/#/login"]


def test_runtime_projection_never_claims_unmigrated_local_account(oidc_client, oidc_app):
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
        legacy = User.query.filter_by(username="alice").one()
        assert legacy.iam_user_id is None
        assert User.query.count() == 1
