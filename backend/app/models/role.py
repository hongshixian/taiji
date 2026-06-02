"""角色 & 权限模型 (RBAC)"""

from datetime import datetime, timezone
from app import db


# 角色-权限 多对多关联表
role_permissions = db.Table(
    "role_permissions",
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"),
              primary_key=True),
    db.Column("permission_code", db.String(64),
              db.ForeignKey("permissions.code", ondelete="CASCADE"),
              primary_key=True),
)


class Permission(db.Model):
    """系统权限（启动时 seed，不允许运行时增删；admin 只能在角色级别分配）"""

    __tablename__ = "permissions"

    code = db.Column(db.String(64), primary_key=True)
    description = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f"<Permission {self.code}>"


class Role(db.Model):
    """角色 — 系统角色 (is_system=true) 由代码定义，自定义角色由 admin 在运行时创建"""

    __tablename__ = "roles"
    __table_args__ = (
        db.UniqueConstraint("tenant_id", "name", name="uq_roles_tenant_name"),
        db.Index("uq_roles_system_name", "name", unique=True,
                 sqlite_where=db.text("tenant_id IS NULL"),
                 postgresql_where=db.text("tenant_id IS NULL")),
    )

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=True, index=True)
    name = db.Column(db.String(50), nullable=False, index=True)
    description = db.Column(db.String(200))
    is_system = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # 多对多：一个角色绑定多个权限码
    permissions = db.relationship("Permission", secondary=role_permissions,
                                  lazy="joined", backref="roles")
    tenant = db.relationship("Tenant", lazy="joined", foreign_keys=[tenant_id])

    @property
    def permission_codes(self) -> list[str]:
        return [p.code for p in self.permissions]

    def __repr__(self):
        scope = "system" if self.tenant_id is None else f"tenant={self.tenant_id}"
        return f"<Role {self.name} ({scope}, system={self.is_system})>"
