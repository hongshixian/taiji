"""权限装饰器

设计：
- @require_permission(*codes) 是基础装饰器，从 JWT claim 读 perms 列表判断
- @admin_required 是兼容层，等价于 @require_permission("user:read")（admin 才有此权限）
- @superuser_required 用于平台运维（可跨 tenant 操作）
"""

from functools import wraps
from contextlib import contextmanager
from flask import g
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


def superuser_required(fn):
    """要求当前用户为平台超级管理员（is_superuser=true）

    用于 superadmin 蓝图——管理 tenants、跨 tenant 操作。
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if not claims.get("is_superuser", False):
            raise BusinessError(
                ErrorCode.PERMISSION_DENIED,
                "需要平台超级管理员权限",
            )
        return fn(*args, **kwargs)
    return wrapper


@contextmanager
def bypass_tenant_filter():
    """临时绕过 tenant filter — 用于需要跨 tenant 查询的内部场景

    用法:
        with bypass_tenant_filter():
            all_users = User.query.all()  # 看所有 tenant 的用户
    """
    old = getattr(g, "bypass_tenant_filter", False)
    g.bypass_tenant_filter = True
    try:
        yield
    finally:
        g.bypass_tenant_filter = old

