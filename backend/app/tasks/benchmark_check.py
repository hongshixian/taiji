"""Benchmark 数据集可访问性检测 Celery 任务

独立任务（不进 tasks 表）：跑 mockllm limit=1，把结果写回 benchmark_suite_states。
worker 无请求上下文，故 tenant_id 显式传入，state 读写手动按 tenant_id 过滤。
"""

from __future__ import annotations

from celery_app import celery
from app import db
from app.utils.decorators import bypass_tenant_filter
from app.utils.logger import get_logger


log = get_logger("tasks.benchmark_check")


@celery.task(bind=True, max_retries=0, name="tasks.benchmark_check")
def benchmark_check_task(self, tenant_id: int, suite_key: str):
    log.info(f"可达性检测启动: tenant={tenant_id} suite={suite_key}")
    from app.services.benchmark_check_service import run_accessibility_check
    from app.services.benchmark_state_service import record_check_result

    try:
        with celery.flask_app.app_context():
            with bypass_tenant_filter():
                try:
                    ok, error, ms = run_accessibility_check(suite_key)
                    record_check_result(tenant_id, suite_key, ok, error, ms)
                except Exception as exc:  # noqa: BLE001
                    log.exception(f"可达性检测异常 suite={suite_key}")
                    record_check_result(tenant_id, suite_key, False, f"{type(exc).__name__}: {exc}"[:800], 0)
            db.session.remove()
    except Exception:  # noqa: BLE001
        log.exception(f"可达性检测任务致命异常 suite={suite_key}")
        return {"suite_key": suite_key, "status": "error"}
    return {"suite_key": suite_key, "status": "completed"}
