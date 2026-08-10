"""Authentication context shared by legacy JWT and the OIDC BFF session."""

from functools import wraps

from flask import current_app, g
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from app.utils.errors import BusinessError, ErrorCode


def oidc_mode() -> bool:
    return current_app.config.get("AUTH_MODE") == "oidc"


def login_required(optional: bool = False, refresh: bool = False):
    """Require the active authentication mode without exposing it to handlers."""
    def decorator(fn):
        legacy_protected = jwt_required(optional=optional, refresh=refresh)(fn)

        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not oidc_mode():
                return legacy_protected(*args, **kwargs)
            if getattr(g, "current_user_id", None) is None:
                if optional:
                    return fn(*args, **kwargs)
                raise BusinessError(ErrorCode.TOKEN_MISSING, "登录会话不存在或已过期")
            return fn(*args, **kwargs)

        return wrapper
    return decorator


def current_user_id() -> int:
    if oidc_mode():
        user_id = getattr(g, "current_user_id", None)
    else:
        identity = get_jwt_identity()
        user_id = int(identity) if identity is not None else None
    if user_id is None:
        raise BusinessError(ErrorCode.TOKEN_MISSING, "登录会话不存在或已过期")
    return int(user_id)


def current_claims() -> dict:
    if oidc_mode():
        return getattr(g, "auth_claims", {})
    return get_jwt()
