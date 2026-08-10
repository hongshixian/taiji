"""多租户隔离 — TenantMixin + 全局 SQLAlchemy 拦截器

⚠️ 重要：这是多租户安全的核心防线

任何继承 TenantMixin 的模型，所有 query 会自动 filter by g.tenant_id。
意味着：
  User.query.filter_by(username="x").first()
等价于：
  User.query.filter_by(username="x", tenant_id=g.tenant_id).first()

绕过条件（这些都不会触发 filter）：
  1. 不在 request context 中（如 Celery 任务、Flask CLI）
  2. g.bypass_tenant_filter = True（superuser 路径）
  3. g.tenant_id 未设置（注册等公开接口）

新增业务模型时务必继承 TenantMixin，否则数据会全局可见！
"""

from sqlalchemy import Column, Integer, ForeignKey, event
from sqlalchemy.orm import ORMExecuteState
from flask import g, has_request_context

from app import db
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TenantMixin:
    """租户隔离 mixin — 业务模型继承后自动获得 tenant_id 列与全局查询过滤"""

    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)


def _should_apply_filter() -> bool:
    """是否应当对当前查询应用 tenant filter"""
    if not has_request_context():
        return False
    if getattr(g, "bypass_tenant_filter", False):
        return False
    if getattr(g, "tenant_id", None) is None:
        if getattr(g, "current_user_id", None) is not None:
            from app.utils.errors import BusinessError, ErrorCode
            raise BusinessError(ErrorCode.TENANT_NOT_FOUND, "已认证请求缺少租户上下文")
        return False
    return True


@event.listens_for(db.session, "do_orm_execute")
def _add_tenant_filter(execute_state: ORMExecuteState):
    """全局拦截 ORM 查询，自动加 tenant_id filter

    使用 SQLAlchemy 2.x 风格的 do_orm_execute 事件，
    它能覆盖 Query API 和 select() 两种调用方式。
    """
    if not execute_state.is_select:
        return
    if not _should_apply_filter():
        return

    tenant_id = g.tenant_id

    from sqlalchemy.orm import with_loader_criteria
    execute_state.statement = execute_state.statement.options(
        with_loader_criteria(
            TenantMixin,
            lambda cls: cls.tenant_id == tenant_id,
            include_aliases=True,
        )
    )


@event.listens_for(db.session, "before_flush")
def _validate_tenant_writes(session, _flush_context, _instances):
    """Reject cross-tenant inserts and updates before SQL reaches the database."""
    if not has_request_context() or getattr(g, "bypass_tenant_filter", False):
        return
    if getattr(g, "current_user_id", None) is None:
        return
    tenant_id = getattr(g, "tenant_id", None)
    if tenant_id is None:
        from app.utils.errors import BusinessError, ErrorCode
        raise BusinessError(ErrorCode.TENANT_NOT_FOUND, "已认证请求缺少租户上下文")
    for instance in session.new.union(session.dirty):
        if isinstance(instance, TenantMixin) and instance.tenant_id != tenant_id:
            from app.utils.errors import BusinessError, ErrorCode
            raise BusinessError(ErrorCode.PERMISSION_DENIED, "禁止写入其他租户的数据")
