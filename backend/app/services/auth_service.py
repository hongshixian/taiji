"""认证业务逻辑"""

from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token

from app import db
from app.models.user import User
from app.utils.errors import BusinessError, ErrorCode


# ─── 认证 ────────────────────────────────

def register_user(username: str, email: str, password: str) -> User:
    if User.query.filter_by(username=username).first():
        raise BusinessError(ErrorCode.USER_EXISTS)
    if User.query.filter_by(email=email).first():
        raise BusinessError(ErrorCode.EMAIL_EXISTS)

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
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

    access_token = create_access_token(identity=str(user.id))
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
    )
    db.session.add(user)
    db.session.commit()
    return user


def update_user(user_id: int, data: dict) -> User:
    user = db.session.get(User, user_id)
    if not user:
        raise BusinessError(ErrorCode.USER_NOT_FOUND)

    if "username" in data and data["username"] != user.username:
        if User.query.filter_by(username=data["username"]).first():
            raise BusinessError(ErrorCode.USER_EXISTS)
        user.username = data["username"]
    if "email" in data and data["email"] != user.email:
        if User.query.filter_by(email=data["email"]).first():
            raise BusinessError(ErrorCode.EMAIL_EXISTS)
        user.email = data["email"]
    if "role" in data:
        user.role = data["role"]
    if "is_active" in data:
        user.is_active = data["is_active"]
    if "password" in data and data["password"]:
        user.password_hash = generate_password_hash(data["password"])

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
    )
    db.session.add(admin)
    db.session.commit()
    return admin
