"""认证业务逻辑"""

from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token

from app import db
from app.models.user import User


def register_user(username: str, email: str, password: str) -> User:
    """注册新用户

    Args:
        username: 用户名
        email: 邮箱
        password: 明文密码

    Returns:
        User: 新创建的用户对象

    Raises:
        ValueError: 用户名或邮箱已存在
    """
    # 检查唯一性
    if User.query.filter_by(username=username).first():
        raise ValueError("用户名已存在")
    if User.query.filter_by(email=email).first():
        raise ValueError("邮箱已注册")

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
    )
    db.session.add(user)
    db.session.commit()
    return user


def login_user(username: str, password: str) -> dict:
    """用户登录，返回 JWT token

    Args:
        username: 用户名
        password: 明文密码

    Returns:
        dict: {"access_token": ..., "refresh_token": ..., "user": {...}}

    Raises:
        ValueError: 用户名或密码错误
    """
    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        raise ValueError("用户名或密码错误")

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user_to_dict(user),
    }


def get_user_by_id(user_id: int) -> User | None:
    """根据 ID 查询用户"""
    return db.session.get(User, user_id)


def user_to_dict(user: User) -> dict:
    """将 User 对象转为字典（避免泄露密码哈希）"""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
    }