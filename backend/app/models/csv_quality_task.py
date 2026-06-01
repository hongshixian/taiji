"""CSV 数据质量检查任务详情模型"""

from app import db
from app.models._tenant_mixin import TenantMixin


class CsvQualityTask(db.Model, TenantMixin):
    """CSV 数据质量检查任务详情（多租户）"""

    __tablename__ = "csv_quality_tasks"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(
        db.Integer,
        db.ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    task_name = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(255))
    input_text = db.Column(db.Text, nullable=False)
    content_sample = db.Column(db.Text)
    result = db.Column(db.JSON)

    task = db.relationship("Task", back_populates="csv_quality")

    def __repr__(self):
        return f"<CsvQualityTask {self.task_id}@tenant={self.tenant_id}>"
