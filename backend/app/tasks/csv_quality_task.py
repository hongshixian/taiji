"""CSV 数据质量检查 Celery 任务"""

from celery_app import celery
from app import db
from app.services.csv_quality_service import execute_csv_quality_check
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery.task(bind=True, max_retries=0)
def check_csv_quality(self, task_id: int, tenant_id: int | None = None):
    """检查 CSV 数据质量"""

    logger.info(f"Celery CSV 检查任务启动: task_id={task_id} tenant_id={tenant_id}")

    try:
        with celery.flask_app.app_context():
            from app.utils.decorators import bypass_tenant_filter
            with bypass_tenant_filter():
                execute_csv_quality_check(task_id)
            db.session.remove()
    except Exception:
        logger.exception(f"Celery CSV 检查任务 {task_id} 致命异常")
        return {"task_id": task_id, "status": "error"}

    return {"task_id": task_id, "status": "completed"}
