"""权限装饰器"""

from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app import db
from app.models.user import User
from app.utils.roles import Role


def admin_required(fn):
    """要求管理员角色 —— 在 @jwt_required() 之后使用"""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = int(get_jwt_identity())
        user = db.session.get(User, user_id)
        if not user or not user.is_active:
            return jsonify({"code": 403, "message": "账户已禁用"}), 403
        if not user.is_admin:
            return jsonify({"code": 403, "message": "需要管理员权限"}), 403
        return fn(*args, **kwargs)

    return wrapper
