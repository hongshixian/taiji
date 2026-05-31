"""认证业务逻辑"""

from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token

from app import db
from app.models.user import User
from app.utils.errors import BusinessError, ErrorCode


def _revoke_marker() -> datetime:
    """生成 tokens_revoked_at 时间戳：向上取整到下一秒。

    JWT iat 精度是秒；设为 now 会让"同秒内紧接着重新登录"的新 token 也被吊销。
    向上取整到下一秒确保：所有早于"下一秒"的 token 失效，新登录的 token（iat ≥ 下一秒）不受影响。
    """
    now = datetime.now(timezone.utc)
    return (now.replace(microsecond=0) + timedelta(seconds=1))


# ─── 认证 ────────────────────────────────

def register_user(username: str, email: str, password: str) -> User:
    if User.query.filter_by(username=username).first():
        raise BusinessError(ErrorCode.USER_EXISTS)
    if User.query.filter_by(email=email).first():
        raise BusinessError(ErrorCode.EMAIL_EXISTS)

    role_id = _role_id_by_name("user")
    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        role="user",
        role_id=role_id,
    )
    db.session.add(user)
    db.session.commit()
    return user


def login_user(username: str, password: str) -> dict:
    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        raise BusinessError(ErrorCode.INVALID_CREDENTIAL)
    if not user.is_active:
        raise BusinessError(ErrorCode.ACCOUNT_DISABLED)

    # JWT additional_claims：把权限码列表塞进 access token，避免每请求查 DB
    # 改密 / 改角色时 tokens_revoked_at 会令旧 token 失效，所以 perms 缓存安全
    claims = {"perms": user.permissions}
    access_token = create_access_token(identity=str(user.id), additional_claims=claims)
    refresh_token = create_refresh_token(identity=str(user.id))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user_to_dict(user),
    }


def get_user_by_id(user_id: int) -> User | None:
    return db.session.get(User, user_id)


def user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "role_id": user.role_id,
        "role_name": user.role_obj.name if user.role_obj else user.role,
        "permissions": user.permissions,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


# ─── 管理员操作用户 ──────────────────────

def list_users(page: int, per_page: int) -> tuple[list, int]:
    """分页查询所有用户"""
    pagination = User.query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return [user_to_dict(u) for u in pagination.items], pagination.total


def create_user(username: str, email: str, password: str, role: str) -> User:
    if User.query.filter_by(username=username).first():
        raise BusinessError(ErrorCode.USER_EXISTS)
    if User.query.filter_by(email=email).first():
        raise BusinessError(ErrorCode.EMAIL_EXISTS)

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        role=role,
        role_id=_role_id_by_name(role),
    )
    db.session.add(user)
    db.session.commit()
    return user


def update_user(user_id: int, data: dict) -> User:
    user = db.session.get(User, user_id)
    if not user:
        raise BusinessError(ErrorCode.USER_NOT_FOUND)

    # 监测需要撤销该用户所有 token 的变更
    revoke_tokens = False

    if "username" in data and data["username"] != user.username:
        if User.query.filter_by(username=data["username"]).first():
            raise BusinessError(ErrorCode.USER_EXISTS)
        user.username = data["username"]
    if "email" in data and data["email"] != user.email:
        if User.query.filter_by(email=data["email"]).first():
            raise BusinessError(ErrorCode.EMAIL_EXISTS)
        user.email = data["email"]
    if "role" in data and data["role"] != user.role:
        user.role = data["role"]
        user.role_id = _role_id_by_name(data["role"])
        revoke_tokens = True  # 角色变更应使旧 token 失效
    if "is_active" in data and data["is_active"] != user.is_active:
        user.is_active = data["is_active"]
        if not data["is_active"]:
            revoke_tokens = True  # 禁用账户：踢出所有会话
    if "password" in data and data["password"]:
        user.password_hash = generate_password_hash(data["password"])
        revoke_tokens = True  # 改密：踢出所有会话

    if revoke_tokens:
        user.tokens_revoked_at = _revoke_marker()

    db.session.commit()
    return user


def change_password(user_id: int, old_password: str, new_password: str) -> User:
    """用户自助修改密码 — 需校验旧密码，成功后踢掉自己所有会话"""
    user = db.session.get(User, user_id)
    if not user:
        raise BusinessError(ErrorCode.USER_NOT_FOUND)
    if not check_password_hash(user.password_hash, old_password):
        raise BusinessError(ErrorCode.INVALID_CREDENTIAL, "旧密码错误")

    user.password_hash = generate_password_hash(new_password)
    user.tokens_revoked_at = _revoke_marker()
    db.session.commit()
    return user


def delete_user(user_id: int, current_user_id: int):
    if user_id == current_user_id:
        raise BusinessError(ErrorCode.CANNOT_DELETE_SELF)
    user = db.session.get(User, user_id)
    if not user:
        raise BusinessError(ErrorCode.USER_NOT_FOUND)
    db.session.delete(user)
    db.session.commit()


def seed_admin(username: str, email: str, password: str):
    """确保存在管理员账号（不存在则创建）"""
    admin = User.query.filter_by(role="admin").first()
    if admin:
        return admin
    admin = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        role="admin",
        role_id=_role_id_by_name("admin"),
    )
    db.session.add(admin)
    db.session.commit()
    return admin


# ─── 内部工具 ────────────────────────────────

def _role_id_by_name(name: str) -> int | None:
    """根据角色名找 role_id；找不到返回 None（兼容尚未跑 RBAC migration 的环境）"""
    from app.models.role import Role
    role = Role.query.filter_by(name=name).first()
    return role.id if role else None
