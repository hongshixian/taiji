"""Benchmark suite 启用状态 + 可访问性检测结果（多租户）

每个租户对每个 inspect_evals suite 可有一行覆盖：
  * enabled 为 None 时继承 suites.yaml 的默认（not disabled）；显式 True/False 覆盖之。
  * last_check_* 记录最近一次「数据集可访问性检测」的结果（用 mockllm 跑 limit=1）。
"""

from datetime import datetime, timezone

from app import db
from app.models._tenant_mixin import TenantMixin


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BenchmarkSuiteState(db.Model, TenantMixin):
    """租户对某个 benchmark suite 的启用覆盖与检测状态"""

    __tablename__ = "benchmark_suite_states"

    id = db.Column(db.Integer, primary_key=True)
    suite_key = db.Column(db.String(100), nullable=False, index=True)
    # None => 继承 yaml 默认（not suite.disabled）；True/False => 显式覆盖
    enabled = db.Column(db.Boolean, nullable=True)
    # unknown / pending / ok / failed
    last_check_status = db.Column(db.String(20), nullable=False, default="unknown")
    last_check_error = db.Column(db.Text)
    last_check_at = db.Column(db.DateTime)
    last_check_ms = db.Column(db.Integer)
    # 数据集样本总数（检测时从 eval log 的 dataset.samples 拿到；None=未知）
    sample_count = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        db.UniqueConstraint("tenant_id", "suite_key", name="uq_suite_state_tenant_key"),
    )

    def __repr__(self):
        return f"<BenchmarkSuiteState {self.suite_key!r} tenant={self.tenant_id} enabled={self.enabled}>"
