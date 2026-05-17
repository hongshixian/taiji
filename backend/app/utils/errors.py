"""统一错误响应"""

from flask import jsonify


def error_response(code: int, message: str, status_code: int = 400):
    """统一错误响应格式

    Args:
        code: 业务错误码
        message: 错误描述
        status_code: HTTP 状态码
    """
    response = jsonify({"code": code, "message": message})
    response.status_code = status_code
    return response


def register_error_handlers(app):
    """注册全局错误处理器"""

    @app.errorhandler(400)
    def bad_request(e):
        return error_response(400, "请求参数错误", 400)

    @app.errorhandler(404)
    def not_found(e):
        return error_response(404, "资源不存在", 404)

    @app.errorhandler(405)
    def method_not_allowed(e):
        return error_response(405, "请求方法不允许", 405)

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(f"服务器内部错误: {e}")
        return error_response(500, "服务器内部错误", 500)