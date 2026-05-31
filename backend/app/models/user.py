"""用户模型"""

from datetime import datetime, timezone
from sqlalchemy import UniqueConstraint
from app import db
from app.models._tenant_mixin import TenantMixin


class User(db.Model, TenantMixin):
    """太极平台用户（多租户：username/email 在 tenant 内唯一）"""

    __tablename__ = "users"
    # tenant 内唯一约束（取代原来的全局唯一）
    __table_args__ = (
        UniqueConstraint("tenant_id", "username", name="uq_users_tenant_username"),
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, index=True)
    email = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default="user", nullable=False)        # 兼容字段；权威字段是 role_id
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=True, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # 平台超级管理员（可跨 tenant 操作；与 tenant_id 解耦）
    is_superuser = db.Column(db.Boolean, default=False, nullable=False)

    # 早于此时间签发的 JWT 全部失效（改密 / 禁用 / 改角色时设置）
    tokens_revoked_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # 关联分析任务
    analyze_tasks = db.relationship("AnalyzeTask", backref="user", lazy="dynamic")

    # 关联角色（RBAC）
    role_obj = db.relationship("Role", lazy="joined", foreign_keys=[role_id])

    # 关联租户（Tenant 表无 TenantMixin，不会被全局过滤）
    tenant = db.relationship("Tenant", lazy="joined", foreign_keys="User.tenant_id")

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
        return f"<User {self.username}@tenant={self.tenant_id} role={self.role} role_id={self.role_id}>"
