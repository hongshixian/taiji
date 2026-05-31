"""Flask 应用工厂"""

from flask import Flask, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config
from app.utils.errors import register_error_handlers, ErrorCode, _err_response

# 扩展实例（先创建，后续 init_app）
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],  # 不用全局默认限制，由各路由自行声明
)

# API 版本前缀 —— 所有业务蓝图都挂在 /api/v1/ 之下
# /api/health 等基础设施端点保持原地（跨版本稳定）
API_V1 = "/api/v1"


def create_app(config_obj=Config):
    """创建 Flask 应用（工厂模式）

    Args:
        config_obj: 配置类，默认使用 Config

    Returns:
        Flask: 应用实例
    """
    # 先导入模型，确保 SQLAlchemy 能发现它们
    import app.models  # noqa: F401

    flask_app = Flask(__name__)
    flask_app.config.from_object(config_obj)

    # 初始化扩展
    db.init_app(flask_app)
    migrate.init_app(flask_app, db)
    jwt.init_app(flask_app)
    limiter.init_app(flask_app)
    CORS(flask_app, supports_credentials=True)

    # 初始化 Celery
    from celery_app import init_celery
    init_celery(flask_app)

    # 注册错误处理器
    register_error_handlers(flask_app)

    # ── 限流超出处理器 ──────────────────────────────────────
    @flask_app.errorhandler(429)
    def ratelimit_error(e):
        # e.description 由 flask-limiter 给出 (如 "5 per 1 minute")
        return _err_response(
            ErrorCode.RATE_LIMITED,
            f"请求过于频繁，请稍后再试（限制：{e.description}）",
        )

    # 健康检查路由（不需要鉴权；跨 API 版本稳定，不放在 /api/v1/ 下）
    @flask_app.route("/api/health")
    def health():
        return jsonify({"status": "ok"})

    # 注册业务蓝图（统一挂在 /api/v1/ 之下）
    from app.api.auth import auth_bp
    from app.api.analyze import analyze_bp
    from app.api.admin import admin_bp

    flask_app.register_blueprint(auth_bp, url_prefix=f"{API_V1}/auth")
    flask_app.register_blueprint(analyze_bp, url_prefix=f"{API_V1}/analyze")
    flask_app.register_blueprint(admin_bp, url_prefix=f"{API_V1}/admin")

    # 注册 JWT 错误处理器（使用业务错误码）
    @jwt.expired_token_loader
    def expired_token_callback(_jwt_header, _jwt_payload):
        return _err_response(ErrorCode.TOKEN_EXPIRED)

    @jwt.invalid_token_loader
    def invalid_token_callback(_reason):
        return _err_response(ErrorCode.TOKEN_INVALID)

    @jwt.unauthorized_loader
    def missing_token_callback(_reason):
        return _err_response(ErrorCode.TOKEN_MISSING)

    return flask_app
