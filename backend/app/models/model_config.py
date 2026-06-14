"""模型配置模型（多租户）"""

from datetime import datetime, timezone

from app import db
from app.models._tenant_mixin import TenantMixin


class ModelConfig(db.Model, TenantMixin):
    """被测模型配置，租户隔离"""

    __tablename__ = "model_configs"

    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(100), nullable=False)  # 榜单显示名
    model_name = db.Column(db.String(200), nullable=False)     # API 请求时的模型名
    api_base_url = db.Column(db.String(500), nullable=False)   # API Base URL
    api_protocol = db.Column(db.String(50), nullable=False, default="openai")  # openai / anthropic / custom
    api_key = db.Column(db.String(500))                        # API Key（可选，存密文）
    description = db.Column(db.String(500))                    # 备注
    extra_params = db.Column(db.JSON)                          # 其他自定义参数
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self):
        return f"<ModelConfig {self.display_name!r} tenant={self.tenant_id}>"
