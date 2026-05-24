"""管理员接口（需 admin 角色）"""

from flask import Blueprint, request, jsonify
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

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/users", methods=["GET"])
@jwt_required()
@admin_required
def get_users():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    users, total = list_users(page, per_page)
    return jsonify({"code": 0, "data": {"items": users, "total": total}}), 200


@admin_bp.route("/users/<int:user_id>", methods=["GET"])
@jwt_required()
@admin_required
def get_user(user_id):
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"code": 404, "message": "用户不存在"}), 404
    return jsonify({"code": 0, "data": user_to_dict(user)}), 200


@admin_bp.route("/users", methods=["POST"])
@jwt_required()
@admin_required
def add_user():
    data = request.get_json()
    if not data:
        return jsonify({"code": 400, "message": "请求体不能为空"}), 400

    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    role = data.get("role", Role.USER)

    if not username or not email or not password:
        return jsonify({"code": 400, "message": "用户名、邮箱、密码不能为空"}), 400
    if len(password) < 6:
        return jsonify({"code": 400, "message": "密码至少 6 位"}), 400
    if not Role.is_valid(role):
        return jsonify({"code": 400, "message": "无效的角色"}), 400

    try:
        user = create_user(username, email, password, role)
        return jsonify({"code": 0, "data": user_to_dict(user)}), 201
    except ValueError as e:
        return jsonify({"code": 400, "message": str(e)}), 400


@admin_bp.route("/users/<int:user_id>", methods=["PUT"])
@jwt_required()
@admin_required
def edit_user(user_id):
    data = request.get_json()
    if not data:
        return jsonify({"code": 400, "message": "请求体不能为空"}), 400

    role = data.get("role")
    if role is not None and not Role.is_valid(role):
        return jsonify({"code": 400, "message": "无效的角色"}), 400

    try:
        user = update_user(user_id, data)
        return jsonify({"code": 0, "data": user_to_dict(user)}), 200
    except ValueError as e:
        return jsonify({"code": 400, "message": str(e)}), 400


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def remove_user(user_id):
    current_user_id = int(get_jwt_identity())
    try:
        delete_user(user_id, current_user_id)
        return jsonify({"code": 0, "message": "已删除"}), 200
    except ValueError as e:
        return jsonify({"code": 400, "message": str(e)}), 400
