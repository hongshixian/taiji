"""Celery 异步任务 — 网页内容分析"""

from celery_app import celery
from app import db
from app.services.analyze_service import execute_analysis
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery.task(bind=True, max_retries=0)
def analyze_webpage(self, task_id: int):
    """分析网页内容

    Args:
        task_id: AnalyzeTask 的 ID

    Returns:
        dict: {"task_id": int, "status": str}
    """
    logger.info(f"Celery 任务启动: task_id={task_id}")

    try:
        with celery.flask_app.app_context():
            execute_analysis(task_id)
            db.session.remove()
    except Exception as e:
        logger.exception(f"Celery 任务 {task_id} 致命异常")
        # 任务层面的异常已在 execute_analysis 内处理
        return {"task_id": task_id, "status": "error"}

    return {"task_id": task_id, "status": "completed"}