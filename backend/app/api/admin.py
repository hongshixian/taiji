"""管理员接口（需 admin 角色）"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.services.auth_service import (
    list_users,
    create_user,
    update_user,
    delete_user,
    get_user_by_id,
    user_to_dict,
)
from app.utils.decorators import admin_required
from app.utils.roles import Role
from app.utils.response import ok, created, paginated
from app.utils.errors import BusinessError, ErrorCode

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/users", methods=["GET"])
@jwt_required()
@admin_required
def get_users():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    users, total = list_users(page, per_page)
    return paginated(items=users, total=total, page=page, per_page=per_page)


@admin_bp.route("/users/<int:user_id>", methods=["GET"])
@jwt_required()
@admin_required
def get_user(user_id):
    user = get_user_by_id(user_id)
    if not user:
        raise BusinessError(ErrorCode.USER_NOT_FOUND)
    return ok(user_to_dict(user))


@admin_bp.route("/users", methods=["POST"])
@jwt_required()
@admin_required
def add_user():
    data = request.get_json()
    if not data:
        raise BusinessError(ErrorCode.EMPTY_BODY)

    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    role = data.get("role", Role.USER)

    if not username or not email or not password:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "用户名、邮箱、密码不能为空")
    if len(password) < 6:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "密码至少 6 位")
    if not Role.is_valid(role):
        raise BusinessError(ErrorCode.INVALID_ROLE)

    user = create_user(username, email, password, role)
    return created(user_to_dict(user))


@admin_bp.route("/users/<int:user_id>", methods=["PUT"])
@jwt_required()
@admin_required
def edit_user(user_id):
    data = request.get_json()
    if not data:
        raise BusinessError(ErrorCode.EMPTY_BODY)

    role = data.get("role")
    if role is not None and not Role.is_valid(role):
        raise BusinessError(ErrorCode.INVALID_ROLE)

    user = update_user(user_id, data)
    return ok(user_to_dict(user))


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def remove_user(user_id):
    current_user_id = int(get_jwt_identity())
    delete_user(user_id, current_user_id)
    return ok(message="已删除")
