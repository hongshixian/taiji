"""租户模型 — 多租户共享 schema 的核心实体"""

from datetime import datetime, timezone
from app import db


class Tenant(db.Model):
    """租户（组织 / 工作空间）

    所有业务表都关联 tenant_id（通过 TenantMixin），同一 tenant 内的数据相互可见，
    不同 tenant 间默认完全隔离。系统种子租户 (is_system=true) 不允许删除。
    """

    __tablename__ = "tenants"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    plan = db.Column(db.String(20), default="free", nullable=False)       # free / pro / enterprise
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_system = db.Column(db.Boolean, default=False, nullable=False)      # default/guest 等系统租户保护位
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Tenant {self.slug} ({self.name})>"


# 系统种子租户 slug 常量
DEFAULT_TENANT_SLUG = "default"   # 现有 admin 数据归这里
GUEST_TENANT_SLUG = "guest"       # 新注册用户默认归这里
