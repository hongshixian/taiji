"""Flask 应用工厂"""

from flask import Flask, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager

from config import Config
from app.utils.errors import register_error_handlers

# 扩展实例（先创建，后续 init_app）
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


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
    CORS(flask_app, supports_credentials=True)

    # 注册错误处理器
    register_error_handlers(flask_app)

    # 健康检查路由（不需要鉴权）
    @flask_app.route("/api/health")
    def health():
        return jsonify({"status": "ok"})

    # 注册蓝图
    from app.api.auth import auth_bp
    from app.api.analyze import analyze_bp

    flask_app.register_blueprint(auth_bp, url_prefix="/api/auth")
    flask_app.register_blueprint(analyze_bp, url_prefix="/api/analyze")

    # 注册 JWT 错误处理器
    @jwt.expired_token_loader
    def expired_token_callback(_jwt_header, _jwt_payload):
        return jsonify({"code": 401, "message": "Token 已过期"}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(_reason):
        return jsonify({"code": 401, "message": "Token 无效"}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(_reason):
        return jsonify({"code": 401, "message": "缺少认证 Token"}), 401

    return flask_app