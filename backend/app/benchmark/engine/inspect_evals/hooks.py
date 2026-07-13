"""进度上报 hook —— 用 inspect_ai 的 hook 机制把样本完成事件推给 taiji 的 ProgressReporter

一次评测启动时，把 ProgressReporter 塞到一个线程局部变量里，
Hooks 类通过读它来上报。这样：
  * 不需要修改 inspect_evals 源码
  * 也不需要每次 eval() 都新建一个 hook 类
"""

from __future__ import annotations

import threading


_state = threading.local()


class _ProgressState:
    def __init__(self, progress, total_hint: int, logger):
        self.progress = progress
        self.total = total_hint
        self.completed = 0
        self.logger = logger


def _current() -> _ProgressState | None:
    return getattr(_state, "value", None)


def bind(progress, total_hint: int, logger) -> None:
    """在 eval() 调用前绑定一次；同一线程只允许一个活跃状态"""

    _state.value = _ProgressState(progress, total_hint, logger)


def release() -> None:
    if hasattr(_state, "value"):
        del _state.value


# ---------------------------------------------------------------------------
# Hooks —— 由 inspect_ai 通过 entry_points 或 register_hooks() 加载
# ---------------------------------------------------------------------------
# inspect_ai >=0.3.60 提供的 hooks API 是 @hooks 装饰器 + Hooks 基类。
# 但 hooks 接口在 0.3.x 尾段有过调整（Hooks vs TaskHooks），因此这里做兼容导入。
# ---------------------------------------------------------------------------

_registered = False


def _try_register() -> bool:
    """尝试注册 hook；不同 inspect_ai 版本的 hook API 可能略有差异，静默降级。"""

    global _registered
    if _registered:
        return True

    try:
        from inspect_ai.hooks import hooks, Hooks   # noqa
    except Exception:
        try:
            from inspect_ai.hooks import Hooks   # noqa
            hooks = None  # 老版本没有装饰器，走 Hooks 子类被自动发现的路径
        except Exception:
            return False

    try:
        base = Hooks  # type: ignore[name-defined]
    except NameError:
        return False

    @hooks(  # type: ignore[misc]
        name="taiji_progress",
        description="Report sample-level progress to Taiji task log",
    ) if hooks else _identity  # type: ignore[operator]
    class TaijiProgressHooks(base):  # type: ignore[misc, valid-type]
        async def on_sample_end(self, data):  # noqa: ANN001
            state = _current()
            if state is None:
                return
            state.completed += 1
            try:
                if state.total <= 0:
                    total = getattr(data, "total_samples", None) or state.completed
                else:
                    total = state.total
                state.progress.report(
                    completed=state.completed,
                    total=total,
                )
            except Exception:  # 不能让 hook 抛异常打断评测
                pass

        async def on_task_start(self, data):  # noqa: ANN001
            state = _current()
            if state is None:
                return
            try:
                total = getattr(data, "total_samples", None)
                if total:
                    state.total = int(total)
                    state.progress.report(completed=0, total=state.total)
            except Exception:
                pass

        async def on_task_end(self, data):  # noqa: ANN001
            state = _current()
            if state is None:
                return
            try:
                state.progress.report(
                    completed=state.completed,
                    total=state.total or state.completed,
                )
            except Exception:
                pass

    _registered = True
    return True


def _identity(fn):  # 兼容 fallback（当 hooks 装饰器不存在时）
    return fn


def ensure_registered(logger) -> bool:
    """在 engine.run() 里调用一次即可（幂等）"""

    ok = _try_register()
    if not ok and logger is not None:
        try:
            logger.warn(
                step="run",
                event="hooks_unavailable",
                msg="inspect_ai 版本不支持 hooks API，进度上报将退化为起止两点",
            )
        except Exception:
            pass
    return ok
