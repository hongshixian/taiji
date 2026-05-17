"""Celery 实例 — 预留结构，Phase 4 补全"""

from celery import Celery


def create_celery_app(app=None):
    """创建 Celery 应用

    Args:
        app: Flask 应用实例（可选，Worker 启动时传入）

    Returns:
        Celery: Celery 应用实例
    """
    celery = Celery(
        __name__,
        broker=None,  # Phase 4 从 config 读取
        backend=None,
    )

    if app:
        celery.conf.update(app.config)

    # Phase 4 将追加: celery.conf.broker_url, result_backend 等配置

    return celery