"""通用任务模型"""

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


class TaskType:
    """系统内置任务类型"""

    BENCHMARK = "benchmark"
    RED_TEAM = "red_team"


# 由 TaskRegistry.register() 在 handler 加载时动态填充；
# 此处保留空 dict，不在模型层硬编码任务类型名称。
TASK_TYPE_NAMES: dict = {}


class Task(db.Model, TenantMixin):
    """任务生命周期总表（多租户）"""

    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    task_type = db.Column(db.String(80), nullable=False, index=True)
    status = db.Column(
        db.String(20),
        default=TaskStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    error_message = db.Column(db.Text)
    log_path = db.Column(db.String(500))
    progress = db.Column(db.JSON)  # {completed, total, current_metrics}

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    benchmark = db.relationship(
        "BenchmarkTask",
        back_populates="task",
        uselist=False,
        cascade="all, delete-orphan",
    )
    red_team = db.relationship(
        "RedTeamTask",
        back_populates="task",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @property
    def task_type_name(self) -> str:
        return TASK_TYPE_NAMES.get(self.task_type, self.task_type)

    def __repr__(self):
        return f"<Task {self.id}@tenant={self.tenant_id} {self.task_type} [{self.status}]>"
