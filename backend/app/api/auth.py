"""认证接口"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.services.auth_service import (
    register_user,
    login_user,
    get_user_by_id,
    user_to_dict,
)
from app.schemas.auth_schema import RegisterSchema, LoginSchema
from app.utils.validation import validate_schema
from app.utils.response import ok, created
from app.utils.errors import BusinessError, ErrorCode

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
    )
    return ok(result, message="登录成功")


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """刷新 access token"""
    user_id = int(get_jwt_identity())
    access_token = create_access_token(identity=str(user_id))
    return ok({"access_token": access_token}, message="Token 已刷新")


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """获取当前用户信息"""
    user_id = int(get_jwt_identity())
    user = get_user_by_id(user_id)
    if not user:
        raise BusinessError(ErrorCode.USER_NOT_FOUND)
    return ok(user_to_dict(user))
