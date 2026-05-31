"""Celery 异步任务 — 网页内容分析"""

from celery_app import celery
from app import db
from app.services.analyze_service import execute_analysis
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery.task(bind=True, max_retries=0)
def analyze_webpage(self, task_id: int, tenant_id: int | None = None):
    """分析网页内容

    Args:
        task_id: AnalyzeTask 的 ID
        tenant_id: 任务所属租户 ID（用于在 worker 进程内恢复 tenant 上下文）

    Returns:
        dict: {"task_id": int, "status": str}
    """
    logger.info(f"Celery 任务启动: task_id={task_id} tenant_id={tenant_id}")

    try:
        with celery.flask_app.app_context():
            # worker 不在 request 上下文里，但 has_request_context() = False 时
            # event hook 会自动跳过 filter。这里仍然手动用 bypass 工具，
            # 防止以后改了 hook 行为后跨租户泄漏。
            from app.utils.decorators import bypass_tenant_filter
            with bypass_tenant_filter():
                execute_analysis(task_id)
            db.session.remove()
    except Exception as e:
        logger.exception(f"Celery 任务 {task_id} 致命异常")
        return {"task_id": task_id, "status": "error"}

    return {"task_id": task_id, "status": "completed"}
