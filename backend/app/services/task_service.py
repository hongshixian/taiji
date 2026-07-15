"""通用任务生命周期服务"""

from datetime import datetime, timezone

from flask import g
from sqlalchemy import func

from app import db
from app.models.task import Task, TaskStatus
from app.utils.errors import BusinessError, ErrorCode


def create_task_record(user_id: int, task_type: str) -> Task:
    """创建任务总表记录（从 g.tenant_id 取租户）"""

    tenant_id = getattr(g, "tenant_id", None)
    if tenant_id is None:
        raise ValueError("未指定租户上下文（缺少 g.tenant_id）")

    task = Task(
        tenant_id=tenant_id,
        user_id=user_id,
        task_type=task_type,
        status=TaskStatus.PENDING.value,
    )
    db.session.add(task)
    db.session.flush()
    from app.services.task_log_service import create_task_logger
    task_logger = create_task_logger(task)
    task_logger.info(
        step="create",
        event="task_created",
        msg="任务已创建",
        data={"task_type": task.task_type},
    )
    return task


def get_task_or_404(task_id: int, task_type: str | None = None) -> Task:
    """按租户上下文查询任务，不存在则抛业务异常"""

    query = Task.query.filter_by(id=task_id)
    if task_type:
        query = query.filter_by(task_type=task_type)
    task = query.first()
    if not task:
        raise BusinessError(ErrorCode.TASK_NOT_FOUND)
    return task


def list_tasks(page: int = 1, per_page: int = 20, task_type: str | None = None):
    """分页查询当前租户任务"""

    query = Task.query
    if task_type:
        query = query.filter_by(task_type=task_type)
    return (
        query
        .order_by(Task.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )


def count_tasks_by_status(task_type: str | None = None) -> dict:
    """按状态统计当前租户任务数量（供页面顶部指标用）。

    返回各状态计数 + 派生的 active(pending+running) 与 total。
    依赖 TenantMixin 的全局查询拦截，自动限定在当前租户内。
    """

    query = Task.query.with_entities(Task.status, func.count(Task.id))
    if task_type:
        query = query.filter(Task.task_type == task_type)
    rows = query.group_by(Task.status).all()
    counts = {status: cnt for status, cnt in rows}

    statuses = [s.value for s in TaskStatus]
    result = {s: counts.get(s, 0) for s in statuses}
    result["active"] = result["pending"] + result["running"]
    result["total"] = sum(result[s] for s in statuses)
    return result


def mark_running(task: Task) -> None:
    task.status = TaskStatus.RUNNING.value
    task.started_at = datetime.now(timezone.utc)
    task.completed_at = None
    task.error_message = None
    db.session.commit()


def mark_success(task: Task) -> None:
    task.status = TaskStatus.SUCCESS.value
    task.error_message = None
    task.completed_at = datetime.now(timezone.utc)
    db.session.commit()


def mark_failed(task: Task, message: str) -> None:
    task.status = TaskStatus.FAILED.value
    task.error_message = message
    task.completed_at = datetime.now(timezone.utc)
    db.session.commit()


def mark_stopped(task: Task) -> None:
    task.status = TaskStatus.STOPPED.value
    task.completed_at = datetime.now(timezone.utc)
    db.session.commit()


def set_celery_task_id(task: Task, celery_id: str) -> None:
    task.celery_task_id = celery_id
    db.session.commit()


def reset_task(task: Task) -> None:
    task.status = TaskStatus.PENDING.value
    task.error_message = None
    task.started_at = None
    task.completed_at = None
    task.progress = None
    db.session.commit()


def delete_task_record(task: Task) -> None:
    db.session.delete(task)
    db.session.commit()


def task_base_to_dict(task: Task) -> dict:
    """任务总表字段序列化"""

    return {
        "id": task.id,
        "task_type": task.task_type,
        "task_type_name": task.task_type_name,
        "status": task.status if isinstance(task.status, str) else task.status.value,
        "error_message": task.error_message,
        "log_path": task.log_path,
        "user_id": task.user_id,
        "username": task.user.username if task.user else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }
