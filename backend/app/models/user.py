"""用户模型"""

from datetime import datetime, timezone
from app import db


class User(db.Model):
    """太极平台用户"""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default="user", nullable=False)        # 兼容字段；权威字段是 role_id
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=True, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # 早于此时间签发的 JWT 全部失效（改密 / 禁用 / 改角色时设置）
    tokens_revoked_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # 关联分析任务
    analyze_tasks = db.relationship("AnalyzeTask", backref="user", lazy="dynamic")

    # 关联角色（RBAC）
    role_obj = db.relationship("Role", lazy="joined", foreign_keys=[role_id])

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def permissions(self) -> list[str]:
        """当前用户拥有的权限码列表（从角色派生）"""
        if self.role_obj:
            return self.role_obj.permission_codes
        # 兼容：role_id 还没填的旧数据，按 role 字符串映射到系统角色权限
        from app.permissions import SYSTEM_ROLES
        return list(SYSTEM_ROLES.get(self.role, set()))

    def __repr__(self):
        return f"<User {self.username} role={self.role} role_id={self.role_id}>"
