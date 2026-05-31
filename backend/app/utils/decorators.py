"""权限装饰器"""

from functools import wraps
from flask_jwt_extended import get_jwt_identity

from app import db
from app.models.user import User
from app.utils.errors import BusinessError, ErrorCode


def admin_required(fn):
    """要求管理员角色 —— 在 @jwt_required() 之后使用"""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        # JWT 已由 @jwt_required() 验证，这里只查 user
        user_id = int(get_jwt_identity())
        user = db.session.get(User, user_id)
        if not user or not user.is_active:
            raise BusinessError(ErrorCode.AUTH_DISABLED)
        if not user.is_admin:
            raise BusinessError(ErrorCode.PERMISSION_DENIED)
        return fn(*args, **kwargs)

    return wrapper
