"""自动红队测评任务详情模型"""

from app import db
from app.models._tenant_mixin import TenantMixin


class RedTeamTask(db.Model, TenantMixin):
    """自动红队测评任务详情（多租户）"""

    __tablename__ = "red_team_tasks"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(
        db.Integer,
        db.ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    task_name = db.Column(db.String(100), nullable=False)
    target_model_name = db.Column(db.String(200), nullable=False)
    target_model_endpoint = db.Column(db.String(500))
    target_model_api_key = db.Column(db.String(500))
    attack_method = db.Column(db.String(100), nullable=False)
    attack_config = db.Column(db.JSON)
    result = db.Column(db.JSON)

    task = db.relationship("Task", back_populates="red_team")

    def __repr__(self):
        return f"<RedTeamTask {self.task_id}@tenant={self.tenant_id}>"
