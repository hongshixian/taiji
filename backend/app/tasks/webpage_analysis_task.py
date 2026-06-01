"""网页内容分析 Celery 任务"""

from celery_app import celery
from app import db
from app.services.webpage_analysis_service import execute_webpage_analysis
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery.task(bind=True, max_retries=0)
def analyze_webpage(self, task_id: int, tenant_id: int | None = None):
    """分析网页内容"""

    logger.info(f"Celery 网页分析任务启动: task_id={task_id} tenant_id={tenant_id}")

    try:
        with celery.flask_app.app_context():
            from app.utils.decorators import bypass_tenant_filter
            with bypass_tenant_filter():
                execute_webpage_analysis(task_id)
            db.session.remove()
    except Exception:
        logger.exception(f"Celery 网页分析任务 {task_id} 致命异常")
        return {"task_id": task_id, "status": "error"}

    return {"task_id": task_id, "status": "completed"}
