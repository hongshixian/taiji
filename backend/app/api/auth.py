"""Authentication endpoints for legacy JWT migration and the OIDC BFF."""

from datetime import datetime, timezone
import secrets

from authlib.integrations.base_client.errors import OAuthError
from flask import Blueprint, current_app, redirect, request, session
from flask_limiter import Limiter

from app import _get_client_ip, oauth
from app.auth_context import current_claims, current_user_id, login_required, oidc_mode
from app.schemas.auth_schema import ChangePasswordSchema, LoginSchema, RegisterSchema
from app.services.auth_service import (
    change_password,
    get_current_membership,
    get_user_by_id,
    list_current_user_memberships,
    login_user,
    refresh_access_token,
    register_user,
    switch_tenant,
    user_to_dict,
)
from app.services.oidc_session_service import (
    begin_oidc_session,
    clear_oidc_session,
    current_tenant_options,
    refresh_identity,
    switch_to_tenant,
)
from app.utils.errors import BusinessError, ErrorCode
from app.utils.jwt_blocklist import revoke_jti
from app.utils.response import created, ok
from app.utils.validation import validate_schema

auth_bp = Blueprint("auth", __name__)
auth_limiter = Limiter(key_func=_get_client_ip)


@auth_bp.route("/register", methods=["GET", "POST"])
@auth_limiter.limit("5 per minute")
def register():
    if oidc_mode():
        if request.method != "GET":
            raise BusinessError(ErrorCode.METHOD_NOT_ALLOWED, "注册由 IAM 托管")
        return _authorize_redirect(kc_action="register")

    data = request.get_json()
    if not data:
        raise BusinessError(ErrorCode.EMPTY_BODY)
    parsed, error = validate_schema(RegisterSchema(), data)
    if error:
        return error
    user = register_user(
        username=parsed["username"],
        email=parsed["email"],
        password=parsed["password"],
    )
    return created(user_to_dict(user), message="注册成功")


@auth_bp.route("/login", methods=["GET", "POST"])
@auth_limiter.limit("10 per minute")
def login():
    if oidc_mode():
        if request.method != "GET":
            raise BusinessError(ErrorCode.METHOD_NOT_ALLOWED, "登录由 IAM 托管")
        return _authorize_redirect()

    data = request.get_json()
    if not data:
        raise BusinessError(ErrorCode.EMPTY_BODY)
    parsed, error = validate_schema(LoginSchema(), data)
    if error:
        return error
    return ok(login_user(
        username=parsed["username"],
        password=parsed["password"],
    ), message="登录成功")


@auth_bp.route("/callback", methods=["GET"])
def callback():
    if not oidc_mode():
        raise BusinessError(ErrorCode.NOT_FOUND)
    try:
        token = oauth.keycloak.authorize_access_token()
    except OAuthError as exc:
        raise BusinessError(ErrorCode.TOKEN_INVALID, "OIDC 回调校验失败") from exc
    userinfo = token.get("userinfo")
    if not userinfo:
        raise BusinessError(ErrorCode.TOKEN_INVALID, "OIDC 响应缺少用户身份")
    roles = userinfo.get("realm_access", {}).get("roles", [])
    begin_oidc_session(token, dict(userinfo), is_superuser="platform_admin" in roles)
    target = current_app.config["OIDC_POST_LOGIN_PATH"]
    return redirect(f"{current_app.config['TAIJI_PUBLIC_URL']}{target}")


@auth_bp.route("/refresh", methods=["POST"])
@login_required(refresh=True)
@auth_limiter.limit("30 per minute")
def refresh():
    if oidc_mode():
        refresh_identity(force=True)
        return ok(_current_user_payload(), message="身份会话已刷新")
    tenant_id = current_claims().get("tenant_id")
    access_token = refresh_access_token(current_user_id(), tenant_id)
    return ok({"access_token": access_token}, message="Token 已刷新")


@auth_bp.route("/me", methods=["GET"])
@login_required()
def me():
    if oidc_mode():
        refresh_identity(force=False)
        return ok(_current_user_payload())
    user = get_user_by_id(current_user_id())
    if not user:
        raise BusinessError(ErrorCode.USER_NOT_FOUND)
    membership = get_current_membership(user.id)
    return ok(user_to_dict(user, membership, include_memberships=True))


@auth_bp.route("/tenants", methods=["GET"])
@login_required()
def my_tenants():
    if oidc_mode():
        refresh_identity(force=False)
        return ok(current_tenant_options())
    return ok(list_current_user_memberships(current_user_id()))


@auth_bp.route("/switch-tenant", methods=["POST"])
@login_required()
@auth_limiter.limit("10 per minute")
def switch_current_tenant():
    data = request.get_json() or {}
    tenant_id = data.get("tenant_id")
    if tenant_id is None:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "tenant_id 不能为空")
    if not oidc_mode():
        return ok(switch_tenant(current_user_id(), tenant_id), message="租户已切换")

    tenants = refresh_identity(force=True)
    selected = next((item for item in tenants if item["id"] == str(tenant_id)), None)
    if selected is None:
        raise BusinessError(ErrorCode.TENANT_NOT_FOUND, "用户不属于该租户或租户已停用")
    tenant, membership = switch_to_tenant(selected, tenants=tenants)
    return ok({
        "tenant": dict(selected, local_id=tenant.id),
        "role": membership.iam_role,
        "permissions": membership.permission_codes,
        "csrf_token": session["csrf_token"],
    }, message="租户已切换")


@auth_bp.route("/logout", methods=["POST"])
@login_required()
def logout():
    if oidc_mode():
        clear_oidc_session()
        return ok(message="已退出登录")
    payload = current_claims()
    ttl = max(0, payload["exp"] - int(datetime.now(timezone.utc).timestamp()))
    revoke_jti(payload["jti"], ttl)
    return ok(message="已退出登录")


@auth_bp.route("/password", methods=["PUT"])
@login_required()
@auth_limiter.limit("5 per minute")
def update_password():
    if oidc_mode():
        realm = current_app.config["IAM_REALM"]
        return ok({
            "account_url": f"{current_app.config['IAM_PUBLIC_URL']}/realms/{realm}/account/"
        }, message="密码由 IAM 管理")

    data = request.get_json()
    if not data:
        raise BusinessError(ErrorCode.EMPTY_BODY)
    parsed, error = validate_schema(ChangePasswordSchema(), data)
    if error:
        return error
    change_password(current_user_id(), parsed["old_password"], parsed["new_password"])
    return ok(message="密码已修改，请重新登录")


def _authorize_redirect(**params):
    redirect_uri = (
        f"{current_app.config['TAIJI_PUBLIC_URL']}/api/v1/auth/callback"
    )
    return oauth.keycloak.authorize_redirect(
        redirect_uri,
        nonce=secrets.token_urlsafe(32),
        **params,
    )


def _current_user_payload() -> dict:
    user = get_user_by_id(current_user_id())
    if not user:
        raise BusinessError(ErrorCode.USER_NOT_FOUND)
    membership = get_current_membership(user.id)
    payload = user_to_dict(user, membership)
    payload["tenants"] = current_tenant_options()
    payload["csrf_token"] = session["csrf_token"]
    payload["auth_mode"] = "oidc"
    return payload
