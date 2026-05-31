"""认证接口"""

from datetime import datetime, timezone

from flask import Blueprint, request
from app import db
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, get_jwt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.services.auth_service import (
    register_user,
    login_user,
    get_user_by_id,
    user_to_dict,
    change_password,
)
from app.schemas.auth_schema import RegisterSchema, LoginSchema, ChangePasswordSchema
from app.utils.validation import validate_schema
from app.utils.response import ok, created
from app.utils.errors import BusinessError, ErrorCode
from app.utils.jwt_blocklist import revoke_jti

auth_bp = Blueprint("auth", __name__)

# 本蓝图限流器 — 对敏感接口独立限制
auth_limiter = Limiter(key_func=get_remote_address)


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
        tenant_slug=parsed.get("tenant_slug"),
    )
    return ok(result, message="登录成功")


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """刷新 access token — 重新从 DB 读 perms / tenant_id / is_superuser，确保变更生效"""
    from app.models.user import User
    from app import db
    from flask import g

    user_id = int(get_jwt_identity())
    # refresh 时已有 token 自带 tenant_id claim，g.tenant_id 已设置
    # 但若用户被 superuser 跨 tenant 改了 tenant_id，refresh 需重新读 DB
    g.bypass_tenant_filter = True
    try:
        user = db.session.get(User, user_id)
    finally:
        g.bypass_tenant_filter = False

    if not user or not user.is_active:
        raise BusinessError(ErrorCode.ACCOUNT_DISABLED)

    claims = {
        "perms": user.permissions,
        "tenant_id": user.tenant_id,
        "is_superuser": user.is_superuser,
    }
    access_token = create_access_token(identity=str(user_id), additional_claims=claims)
    return ok({"access_token": access_token}, message="Token 已刷新")


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """获取当前用户信息

    在 user_to_dict 的基础上叠加"当前操作租户"上下文 (current_tenant)。
    对超管而言，user.tenant_* 反映"我归属哪里"，current_tenant 反映"我正在看哪里"——
    切换租户后只有 current_tenant 会变。普通用户两者一致。
    """
    from flask import g
    from app.models.tenant import Tenant

    user_id = int(get_jwt_identity())
    user = get_user_by_id(user_id)
    if not user:
        raise BusinessError(ErrorCode.USER_NOT_FOUND)

    data = user_to_dict(user)

    # 当前会话操作的租户（来自 JWT claim 的 tenant_id，可能与 user.tenant_id 不同）
    current_id = getattr(g, "tenant_id", None)
    current = None
    if current_id is not None:
        from app.utils.decorators import bypass_tenant_filter
        with bypass_tenant_filter():
            t = db.session.get(Tenant, current_id)
        if t:
            current = {"id": t.id, "slug": t.slug, "name": t.name, "plan": t.plan}
    data["current_tenant"] = current

    return ok(data)


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
