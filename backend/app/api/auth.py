"""认证接口"""

from datetime import datetime, timezone

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from flask_limiter import Limiter

from app import _get_client_ip
from app.services.auth_service import (
    register_user,
    login_user,
    get_user_by_id,
    user_to_dict,
    change_password,
    get_current_membership,
    list_current_user_memberships,
    refresh_access_token,
    switch_tenant,
)
from app.schemas.auth_schema import RegisterSchema, LoginSchema, ChangePasswordSchema
from app.utils.validation import validate_schema
from app.utils.response import ok, created
from app.utils.errors import BusinessError, ErrorCode
from app.utils.jwt_blocklist import revoke_jti

auth_bp = Blueprint("auth", __name__)

# 本蓝图限流器 — 对敏感接口独立限制（使用与全局相同的 key 函数以支持反向代理）
auth_limiter = Limiter(key_func=_get_client_ip)


@auth_bp.route("/register", methods=["POST"])
@auth_limiter.limit("5 per minute")
def register():
    """用户注册 — 限流 5次/分钟"""
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


@auth_bp.route("/login", methods=["POST"])
@auth_limiter.limit("10 per minute")
def login():
    """用户登录 — 限流 10次/分钟"""
    data = request.get_json()
    if not data:
        raise BusinessError(ErrorCode.EMPTY_BODY)

    parsed, error = validate_schema(LoginSchema(), data)
    if error:
        return error

    result = login_user(
        username=parsed["username"],
        password=parsed["password"],
    )
    return ok(result, message="登录成功")


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
@auth_limiter.limit("30 per minute")
def refresh():
    """刷新 access token — 重新从当前 membership 读 perms，确保变更生效"""
    user_id = int(get_jwt_identity())
    tenant_id = get_jwt().get("tenant_id")
    access_token = refresh_access_token(user_id, tenant_id)
    return ok({"access_token": access_token}, message="Token 已刷新")


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """获取当前用户和当前租户成员身份信息。"""
    user_id = int(get_jwt_identity())
    user = get_user_by_id(user_id)
    if not user:
        raise BusinessError(ErrorCode.USER_NOT_FOUND)

    membership = get_current_membership(user_id)
    return ok(user_to_dict(user, membership, include_memberships=True))


@auth_bp.route("/tenants", methods=["GET"])
@jwt_required()
def my_tenants():
    """列出当前用户可切换的租户身份。"""
    user_id = int(get_jwt_identity())
    return ok(list_current_user_memberships(user_id))


@auth_bp.route("/switch-tenant", methods=["POST"])
@jwt_required()
@auth_limiter.limit("10 per minute")
def switch_current_tenant():
    """普通用户/管理员切换到自己拥有 membership 的租户。"""
    data = request.get_json() or {}
    tenant_id = data.get("tenant_id")
    if tenant_id is None:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "tenant_id 不能为空")
    result = switch_tenant(int(get_jwt_identity()), tenant_id)
    return ok(result, message="租户已切换")


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """退出登录 — 把当前 access token 的 jti 加入黑名单"""
    payload = get_jwt()
    jti = payload["jti"]
    exp = payload["exp"]
    now_ts = int(datetime.now(timezone.utc).timestamp())
    ttl = max(0, exp - now_ts)
    revoke_jti(jti, ttl)
    return ok(message="已退出登录")


@auth_bp.route("/password", methods=["PUT"])
@jwt_required()
@auth_limiter.limit("5 per minute")
def update_password():
    """用户自助修改密码 — 成功后所有会话失效，需要重新登录"""
    data = request.get_json()
    if not data:
        raise BusinessError(ErrorCode.EMPTY_BODY)

    parsed, error = validate_schema(ChangePasswordSchema(), data)
    if error:
        return error

    user_id = int(get_jwt_identity())
    change_password(user_id, parsed["old_password"], parsed["new_password"])
    return ok(message="密码已修改，请重新登录")
