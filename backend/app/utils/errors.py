"""业务错误码体系 + 全局异常处理

设计原则：
- 业务错误码与 HTTP 状态码解耦 —— code 字段反映业务语义，HTTP 状态码反映传输语义
- 分段：1xxxx 用户/认证、2xxxx 任务、3xxxx 鉴权、9xxxx 系统级
- handler 内只 `raise BusinessError(ErrorCode.XXX)`，由全局 errorhandler 统一序列化
"""

from dataclasses import dataclass
from flask import jsonify


@dataclass(frozen=True)
class ErrCode:
    """错误码条目"""
    code: int
    message: str
    http: int = 400  # 默认 HTTP 状态码


class ErrorCode:
    """业务错误码表"""

    # ── 用户 / 认证 ────────────────────────────
    USER_EXISTS = ErrCode(10001, "用户名已存在")
    EMAIL_EXISTS = ErrCode(10002, "邮箱已注册")
    INVALID_CREDENTIAL = ErrCode(10003, "用户名或密码错误", http=401)
    ACCOUNT_DISABLED = ErrCode(10004, "账户已被禁用", http=401)
    USER_NOT_FOUND = ErrCode(10005, "用户不存在", http=404)
    CANNOT_DELETE_SELF = ErrCode(10006, "不能删除自己")
    INVALID_ROLE = ErrCode(10007, "无效的角色")
    ROLE_NOT_FOUND = ErrCode(10008, "角色不存在", http=404)
    ROLE_EXISTS = ErrCode(10009, "角色名已存在")
    SYSTEM_ROLE_PROTECTED = ErrCode(10010, "系统角色受保护，不可修改")
    ROLE_IN_USE = ErrCode(10011, "角色仍在使用中，不可删除")

    # ── 多租户 ───────────────────────────────
    TENANT_NOT_FOUND = ErrCode(11001, "租户不存在", http=404)
    TENANT_EXISTS = ErrCode(11002, "租户 slug 已存在")
    SYSTEM_TENANT_PROTECTED = ErrCode(11003, "系统租户受保护，不可修改")
    TENANT_IN_USE = ErrCode(11004, "租户仍在使用中，不可删除")

    # ── 任务模块 ──────────────────────────────
    TASK_NOT_FOUND = ErrCode(20001, "任务不存在", http=404)
    INVALID_URL = ErrCode(20002, "URL 格式错误")

    # ── 鉴权 ──────────────────────────────────
    TOKEN_EXPIRED = ErrCode(30001, "Token 已过期", http=401)
    TOKEN_INVALID = ErrCode(30002, "Token 无效", http=401)
    TOKEN_MISSING = ErrCode(30003, "缺少认证 Token", http=401)
    PERMISSION_DENIED = ErrCode(30004, "需要管理员权限", http=403)
    AUTH_DISABLED = ErrCode(30005, "账户已禁用", http=403)
    TOKEN_REVOKED = ErrCode(30006, "Token 已撤销，请重新登录", http=401)

    # ── 系统级 ────────────────────────────────
    VALIDATION_ERROR = ErrCode(90001, "请求参数错误")
    EMPTY_BODY = ErrCode(90002, "请求体不能为空")
    RATE_LIMITED = ErrCode(90003, "请求过于频繁", http=429)
    NOT_FOUND = ErrCode(90404, "资源不存在", http=404)
    METHOD_NOT_ALLOWED = ErrCode(90405, "请求方法不允许", http=405)
    INTERNAL_ERROR = ErrCode(90500, "服务器内部错误", http=500)


class BusinessError(Exception):
    """业务异常 — 由全局 errorhandler 转换为统一响应

    用法:
        raise BusinessError(ErrorCode.USER_EXISTS)
        raise BusinessError(ErrorCode.TASK_NOT_FOUND, "任务 #123 已被删除")  # 自定义 message
    """

    def __init__(self, err: ErrCode, message: str | None = None):
        self.err = err
        self.message = message or err.message
        super().__init__(self.message)


def _err_response(err: ErrCode, message: str | None = None):
    """构造统一错误响应"""
    return jsonify({
        "code": err.code,
        "message": message or err.message,
    }), err.http


def register_error_handlers(app):
    """注册全局错误处理器"""

    @app.errorhandler(BusinessError)
    def handle_business(e: BusinessError):
        return _err_response(e.err, e.message)

    @app.errorhandler(404)
    def not_found(_e):
        return _err_response(ErrorCode.NOT_FOUND)

    @app.errorhandler(405)
    def method_not_allowed(_e):
        return _err_response(ErrorCode.METHOD_NOT_ALLOWED)

    @app.errorhandler(500)
    def internal_error(_e):
        app.logger.exception("服务器内部错误")
        return _err_response(ErrorCode.INTERNAL_ERROR)
