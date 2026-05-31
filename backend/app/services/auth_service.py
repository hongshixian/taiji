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

def register_user(username: str, email: str, password: str,
                  tenant_slug: str = "guest") -> User:
    """注册用户

    Args:
        tenant_slug: 默认进 guest 租户（公开注册不应进 default）
    """
    from app.models.tenant import Tenant
    from flask import g

    # 公开注册需要绕过 tenant filter 查 tenant + 检查用户名冲突
    g.bypass_tenant_filter = True
    try:
        tenant = Tenant.query.filter_by(slug=tenant_slug).first()
        if not tenant:
            raise BusinessError(ErrorCode.VALIDATION_ERROR, f"租户 {tenant_slug} 不存在")

        # 同 tenant 内 username/email 唯一
        if User.query.filter_by(tenant_id=tenant.id, username=username).first():
            raise BusinessError(ErrorCode.USER_EXISTS)
        if User.query.filter_by(tenant_id=tenant.id, email=email).first():
            raise BusinessError(ErrorCode.EMAIL_EXISTS)

        role_id = _role_id_by_name("user")
        user = User(
            tenant_id=tenant.id,
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role="user",
            role_id=role_id,
        )
        db.session.add(user)
        db.session.commit()
        return user
    finally:
        g.bypass_tenant_filter = False


def login_user(username: str, password: str, tenant_slug: str | None = None) -> dict:
    """登录

    Args:
        username: 用户名
        password: 密码
        tenant_slug: 租户 slug；不提供则在所有 tenant 中按 username 查（兼容旧接口）
    """
    from app.models.tenant import Tenant
    from flask import g

    # 登录是公开接口，需要绕过 tenant filter 才能查到任何 tenant 下的用户
    g.bypass_tenant_filter = True
    try:
        if tenant_slug:
            tenant = Tenant.query.filter_by(slug=tenant_slug).first()
            if not tenant:
                raise BusinessError(ErrorCode.INVALID_CREDENTIAL)
            user = User.query.filter_by(tenant_id=tenant.id, username=username).first()
        else:
            # 兼容：未指定 tenant 时，按 username 查（多 tenant 重名时只取第一个）
            user = User.query.filter_by(username=username).first()
    finally:
        g.bypass_tenant_filter = False

    if not user or not check_password_hash(user.password_hash, password):
        raise BusinessError(ErrorCode.INVALID_CREDENTIAL)
    if not user.is_active:
        raise BusinessError(ErrorCode.ACCOUNT_DISABLED)

    # JWT additional_claims：perms / tenant_id / is_superuser
    # 改密 / 改角色时 tokens_revoked_at 会令旧 token 失效，所以 claim 缓存安全
    claims = {
        "perms": user.permissions,
        "tenant_id": user.tenant_id,
        "is_superuser": user.is_superuser,
    }
    access_token = create_access_token(identity=str(user.id), additional_claims=claims)
    refresh_token = create_refresh_token(identity=str(user.id), additional_claims=claims)

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


def create_user(username: str, email: str, password: str, role: str,
                tenant_id: int | None = None) -> User:
    """admin 创建用户（默认在当前 request 的 tenant 内）"""
    from flask import g

    if tenant_id is None:
        tenant_id = getattr(g, "tenant_id", None)
    if tenant_id is None:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "未指定租户")

    if User.query.filter_by(tenant_id=tenant_id, username=username).first():
        raise BusinessError(ErrorCode.USER_EXISTS)
    if User.query.filter_by(tenant_id=tenant_id, email=email).first():
        raise BusinessError(ErrorCode.EMAIL_EXISTS)

    user = User(
        tenant_id=tenant_id,
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


def seed_admin(username: str, email: str, password: str,
               tenant_slug: str = "default", is_superuser: bool = True):
    """确保存在管理员账号（不存在则创建）

    默认在 default 租户里建 admin 并设为 superuser，保证有人能管 tenants。

    注：这个函数被 entrypoint 在非 request 上下文调用，hook 会自动跳过 tenant filter。
    """
    from app.models.tenant import Tenant

    admin = User.query.filter_by(role="admin").first()
    if admin:
        return admin

    tenant = Tenant.query.filter_by(slug=tenant_slug).first()
    if not tenant:
        raise BusinessError(ErrorCode.VALIDATION_ERROR,
                            f"租户 {tenant_slug} 不存在（请先跑迁移）")

    admin = User(
        tenant_id=tenant.id,
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        role="admin",
        role_id=_role_id_by_name("admin"),
        is_superuser=is_superuser,
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
