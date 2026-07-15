"""Engine 执行时可以调用的上下文（进度上报、取消检查、日志、工作目录）

这些接口对引擎屏蔽了 taiji 的具体实现（Task ORM / task_log_service / Celery revoke）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol


class ProgressReporter(Protocol):
    """引擎上报进度的最小接口"""

    def report(
        self,
        *,
        completed: int,
        total: int,
        current_metrics: dict | None = None,
        current_sample: str | None = None,
        sample_grid: list[dict] | None = None,
    ) -> None: ...


class CancelToken(Protocol):
    def cancelled(self) -> bool: ...


class EngineLogger(Protocol):
    """引擎需要的最小日志接口（写到任务的 JSONL 日志）"""

    def info(self, *, step: str, event: str, msg: str, data: dict | None = None) -> None: ...
    def warn(self, *, step: str, event: str, msg: str, data: dict | None = None) -> None: ...
    def error(self, *, step: str, event: str, msg: str, data: dict | None = None) -> None: ...


@dataclass
class TaskExecutionContext:
    """一次任务执行的完整上下文"""

    task_id: int
    tenant_id: int
    workspace: Path                          # 该任务的产物目录（引擎写 .eval 到这里）
    hf_cache_dir: Path                       # HuggingFace datasets 缓存目录
    logger: EngineLogger
    progress: ProgressReporter
    cancel_token: CancelToken
    extra_env: dict = field(default_factory=dict)    # 额外环境变量


# ---------------------------------------------------------------------------
# 简单实现：把进度写到 Task 表 + 任务 JSONL 日志
# ---------------------------------------------------------------------------

class _DbProgressReporter:
    """默认实现：把进度更新到 Task.progress + 日志。"""

    def __init__(self, task_id: int, task_logger, min_interval_ms: int = 1000):
        self._task_id = task_id
        self._logger = task_logger
        self._min_interval_ms = min_interval_ms
        self._last_completed = -1
        self._last_ts = 0.0

    def report(self, *, completed, total, current_metrics=None, current_sample=None, sample_grid=None):
        # 只有推进才写库/日志，避免刷屏
        if completed == self._last_completed:
            return
        # 时间节流：非最终上报至少间隔 min_interval_ms，防止大 N 时逐样本刷库
        import time
        now = time.monotonic()
        is_final = bool(total) and completed >= total
        if not is_final and (now - self._last_ts) * 1000 < self._min_interval_ms:
            return
        self._last_completed = completed
        self._last_ts = now

        from app import db
        from app.models.task import Task

        task = db.session.get(Task, self._task_id)
        if task is None:
            return
        task.progress = {
            "completed": completed,
            "total": total,
            "current_metrics": current_metrics or {},
            "sample_grid": sample_grid or [],
        }
        db.session.commit()

        self._logger.info(
            step="run",
            event="progress",
            msg=f"进度 {completed}/{total}",
            data={
                "completed": completed,
                "total": total,
                "sample": current_sample,
                "metrics": current_metrics or {},
            },
        )


class _NoopCancelToken:
    def cancelled(self) -> bool:
        return False


def build_context(
    *,
    task_id: int,
    tenant_id: int,
    workspace: Path,
    hf_cache_dir: Path,
    task_logger,
    cancel_token: CancelToken | None = None,
    extra_env: dict | None = None,
) -> TaskExecutionContext:
    """taiji Handler 层构造 Context 的便捷入口"""

    workspace.mkdir(parents=True, exist_ok=True)
    hf_cache_dir.mkdir(parents=True, exist_ok=True)
    return TaskExecutionContext(
        task_id=task_id,
        tenant_id=tenant_id,
        workspace=workspace,
        hf_cache_dir=hf_cache_dir,
        logger=task_logger,
        progress=_DbProgressReporter(task_id, task_logger),
        cancel_token=cancel_token or _NoopCancelToken(),
        extra_env=extra_env or {},
    )
