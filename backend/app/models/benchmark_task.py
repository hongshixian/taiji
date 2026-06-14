"""Benchmark 测评任务详情模型"""

from app import db
from app.models._tenant_mixin import TenantMixin


class BenchmarkTask(db.Model, TenantMixin):
    """Benchmark 测评任务详情（多租户）"""

    __tablename__ = "benchmark_tasks"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(
        db.Integer,
        db.ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    task_name = db.Column(db.String(100), nullable=False)
    model_name = db.Column(db.String(200), nullable=False)
    model_endpoint = db.Column(db.String(500))
    model_api_key = db.Column(db.String(500))
    benchmark_suite = db.Column(db.String(100), nullable=False)
    benchmark_config = db.Column(db.JSON)
    result = db.Column(db.JSON)

    task = db.relationship("Task", back_populates="benchmark")

    def __repr__(self):
        return f"<BenchmarkTask {self.task_id}@tenant={self.tenant_id}>"
