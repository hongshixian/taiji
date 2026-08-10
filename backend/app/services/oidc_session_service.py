"""OIDC token lifecycle and Redis-backed Taiji browser session."""

import secrets
import time

from flask import current_app, g, session

from app.services.iam_client import IamClient, IamHttpError, as_business_error
from app.services.iam_projection_service import (
    project_login,
    project_selected_tenant,
    tenant_options,
)
from app.utils.errors import BusinessError, ErrorCode


TOKEN_FIELDS = {
    "access_token", "refresh_token", "expires_at", "expires_in", "refresh_expires_in",
    "token_type", "id_token", "scope", "session_state",
}


def begin_oidc_session(token: dict, userinfo: dict, is_superuser: bool = False):
    try:
        identity = IamClient().list_my_tenants(token["access_token"])
    except IamHttpError as error:
        raise as_business_error(error) from error
    is_superuser = bool(identity.get("platform_admin", is_superuser))
    user, tenant, membership, selected, tenants = project_login(
        dict(userinfo), identity, is_superuser=is_superuser
    )

    current_app.session_interface.regenerate(session)
    session.clear()
    now = int(time.time())
    session.update({
        "user_id": user.id,
        "iam_user_id": user.iam_user_id,
        "tenant_id": tenant.id,
        "iam_tenant_id": selected["id"],
        "membership_id": membership.id,
        "iam_role": membership.iam_role,
        "permissions": membership.permission_codes,
        "is_superuser": bool(is_superuser),
        "csrf_token": secrets.token_urlsafe(32),
        "iam_token": _serializable_token(token),
        "iam_tenants": tenants,
        "identity_verified_at": now,
        "created_at": now,
        "last_seen_at": now,
    })
    session.permanent = True
    _load_request_context()
    return user, membership


def refresh_identity(*, force: bool) -> list[dict]:
    cached = session.get("iam_tenants", [])
    verified_at = int(session.get("identity_verified_at", 0))
    cache_seconds = current_app.config["IAM_IDENTITY_CACHE_SECONDS"]
    if not force and cached and int(time.time()) - verified_at < cache_seconds:
        return cached

    try:
        token = _valid_token()
        identity = IamClient().list_my_tenants(token["access_token"])
    except IamHttpError as error:
        if not force and cached and int(time.time()) - verified_at < cache_seconds:
            return cached
        if error.status in {401, 403}:
            clear_oidc_session()
        raise as_business_error(error) from error

    tenants = [
        item for item in identity.get("tenants", [])
        if item.get("enabled", True) and item.get("lifecycle_status", "active") == "active"
        and item.get("role") in {"tenant_admin", "member"}
    ]
    if not tenants:
        clear_oidc_session()
        raise BusinessError(ErrorCode.TENANT_NOT_FOUND, "IAM 未返回可用租户")

    is_superuser = bool(identity.get("platform_admin", False))
    from app import db
    from app.models.user import User
    from app.utils.decorators import bypass_tenant_filter
    with bypass_tenant_filter():
        user = db.session.get(User, session["user_id"])
        if user is None:
            clear_oidc_session()
            raise BusinessError(ErrorCode.USER_NOT_FOUND)
        user.is_superuser = is_superuser
        user.is_active = True
        db.session.commit()
    session["is_superuser"] = is_superuser

    target = next((item for item in tenants if item["id"] == session.get("iam_tenant_id")), None)
    if target is None:
        target = next((item for item in tenants if item.get("tenant_type") == "personal"), tenants[0])
    # Re-project even when the tenant did not change: its role or lifecycle may have changed.
    switch_to_tenant(target, tenants=tenants)
    session["iam_tenants"] = tenants
    session["identity_verified_at"] = int(time.time())
    return tenants


def switch_to_tenant(tenant_payload: dict, *, tenants: list[dict] | None = None):
    tenant, membership = project_selected_tenant(session["user_id"], tenant_payload)
    session["tenant_id"] = tenant.id
    session["iam_tenant_id"] = tenant_payload["id"]
    session["membership_id"] = membership.id
    session["iam_role"] = membership.iam_role
    session["permissions"] = membership.permission_codes
    if tenants is not None:
        session["iam_tenants"] = tenants
    _load_request_context()
    return tenant, membership


def current_tenant_options() -> list[dict]:
    return tenant_options(session.get("iam_tenants", []))


def current_iam_access_token() -> str:
    """Return a refreshed IAM access token for server-side controlled API calls."""
    try:
        return _valid_token()["access_token"]
    except IamHttpError as error:
        if error.status in {401, 403}:
            clear_oidc_session()
        raise as_business_error(error) from error


def local_session_projection_stale() -> bool:
    """Detect controlled IAM changes reflected in the shared local projection."""
    from app import db
    from app.models.tenant_membership import TenantMembership
    from app.models.user import User
    from app.utils.decorators import bypass_tenant_filter

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
        or membership.iam_role != session.get("iam_role")
        or sorted(membership.permission_codes) != sorted(session.get("permissions", []))
    )


def clear_oidc_session():
    session.clear()


def _valid_token() -> dict:
    token = dict(session.get("iam_token") or {})
    if not token.get("access_token"):
        raise IamHttpError(401, "missing_token", "身份会话缺少 Access Token")
    if int(token.get("expires_at", 0)) > int(time.time()) + 30:
        return token
    refresh_token = token.get("refresh_token")
    if not refresh_token:
        raise IamHttpError(401, "missing_refresh_token", "身份会话无法刷新")
    refreshed = IamClient().refresh_token(refresh_token)
    if "refresh_token" not in refreshed:
        refreshed["refresh_token"] = refresh_token
    if "expires_at" not in refreshed:
        refreshed["expires_at"] = int(time.time()) + int(refreshed.get("expires_in", 0))
    token = _serializable_token(refreshed)
    session["iam_token"] = token
    return token


def _serializable_token(token: dict) -> dict:
    result = {key: value for key, value in token.items() if key in TOKEN_FIELDS and value is not None}
    if "expires_at" not in result:
        result["expires_at"] = int(time.time()) + int(result.get("expires_in", 0))
    return result


def _load_request_context():
    g.current_user_id = session.get("user_id")
    g.tenant_id = session.get("tenant_id")
    g.is_superuser = bool(session.get("is_superuser", False))
    g.auth_claims = {
        "tenant_id": g.tenant_id,
        "perms": session.get("permissions", []),
        "is_superuser": g.is_superuser,
        "iam_role": session.get("iam_role"),
    }
