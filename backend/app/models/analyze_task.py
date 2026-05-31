"""分析任务模型"""

import enum
from datetime import datetime, timezone
from app import db
from app.models._tenant_mixin import TenantMixin


class TaskStatus(str, enum.Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class AnalyzeTask(db.Model, TenantMixin):
    """网页分析任务记录（多租户）"""

    __tablename__ = "analyze_tasks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    url = db.Column(db.String(2048), nullable=False)
    status = db.Column(db.String(20), default=TaskStatus.PENDING.value, nullable=False, index=True)

    # 分析结果
    title = db.Column(db.String(512))
    summary = db.Column(db.Text)
    keywords = db.Column(db.JSON)  # ["关键词1", "关键词2", ...]

    # 错误信息
    error_message = db.Column(db.Text)

    # 时间信息
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    def __repr__(self):
        return f"<AnalyzeTask {self.id}@tenant={self.tenant_id} [{self.status}] {self.url[:50]}>"
