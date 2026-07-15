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
from sqlalchemy.orm import Query, ORMExecuteState
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

    # 对每个查询的根实体加 filter（如果它有 tenant_id 属性）
    execute_state.statement = execute_state.statement.options(
        # 不能用 options 加 filter；改为遍历实体显式 where
    )

    # 改用 with_loader_criteria：自动给所有匹配 TenantMixin 的表加 where
    from sqlalchemy.orm import with_loader_criteria
    execute_state.statement = execute_state.statement.options(
        with_loader_criteria(
            TenantMixin,
            lambda cls: cls.tenant_id == tenant_id,
            include_aliases=True,
        )
    )
