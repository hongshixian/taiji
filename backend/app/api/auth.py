"""认证接口"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token

from app.services.auth_service import register_user, login_user, get_user_by_id, user_to_dict

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    """用户注册"""
    data = request.get_json()
    if not data:
        return jsonify({"code": 400, "message": "请求体不能为空"}), 400

    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")

    # 参数校验
    if not username or not email or not password:
        return jsonify({"code": 400, "message": "用户名、邮箱和密码不能为空"}), 400
    if len(username) < 3 or len(username) > 80:
        return jsonify({"code": 400, "message": "用户名长度应为 3-80 个字符"}), 400
    if len(password) < 6:
        return jsonify({"code": 400, "message": "密码长度至少为 6 个字符"}), 400

    try:
        user = register_user(username, email, password)
        return jsonify({
            "code": 0,
            "message": "注册成功",
            "data": user_to_dict(user),
        }), 201
    except ValueError as e:
        return jsonify({"code": 400, "message": str(e)}), 400


@auth_bp.route("/login", methods=["POST"])
def login():
    """用户登录"""
    data = request.get_json()
    if not data:
        return jsonify({"code": 400, "message": "请求体不能为空"}), 400

    username = data.get("username", "")
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"code": 400, "message": "用户名和密码不能为空"}), 400

    try:
        result = login_user(username, password)
        return jsonify({
            "code": 0,
            "message": "登录成功",
            "data": result,
        }), 200
    except ValueError as e:
        return jsonify({"code": 401, "message": str(e)}), 401


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """刷新 access token"""
    user_id = get_jwt_identity()
    access_token = create_access_token(identity=user_id)
    return jsonify({
        "code": 0,
        "message": "Token 刷新成功",
        "data": {"access_token": access_token},
    }), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """获取当前用户信息"""
    user_id = int(get_jwt_identity())
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"code": 404, "message": "用户不存在"}), 404
    return jsonify({
        "code": 0,
        "message": "ok",
        "data": user_to_dict(user),
    }), 200