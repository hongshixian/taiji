"""Benchmark 测评任务详情模型"""

from app import db
from app.models._tenant_mixin import TenantMixin


class BenchmarkTask(db.Model, TenantMixin):
    """Benchmark 测评任务详情（多租户）

    与新的引擎抽象对齐：
      * 被测/评委模型统一走 model_configs 引用（ForeignKey）
      * engine 字段记录本次任务使用的评测引擎（默认 inspect_evals，未来可扩展）
      * benchmark_config：用户提交时的原始参数快照（execution_config + suite_config）
      * result：BenchmarkResult 的序列化结果
      * notes：任务备注
    """

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
    notes = db.Column(db.String(500))

    # ── 引擎与 suite ─────────────────────────────────────────────────────
    engine = db.Column(db.String(50), nullable=False, default="inspect_evals")
    benchmark_suite = db.Column(db.String(100), nullable=False)

    # ── 模型引用（FK 到 model_configs） ──────────────────────────────────
    target_model_id = db.Column(
        db.Integer,
        db.ForeignKey("model_configs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    judge_model_id = db.Column(
        db.Integer,
        db.ForeignKey("model_configs.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    # ── 用户提交的参数快照（引擎无关格式） ──────────────────────────────
    benchmark_config = db.Column(db.JSON)   # {execution_config, suite_config}
    result = db.Column(db.JSON)              # BenchmarkResult.to_dict()

    task = db.relationship("Task", back_populates="benchmark")
    target_model = db.relationship("ModelConfig", foreign_keys=[target_model_id])
    judge_model = db.relationship("ModelConfig", foreign_keys=[judge_model_id])

    def __repr__(self):
        return f"<BenchmarkTask {self.task_id}@tenant={self.tenant_id} suite={self.benchmark_suite}>"
