"""审计日志模型"""

from datetime import datetime, timezone

from app import db


class AuditLog(db.Model):
    """平台管理行为记录。

    不继承 TenantMixin：审计日志需要支持平台级记录和超级管理员跨租户查询。
    tenant_id / actor_user_id 不使用外键，避免用户或租户删除后破坏历史事实记录。
    """

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=True, index=True)
    actor_user_id = db.Column(db.Integer, nullable=True, index=True)
    actor_username = db.Column(db.String(80), nullable=True)
    actor_is_superuser = db.Column(db.Boolean, default=False, nullable=False)
    action = db.Column(db.String(80), nullable=False, index=True)
    resource_type = db.Column(db.String(80), nullable=False, index=True)
    resource_id = db.Column(db.String(100), nullable=True, index=True)
    resource_name = db.Column(db.String(200), nullable=True)
    result = db.Column(db.String(20), nullable=False, default="success", index=True)
    before_data = db.Column(db.JSON, nullable=True)
    after_data = db.Column(db.JSON, nullable=True)
    metadata_data = db.Column("metadata", db.JSON, nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(512), nullable=True)
    request_id = db.Column(db.String(100), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           nullable=False, index=True)

    def __repr__(self):
        return f"<AuditLog {self.action} {self.resource_type}:{self.resource_id}>"
