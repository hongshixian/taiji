"""Flask 应用工厂"""

from flask import Flask, jsonify, g, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager, verify_jwt_in_request, get_jwt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def _get_client_ip():
    """限流 key 函数：优先读取反向代理传递的 X-Forwarded-For / X-Real-IP"""
    # X-Forwarded-For 格式: "client_ip, proxy1_ip, proxy2_ip"
    forwarded = request.headers.get("X-Forwarded-For", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP", "").strip()
    if real_ip:
        return real_ip
    return request.remote_addr or "127.0.0.1"

from config import Config
from app.utils.errors import register_error_handlers, ErrorCode, _err_response

# 扩展实例（先创建，后续 init_app）
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
limiter = Limiter(
    key_func=_get_client_ip,
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

    # 生产环境密钥安全校验
    if hasattr(config_obj, "_check_secrets"):
        config_obj._check_secrets()

    # 初始化扩展
    db.init_app(flask_app)
    migrate.init_app(flask_app, db)
    jwt.init_app(flask_app)
    limiter.init_app(flask_app)
    # CORS — 仅允许配置的来源；未配置时默认允许同源（安全回退）
    cors_origins = flask_app.config.get("CORS_ORIGINS", "")
    if cors_origins:
        allowed_origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
    else:
        # 开发环境回退：允许前端 dev server 来源
        allowed_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
    CORS(flask_app, origins=allowed_origins, supports_credentials=True)

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
    from app.api.task import task_bp
    from app.api.admin import admin_bp
    from app.api.superadmin import superadmin_bp
    from app.api.audit import audit_bp
    from app.api.model_config import model_config_bp

    # 初始化 auth 蓝图独立限流器（需要在注册蓝图前完成）
    from app.api.auth import auth_limiter
    auth_limiter.init_app(flask_app)

    flask_app.register_blueprint(auth_bp, url_prefix=f"{API_V1}/auth")
    flask_app.register_blueprint(task_bp, url_prefix=f"{API_V1}/tasks")
    flask_app.register_blueprint(admin_bp, url_prefix=f"{API_V1}/admin")
    flask_app.register_blueprint(superadmin_bp, url_prefix=f"{API_V1}/superadmin")
    flask_app.register_blueprint(audit_bp, url_prefix=f"{API_V1}/audit-logs")
    flask_app.register_blueprint(model_config_bp, url_prefix=f"{API_V1}/models")

    # 加载所有任务处理器并注册对应蓝图
    from app.handlers.registry import registry
    registry.discover()
    for handler in registry.all():
        flask_app.register_blueprint(
            handler.make_blueprint(),
            url_prefix=f"{API_V1}/tasks/{handler.url_prefix}",
        )

    # ─── 多租户：从 JWT 装 g.tenant_id 和 g.is_superuser ───
    @flask_app.before_request
    def _load_tenant_context():
        """所有请求统一从 JWT 读 tenant_id / is_superuser 存到 g

        无 JWT / JWT 无效的请求（如 register / login / health）会直接跳过，
        g.tenant_id 不会被设置，后续 query event hook 也不会自动 filter。
        """
        g.tenant_id = None
        g.is_superuser = False
        g.bypass_tenant_filter = False
        try:
            verify_jwt_in_request(optional=True)
            claims = get_jwt()
            if claims:
                g.tenant_id = claims.get("tenant_id")
                g.is_superuser = claims.get("is_superuser", False)
        except Exception:
            # JWT 错误由各 endpoint 的 @jwt_required 处理；这里只是尝试提取
            pass

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

    @jwt.revoked_token_loader
    def revoked_token_callback(_jwt_header, _jwt_payload):
        return _err_response(ErrorCode.TOKEN_REVOKED)

    # ─── JWT 吊销检查 ──────────────────────────────────
    # 同时检查 jti 黑名单（单 token 撤销）+ user.tokens_revoked_at（用户级全量撤销）
    @jwt.token_in_blocklist_loader
    def check_token_revoked(_jwt_header, jwt_payload):
        from datetime import datetime, timezone
        from app.utils.jwt_blocklist import is_jti_revoked
        from app.models.user import User

        # 1. jti 黑名单（登出场景）
        if is_jti_revoked(jwt_payload["jti"]):
            return True

        # 2. 用户级吊销：token 签发时间早于 user.tokens_revoked_at
        user_id = int(jwt_payload["sub"])
        user = db.session.get(User, user_id)
        if not user:
            return True  # 用户已删除，token 自动失效
        if not user.is_active:
            return True  # 账户已禁用
        if user.tokens_revoked_at:
            token_iat = datetime.fromtimestamp(jwt_payload["iat"], tz=timezone.utc)
            # SQLite 存的是 naive datetime，但语义上是 UTC；对齐时区再比较
            revoked_at = user.tokens_revoked_at
            if revoked_at.tzinfo is None:
                revoked_at = revoked_at.replace(tzinfo=timezone.utc)
            # 严格 < 比较：service 设置 revoked_at 时会向上取整到下一秒，
            # 保证"改密那一秒前签发的 token 全部失效，紧接着登录的不受影响"
            if token_iat < revoked_at:
                return True

        return False

    return flask_app
