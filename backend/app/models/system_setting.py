"""平台级系统设置模型"""

from datetime import datetime, timezone

from app import db


class SystemSetting(db.Model):
    """平台级 key/value 配置，不属于任何租户。"""

    __tablename__ = "system_settings"

    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.JSON, nullable=False)
    description = db.Column(db.String(200))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<SystemSetting {self.key}>"
