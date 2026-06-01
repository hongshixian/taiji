"""用户模型"""

from datetime import datetime, timezone
from app import db


class User(db.Model):
    """太极平台用户（全局唯一登录主体）"""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # 平台超级管理员（可跨 tenant 操作；与 membership 身份解耦）
    is_superuser = db.Column(db.Boolean, default=False, nullable=False)

    # 早于此时间签发的 JWT 全部失效（改密 / 禁用 / 改角色时设置）
    tokens_revoked_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # 关联任务
    tasks = db.relationship("Task", backref="user", lazy="dynamic")

    # 用户在各租户的成员身份
    memberships = db.relationship(
        "TenantMembership",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def __repr__(self):
        return f"<User {self.username}>"
