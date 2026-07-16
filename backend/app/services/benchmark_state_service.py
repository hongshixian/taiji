"""Benchmark suite 启用状态 + 检测结果服务

合并「suites.yaml 的静态 SuiteDescriptor」与「租户级 BenchmarkSuiteState 覆盖」，
对外提供有效启用判定、列表、启用切换、检测状态读写。

租户作用域：
  * 请求上下文里，TenantMixin 自动过滤 BenchmarkSuiteState.query 到 g.tenant_id。
  * Celery worker 无请求上下文（bypass_tenant_filter），故写路径显式接收 tenant_id 并手动 filter。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError

from app import db
from app.benchmark.dto import SuiteDescriptor
from app.benchmark.engine.registry import engine_registry
from app.models.benchmark_suite_state import BenchmarkSuiteState
from app.utils.errors import BusinessError, ErrorCode


# pending 超过此时长视为卡死 → 读取时按 unknown 呈现（不阻止重新检测）
_PENDING_STALE = timedelta(minutes=15)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# 有效启用判定
# ---------------------------------------------------------------------------

def effective_enabled(suite: SuiteDescriptor, state: BenchmarkSuiteState | None) -> bool:
    """租户覆盖优先：state.enabled 非 None 用它，否则回退 yaml 默认（not disabled）。"""
    if state is not None and state.enabled is not None:
        return bool(state.enabled)
    return not suite.disabled


def _validate_suite_key(suite_key: str) -> SuiteDescriptor:
    for s in engine_registry.all_suites(include_disabled=True):
        if s.key == suite_key:
            return s
    raise BusinessError(ErrorCode.VALIDATION_ERROR, f"未知 benchmark suite：{suite_key}")


def _effective_check_status(state: BenchmarkSuiteState | None) -> str:
    """把 pending 且过期的视为 unknown（读时计算，无需清扫器）。"""
    if state is None:
        return "unknown"
    status = state.last_check_status or "unknown"
    if status == "pending" and state.last_check_at is not None:
        at = state.last_check_at
        if at.tzinfo is None:
            at = at.replace(tzinfo=timezone.utc)
        if _utcnow() - at > _PENDING_STALE:
            return "unknown"
    return status


# ---------------------------------------------------------------------------
# 读：列表 / 有效启用 keys（请求上下文，自动租户过滤）
# ---------------------------------------------------------------------------

def _states_by_key() -> dict[str, BenchmarkSuiteState]:
    """当前租户的 state 映射（依赖 TenantMixin 自动过滤）。"""
    return {s.suite_key: s for s in BenchmarkSuiteState.query.all()}


def list_suites_with_state() -> list[dict]:
    """管理页数据：全部 suite（含 disabled）+ 租户 state 合并。

    sample_count 取自 suite.to_dict() 的静态调研值（suites.yaml），不再用检测时的动态值。
    """
    states = _states_by_key()
    items: list[dict] = []
    for suite in engine_registry.all_suites(include_disabled=True):
        state = states.get(suite.key)
        items.append({
            **suite.to_dict(),
            "effective_enabled": effective_enabled(suite, state),
            "override_enabled": (state.enabled if state is not None else None),
            "last_check_status": _effective_check_status(state),
            "last_check_error": (state.last_check_error if state else None),
            "last_check_at": (state.last_check_at.isoformat() if state and state.last_check_at else None),
            "last_check_ms": (state.last_check_ms if state else None),
        })
    return items


def enabled_suite_keys_for_tenant() -> list[str]:
    """当前租户有效启用的 suite key（任务创建下拉 / 提交校验用，请求上下文）。"""
    states = _states_by_key()
    return [
        s.key
        for s in engine_registry.all_suites(include_disabled=True)
        if effective_enabled(s, states.get(s.key))
    ]


# ---------------------------------------------------------------------------
# 写：启用切换（请求上下文，需 tenant_id 建行）
# ---------------------------------------------------------------------------

def set_enabled(tenant_id: int, suite_key: str, enabled: bool | None) -> dict:
    _validate_suite_key(suite_key)
    state = _get_or_create_state(tenant_id, suite_key)
    state.enabled = enabled
    state.updated_at = _utcnow()
    db.session.commit()
    return _one_item(suite_key)


def _one_item(suite_key: str) -> dict:
    suite = _validate_suite_key(suite_key)
    state = (
        BenchmarkSuiteState.query.filter_by(suite_key=suite_key).first()
    )
    return {
        **suite.to_dict(),
        "effective_enabled": effective_enabled(suite, state),
        "override_enabled": (state.enabled if state is not None else None),
        "last_check_status": _effective_check_status(state),
        "last_check_error": (state.last_check_error if state else None),
        "last_check_at": (state.last_check_at.isoformat() if state and state.last_check_at else None),
        "last_check_ms": (state.last_check_ms if state else None),
    }


def is_check_pending(suite_key: str) -> bool:
    """当前租户下该 suite 是否有未过期的 pending 检测（请求上下文）。"""
    state = BenchmarkSuiteState.query.filter_by(suite_key=suite_key).first()
    return _effective_check_status(state) == "pending"


# ---------------------------------------------------------------------------
# get_or_create（防并发唯一约束冲突）
# ---------------------------------------------------------------------------

def _get_or_create_state(tenant_id: int, suite_key: str) -> BenchmarkSuiteState:
    """按 (tenant_id, suite_key) 取或建。显式传 tenant_id 以兼容 worker 无请求上下文。"""
    state = BenchmarkSuiteState.query.filter_by(
        tenant_id=tenant_id, suite_key=suite_key
    ).first()
    if state is not None:
        return state
    state = BenchmarkSuiteState(tenant_id=tenant_id, suite_key=suite_key)
    db.session.add(state)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        state = BenchmarkSuiteState.query.filter_by(
            tenant_id=tenant_id, suite_key=suite_key
        ).first()
    return state


# ---------------------------------------------------------------------------
# 检测状态读写（请求 + worker 两侧都用，显式 tenant_id）
# ---------------------------------------------------------------------------

def mark_check_pending(tenant_id: int, suite_key: str) -> None:
    state = _get_or_create_state(tenant_id, suite_key)
    state.last_check_status = "pending"
    state.last_check_error = None
    state.last_check_at = _utcnow()
    state.updated_at = _utcnow()
    db.session.commit()


def record_check_result(tenant_id: int, suite_key: str, ok: bool, error: str | None, ms: int,
                         sample_count: int | None = None) -> None:
    state = _get_or_create_state(tenant_id, suite_key)
    state.last_check_status = "ok" if ok else "failed"
    state.last_check_error = (error or None) if not ok else None
    state.last_check_at = _utcnow()
    state.last_check_ms = ms
    if sample_count is not None:
        state.sample_count = sample_count
    state.updated_at = _utcnow()
    db.session.commit()
