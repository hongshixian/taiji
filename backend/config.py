"""应用配置 — 所有配置项从环境变量/.env 读取"""

import os
from dotenv import load_dotenv

# 自动搜索 .env 文件并加载
load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


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
            if cls.AUTH_MODE == "legacy" and cls.JWT_SECRET_KEY in cls._INSECURE_SECRETS:
                raise RuntimeError(
                    "生产环境禁止使用默认 JWT_SECRET_KEY，"
                    "请设置环境变量 JWT_SECRET_KEY 为随机强密钥"
                )
            if cls.AUTH_MODE == "oidc" and cls.OIDC_CLIENT_SECRET == "taiji-web-dev-secret":
                raise RuntimeError(
                    "生产环境禁止使用默认 TAIJI_OIDC_CLIENT_SECRET，请配置随机强密钥"
                )
            if cls.IAM_MIGRATOR_CLIENT_SECRET == "taiji-migrator-dev-secret":
                raise RuntimeError(
                    "生产环境禁止使用默认 TAIJI_MIGRATOR_CLIENT_SECRET，请配置随机强密钥"
                )
            if cls.IAM_RECONCILER_CLIENT_SECRET == "taiji-reconciler-dev-secret":
                raise RuntimeError(
                    "生产环境禁止使用默认 TAIJI_RECONCILER_CLIENT_SECRET，请配置随机强密钥"
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

    # IAM / OIDC BFF
    AUTH_MODE = os.getenv("AUTH_MODE", "legacy")
    IAM_REALM = os.getenv("IAM_REALM", "fangcun")
    IAM_PUBLIC_URL = os.getenv("IAM_PUBLIC_URL", "http://localhost:8180").rstrip("/")
    IAM_INTERNAL_URL = os.getenv("IAM_INTERNAL_URL", IAM_PUBLIC_URL).rstrip("/")
    OIDC_CLIENT_ID = os.getenv("TAIJI_OIDC_CLIENT_ID", "taiji-web")
    OIDC_CLIENT_SECRET = os.getenv("TAIJI_OIDC_CLIENT_SECRET", "taiji-web-dev-secret")
    IAM_MIGRATOR_CLIENT_ID = os.getenv("TAIJI_MIGRATOR_CLIENT_ID", "taiji-migrator")
    IAM_MIGRATOR_CLIENT_SECRET = os.getenv(
        "TAIJI_MIGRATOR_CLIENT_SECRET", "taiji-migrator-dev-secret"
    )
    IAM_RECONCILER_CLIENT_ID = os.getenv(
        "TAIJI_RECONCILER_CLIENT_ID", "taiji-reconciler"
    )
    IAM_RECONCILER_CLIENT_SECRET = os.getenv(
        "TAIJI_RECONCILER_CLIENT_SECRET", "taiji-reconciler-dev-secret"
    )
    NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
    IAM_EVENT_STREAM = os.getenv("IAM_EVENT_STREAM", "IAM_EVENTS")
    IAM_EVENT_SUBJECT = os.getenv("IAM_EVENT_SUBJECT", "iam.>")
    IAM_EVENT_CONSUMER = os.getenv("IAM_EVENT_CONSUMER", "taiji-projection-v1")
    IAM_EVENT_BATCH_SIZE = int(os.getenv("IAM_EVENT_BATCH_SIZE", "10"))
    IAM_EVENT_ACK_WAIT_SECONDS = int(os.getenv("IAM_EVENT_ACK_WAIT_SECONDS", "300"))
    IAM_RECONCILE_INTERVAL_SECONDS = int(
        os.getenv("IAM_RECONCILE_INTERVAL_SECONDS", "300")
    )
    READINESS_CHECK_EXTERNALS = _env_bool("READINESS_CHECK_EXTERNALS", True)
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    TAIJI_PUBLIC_URL = os.getenv("TAIJI_PUBLIC_URL", "http://localhost:8080").rstrip("/")
    OIDC_POST_LOGIN_PATH = os.getenv("OIDC_POST_LOGIN_PATH", "/")
    IAM_IDENTITY_CACHE_SECONDS = int(os.getenv("IAM_IDENTITY_CACHE_SECONDS", "300"))

    # Redis server-side browser session
    SESSION_TYPE = "redis"
    SESSION_KEY_PREFIX = os.getenv("SESSION_KEY_PREFIX", "taiji:session:")
    SESSION_ID_LENGTH = 32
    SESSION_SERIALIZATION_FORMAT = "json"
    SESSION_PERMANENT = True
    SESSION_REFRESH_EACH_REQUEST = True
    SESSION_IDLE_SECONDS = int(os.getenv("SESSION_IDLE_SECONDS", "7200"))
    SESSION_ABSOLUTE_SECONDS = int(os.getenv("SESSION_ABSOLUTE_SECONDS", "86400"))
    SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "taiji_session")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", FLASK_ENV == "production")
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_PATH = "/"

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
    FLASK_ENV = "testing"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    CELERY_TASK_ALWAYS_EAGER = True
    TASK_LOG_ROOT = os.getenv("TASK_LOG_ROOT", "/tmp/taiji_test_logs")
    AUTH_MODE = "legacy"
    READINESS_CHECK_EXTERNALS = False
