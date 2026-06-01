"""网页内容分析任务详情模型"""

from app import db
from app.models._tenant_mixin import TenantMixin


class WebpageAnalysisTask(db.Model, TenantMixin):
    """网页内容分析任务详情（多租户）"""

    __tablename__ = "webpage_analysis_tasks"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(
        db.Integer,
        db.ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    url = db.Column(db.String(2048), nullable=False)
    title = db.Column(db.String(512))
    summary = db.Column(db.Text)
    keywords = db.Column(db.JSON)

    task = db.relationship("Task", back_populates="webpage_analysis")

    def __repr__(self):
        return f"<WebpageAnalysisTask {self.task_id}@tenant={self.tenant_id} {self.url[:50]}>"
