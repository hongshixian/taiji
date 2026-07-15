"""租户成员身份模型"""

from datetime import datetime, timezone
from sqlalchemy import UniqueConstraint

from app import db
from app.models._tenant_mixin import TenantMixin


class TenantMembership(db.Model, TenantMixin):
    """用户在某个租户下的身份、角色与启用状态。"""

    __tablename__ = "tenant_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "tenant_id", name="uq_membership_user_tenant"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_owner = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", back_populates="memberships", lazy="joined")
    tenant = db.relationship("Tenant", lazy="joined", foreign_keys="TenantMembership.tenant_id")
    role = db.relationship("Role", lazy="joined", foreign_keys=[role_id])

    @property
    def permission_codes(self) -> list[str]:
        return self.role.permission_codes if self.role else []

    def __repr__(self):
        role_name = self.role.name if self.role else self.role_id
        return f"<TenantMembership user={self.user_id} tenant={self.tenant_id} role={role_name}>"
