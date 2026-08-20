"""OIDC token lifecycle and Redis-backed Taiji browser session."""

import secrets
import time

import requests
from flask import current_app, g, session

from app import db
from app.models.tenant import PERSONAL_TENANT_TYPE, Tenant
from app.models.tenant_membership import TenantMembership
from app.models.user import User
from app.services.auth_service import membership_to_dict, provision_oidc_user
from app.utils.decorators import bypass_tenant_filter
from app.utils.errors import BusinessError, ErrorCode


TOKEN_FIELDS = {
    "access_token", "refresh_token", "expires_at", "expires_in", "refresh_expires_in",
    "token_type", "id_token", "scope", "session_state",
}


def begin_oidc_session(token: dict, userinfo: dict, is_superuser: bool = False):
    user, membership = provision_oidc_user(
        dict(userinfo), bootstrap_superuser=bool(is_superuser)
    )

    current_app.session_interface.regenerate(session)
    session.clear()
    now = int(time.time())
    session.update({
        "user_id": user.id,
        "tenant_id": membership.tenant_id,
        "membership_id": membership.id,
        "role": membership_to_dict(membership)["role"],
        "permissions": membership.permission_codes,
        "is_superuser": bool(user.is_superuser),
        "csrf_token": secrets.token_urlsafe(32),
        "oidc_token": _serializable_token(token),
        "identity_verified_at": now,
        "created_at": now,
        "last_seen_at": now,
    })
    session.permanent = True
    _load_request_context()
    return user, membership


def refresh_identity(*, force: bool) -> list[dict]:
    """Refresh the OIDC token when requested, then reload Taiji-owned authorization."""
    if force:
        _valid_token()

    with bypass_tenant_filter():
        user = db.session.get(User, session.get("user_id"))
        if user is None:
            clear_oidc_session()
            raise BusinessError(ErrorCode.USER_NOT_FOUND)
        if not user.is_active:
            clear_oidc_session()
            raise BusinessError(ErrorCode.ACCOUNT_DISABLED)

        membership = _active_membership(user.id, session.get("tenant_id"))
        if membership is None:
            membership = _default_membership(user.id)
        if membership is None:
            clear_oidc_session()
            raise BusinessError(ErrorCode.TENANT_NOT_FOUND, "用户没有可用租户")
        _apply_membership(user, membership)

    session["identity_verified_at"] = int(time.time())
    return current_tenant_options()


def switch_to_tenant(tenant_id: int):
    with bypass_tenant_filter():
        user = db.session.get(User, session.get("user_id"))
        if user is None or not user.is_active:
            raise BusinessError(ErrorCode.ACCOUNT_DISABLED)
        membership = _active_membership(user.id, int(tenant_id))
        if membership is None:
            raise BusinessError(ErrorCode.TENANT_NOT_FOUND, "用户不属于该租户或租户已停用")
        _apply_membership(user, membership)
        _load_request_context()
        return membership.tenant, membership


def current_tenant_options() -> list[dict]:
    user_id = session.get("user_id")
    if user_id is None:
        return []
    with bypass_tenant_filter():
        memberships = (
            TenantMembership.query
            .join(Tenant, Tenant.id == TenantMembership.tenant_id)
            .filter(
                TenantMembership.user_id == user_id,
                TenantMembership.is_active.is_(True),
                Tenant.is_active.is_(True),
            )
            .order_by(
                (Tenant.tenant_type == PERSONAL_TENANT_TYPE).desc(),
                TenantMembership.id,
            )
            .all()
        )
        return [
            {
                "id": membership.tenant_id,
                "local_id": membership.tenant_id,
                "slug": membership.tenant.slug,
                "name": membership.tenant.name,
                "tenant_type": membership.tenant.tenant_type,
                "enabled": True,
                "role": membership_to_dict(membership)["role"],
            }
            for membership in memberships
        ]


def local_session_projection_stale() -> bool:
    """Detect local authorization changes that must replace cached session values."""
    membership_id = session.get("membership_id")
    user_id = session.get("user_id")
    with bypass_tenant_filter():
        membership = db.session.get(TenantMembership, membership_id) if membership_id else None
        user = db.session.get(User, user_id) if user_id else None
    if user is None or not user.is_active:
        return True
    if bool(user.is_superuser) != bool(session.get("is_superuser", False)):
        return True
    if membership is None or not membership.is_active:
        return True
    if membership.tenant is None or not membership.tenant.is_active:
        return True
    return (
        membership.tenant_id != session.get("tenant_id")
        or membership_to_dict(membership)["role"] != session.get("role")
        or sorted(membership.permission_codes) != sorted(session.get("permissions", []))
    )


def clear_oidc_session():
    session.clear()


def _valid_token() -> dict:
    token = dict(session.get("oidc_token") or {})
    if not token.get("access_token"):
        clear_oidc_session()
        raise BusinessError(ErrorCode.TOKEN_MISSING, "身份会话缺少 Access Token")
    if int(token.get("expires_at", 0)) > int(time.time()) + 30:
        return token
    refresh_token = token.get("refresh_token")
    if not refresh_token:
        clear_oidc_session()
        raise BusinessError(ErrorCode.TOKEN_EXPIRED, "身份会话无法刷新")

    realm = current_app.config["IAM_REALM"]
    token_url = (
        f"{current_app.config['IAM_INTERNAL_URL']}/realms/{realm}"
        "/protocol/openid-connect/token"
    )
    try:
        response = requests.post(
            token_url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": current_app.config["OIDC_CLIENT_ID"],
                "client_secret": current_app.config["OIDC_CLIENT_SECRET"],
            },
            timeout=10,
        )
    except requests.RequestException as exc:
        raise BusinessError(ErrorCode.IAM_UNAVAILABLE, "认证服务暂时不可用") from exc
    if response.status_code >= 400:
        clear_oidc_session()
        raise BusinessError(ErrorCode.TOKEN_EXPIRED, "身份会话已失效，请重新登录")

    refreshed = response.json()
    if "refresh_token" not in refreshed:
        refreshed["refresh_token"] = refresh_token
    token = _serializable_token(refreshed)
    session["oidc_token"] = token
    return token


def _serializable_token(token: dict) -> dict:
    result = {key: value for key, value in token.items() if key in TOKEN_FIELDS and value is not None}
    if "expires_at" not in result:
        result["expires_at"] = int(time.time()) + int(result.get("expires_in", 0))
    return result


def _active_membership(user_id: int, tenant_id: int | None) -> TenantMembership | None:
    if tenant_id is None:
        return None
    return (
        TenantMembership.query
        .join(Tenant, Tenant.id == TenantMembership.tenant_id)
        .filter(
            TenantMembership.user_id == user_id,
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.is_active.is_(True),
            Tenant.is_active.is_(True),
        )
        .first()
    )


def _default_membership(user_id: int) -> TenantMembership | None:
    return (
        TenantMembership.query
        .join(Tenant, Tenant.id == TenantMembership.tenant_id)
        .filter(
            TenantMembership.user_id == user_id,
            TenantMembership.is_active.is_(True),
            Tenant.is_active.is_(True),
        )
        .order_by(
            (Tenant.tenant_type == PERSONAL_TENANT_TYPE).desc(),
            TenantMembership.id,
        )
        .first()
    )


def _apply_membership(user: User, membership: TenantMembership) -> None:
    session["tenant_id"] = membership.tenant_id
    session["membership_id"] = membership.id
    session["role"] = membership_to_dict(membership)["role"]
    session["permissions"] = membership.permission_codes
    session["is_superuser"] = bool(user.is_superuser)


def _load_request_context():
    g.current_user_id = session.get("user_id")
    g.tenant_id = session.get("tenant_id")
    g.is_superuser = bool(session.get("is_superuser", False))
    g.auth_claims = {
        "tenant_id": g.tenant_id,
        "perms": session.get("permissions", []),
        "is_superuser": g.is_superuser,
        "role": session.get("role"),
    }
