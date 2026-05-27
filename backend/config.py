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

    # 接口限流 (flask-limiter)
    # 默认使用内存存储，生产环境建议配置 RATELIMIT_STORAGE_URL
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "100 per minute;20 per second")
    RATELIMIT_STORAGE_URL = os.getenv("RATELIMIT_STORAGE_URL", "memory://")
    RATELIMIT_STRATEGY = os.getenv("RATELIMIT_STRATEGY", "fixed-window")


class TestConfig(Config):
    """测试配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    CELERY_TASK_ALWAYS_EAGER = True