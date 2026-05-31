"""权限装饰器

设计：
- @require_permission(*codes) 是基础装饰器，从 JWT claim 读 perms 列表判断
- @admin_required 是兼容层，等价于 @require_permission("user:read")（admin 才有此权限）
- @superuser_required 预留给阶段三（多租户的平台运维）
"""

from functools import wraps
from flask_jwt_extended import get_jwt

from app.utils.errors import BusinessError, ErrorCode


def require_permission(*codes: str):
    """要求当前用户拥有【所有】指定权限码 — 在 @jwt_required() 之后使用

    用法:
        @require_permission("user:write")
        @require_permission("user:read", "role:assign")  # AND
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user_perms = set(get_jwt().get("perms", []))
            missing = set(codes) - user_perms
            if missing:
                raise BusinessError(
                    ErrorCode.PERMISSION_DENIED,
                    f"缺少权限: {', '.join(sorted(missing))}",
                )
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def admin_required(fn):
    """兼容层 — 仅要求 user:read 权限（其实是要求 admin 角色）

    新代码请直接用 @require_permission(...) 表达具体所需权限。
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_perms = set(get_jwt().get("perms", []))
        if "user:read" not in user_perms:
            raise BusinessError(ErrorCode.PERMISSION_DENIED)
        return fn(*args, **kwargs)
    return wrapper
