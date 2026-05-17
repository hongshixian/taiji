"""Celery 应用"""

from celery import Celery

celery = Celery("taiji")


def init_celery(app):
    """用 Flask 配置初始化 Celery

    在 create_app() 中调用，确保 Celery 与 Flask 共享配置。
    在 Worker 启动时也通过 create_celery_app() 调用。

    Args:
        app: Flask 应用实例
    """
    # 直接用 app.config 配置 broker 和 backend
    celery.conf.update(
        broker_url=app.config["CELERY_BROKER_URL"],
        result_backend=app.config["CELERY_RESULT_BACKEND"],
        task_serializer=app.config["CELERY_TASK_SERIALIZER"],
        result_serializer=app.config["CELERY_RESULT_SERIALIZER"],
        accept_content=["json"],
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
    )

    # 绑定 Flask 应用，让 worker 能访问 app.app_context()
    celery.flask_app = app

    return celery


def create_celery_app():
    """Worker 独立启动时创建 Celery 应用

    用法: celery -A celery_app worker -l info
    """
    from app import create_app

    flask_app = create_app()
    return init_celery(flask_app)