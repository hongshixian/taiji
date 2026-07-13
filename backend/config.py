"""应用配置 — 所有配置项从环境变量/.env 读取"""

import os
from dotenv import load_dotenv

# 自动搜索 .env 文件并加载
load_dotenv()


class Config:
    """基础配置"""

    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")

    # 生产环境启动校验：拒绝使用默认开发密钥
    _INSECURE_SECRETS = {"dev-secret-change-me", "change-me-in-production"}

    @classmethod
    def _check_secrets(cls):
        """生产环境下拒绝使用不安全的默认密钥"""
        if cls.FLASK_ENV == "production":
            if cls.SECRET_KEY in cls._INSECURE_SECRETS:
                raise RuntimeError(
                    "生产环境禁止使用默认 SECRET_KEY，"
                    "请设置环境变量 SECRET_KEY 为随机强密钥"
                )
            if cls.JWT_SECRET_KEY in cls._INSECURE_SECRETS:
                raise RuntimeError(
                    "生产环境禁止使用默认 JWT_SECRET_KEY，"
                    "请设置环境变量 JWT_SECRET_KEY 为随机强密钥"
                )

    # 数据库 (默认 SQLite, 生产用 PostgreSQL)
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///data/taiji.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis / Celery
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    CELERY_ACCEPT_CONTENT = ["json"]
    CELERY_TASK_SERIALIZER = "json"
    CELERY_RESULT_SERIALIZER = "json"

    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-dev-secret-change-me-32bytes!")
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "1800"))   # 30 分钟
    JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", "604800"))  # 7 天

    # CORS — 允许的来源列表，逗号分隔；留空则仅允许同源请求
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "")  # e.g. "http://localhost:5173,https://taiji.example.com"

    # 接口限流 (flask-limiter)
    # 默认使用内存存储，生产环境建议配置 RATELIMIT_STORAGE_URL
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "100 per minute;20 per second")
    RATELIMIT_STORAGE_URL = os.getenv("RATELIMIT_STORAGE_URL", "memory://")
    RATELIMIT_STRATEGY = os.getenv("RATELIMIT_STRATEGY", "fixed-window")

    # 任务日志根目录。Docker Compose 使用 /app/logs，本地开发默认写到项目根目录 app_logs。
    TASK_LOG_ROOT = os.getenv("TASK_LOG_ROOT", "../app_logs")

    # Benchmark 引擎产物（.eval log）目录；不配置则落到 TASK_LOG_ROOT/benchmark_artifacts
    BENCHMARK_ARTIFACT_ROOT = os.getenv("BENCHMARK_ARTIFACT_ROOT") or None

    # HuggingFace 数据集缓存目录（同一份 HF_HOME 供数据集下载复用）
    HF_CACHE_ROOT = os.getenv("HF_HOME") or os.getenv("HF_CACHE_ROOT") or None


class TestConfig(Config):
    """测试配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    CELERY_TASK_ALWAYS_EAGER = True
    TASK_LOG_ROOT = os.getenv("TASK_LOG_ROOT", "/tmp/taiji_test_logs")
