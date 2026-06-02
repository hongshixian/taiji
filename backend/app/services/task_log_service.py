"""任务执行日志服务"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import current_app

from app.models.task import Task
from app.utils.errors import BusinessError, ErrorCode
from app.utils.logger import get_logger


VALID_LEVELS = {"DEBUG", "INFO", "WARN", "ERROR"}
logger = get_logger(__name__)


class TaskLogger:
    """单任务 JSONL 日志写入器。"""

    def __init__(self, task: Task):
        self.task = task
        self.started_at = _as_utc(task.created_at) or datetime.now(timezone.utc)
        if not task.log_path:
            task.log_path = build_task_log_path(task.tenant_id, task.task_type, task.id)

    def debug(self, *, step: str, event: str, msg: str, data: dict | None = None):
        self.log("DEBUG", step=step, event=event, msg=msg, data=data)

    def info(self, *, step: str, event: str, msg: str, data: dict | None = None):
        self.log("INFO", step=step, event=event, msg=msg, data=data)

    def warn(self, *, step: str, event: str, msg: str, data: dict | None = None):
        self.log("WARN", step=step, event=event, msg=msg, data=data)

    def error(self, *, step: str, event: str, msg: str, data: dict | None = None):
        self.log("ERROR", step=step, event=event, msg=msg, data=data)

    def log(self, level: str, *, step: str, event: str, msg: str,
            data: dict | None = None):
        level = level.upper()
        if level not in VALID_LEVELS:
            raise ValueError(f"invalid task log level: {level}")

        now = datetime.now(timezone.utc)
        payload = {
            "ts": now.isoformat().replace("+00:00", "Z"),
            "level": level,
            "step": step,
            "event": event,
            "msg": msg,
            "elapsed_ms": max(0, int((now - self.started_at).total_seconds() * 1000)),
            "data": data or {},
        }
        append_task_log(self.task.log_path, payload)


def create_task_logger(task: Task) -> TaskLogger:
    return TaskLogger(task)


def build_task_log_path(tenant_id: int, task_type: str, task_id: int) -> str:
    return f"tasks/tenant_{tenant_id}/{task_type}/task_{task_id}.jsonl"


def append_task_log(log_path: str, payload: dict[str, Any]) -> None:
    try:
        path = _resolve_log_path(log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
        with path.open("a", encoding="utf-8") as fp:
            fp.write(line + "\n")
    except Exception as exc:
        logger.warning("任务日志写入失败: %s", exc)


def read_task_log_entries(task: Task) -> list[dict]:
    if not task.log_path:
        return []
    path = _resolve_log_path(task.log_path)
    if not path.exists():
        return []

    entries = []
    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                entries.append({
                    "ts": None,
                    "level": "ERROR",
                    "step": "log",
                    "event": "log_parse_failed",
                    "msg": "日志行解析失败",
                    "elapsed_ms": 0,
                    "data": {"raw": line},
                })
    return entries


def task_log_response(task: Task) -> dict:
    return {
        "task_id": task.id,
        "task_type": task.task_type,
        "log_path": task.log_path,
        "items": read_task_log_entries(task),
    }


def _resolve_log_path(log_path: str) -> Path:
    if not log_path or Path(log_path).is_absolute() or ".." in Path(log_path).parts:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "任务日志路径无效")

    root = Path(current_app.config["TASK_LOG_ROOT"]).resolve()
    path = (root / log_path).resolve()
    if root != path and root not in path.parents:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "任务日志路径越界")
    return path


def _as_utc(value: datetime | None) -> datetime | None:
    if not value:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
