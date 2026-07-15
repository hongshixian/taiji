"""任务处理器抽象基类

框架只关心任务的生命周期（创建、列表、重试、删除）。
具体任务类型的提交参数解析、执行逻辑、序列化，全部由子类实现。
"""

from abc import ABC, abstractmethod

from flask import Blueprint, request, g
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import limiter
from app.permissions import Permission
from app.schemas.task_schema import TaskQuerySchema
from app.services.task_service import (
    delete_task_record,
    get_task_or_404,
    list_tasks,
    mark_stopped,
    reset_task,
    set_celery_task_id,
    task_base_to_dict,
)
from app.utils.decorators import require_permission
from app.utils.errors import BusinessError, ErrorCode
from app.utils.response import created, ok, paginated
from app.utils.validation import validate_schema


class BaseTaskHandler(ABC):
    """所有任务类型的抽象基类。

    子类必须声明：
        task_type       — 任务类型标识符，与 tasks.task_type 字段一致
        task_type_name  — 可读名称，用于 TASK_TYPE_NAMES 注册
        url_prefix      — 挂载路径段，如 "benchmark" → /api/v1/tasks/benchmark

    子类必须实现：
        submit(user_id) — 解析请求、创建并返回 Task（不负责派发 Celery task）
        execute(task_id) — Worker 执行逻辑，在 app context + bypass_tenant_filter 内调用
        to_dict(task)   — 序列化 task + detail 为 dict
    """

    task_type: str
    task_type_name: str
    url_prefix: str
    rate_limit_submit: str = "30 per minute"

    # ── 子类必须实现 ──────────────────────────────────────────────────────────

    @abstractmethod
    def submit(self, user_id: int):
        """解析 request context，创建并返回 Task（不 delay Celery task）。"""

    @abstractmethod
    def execute(self, task_id: int) -> None:
        """Worker 执行逻辑；在 Flask app context + bypass_tenant_filter 下调用。"""

    @abstractmethod
    def to_dict(self, task) -> dict:
        """将 task + detail 序列化为 API 响应 dict。"""

    # ── 框架提供默认实现（子类按需覆盖） ─────────────────────────────────────

    def get(self, task_id: int):
        return get_task_or_404(task_id, self.task_type)

    def list(self, page: int, per_page: int):
        return list_tasks(page=page, per_page=per_page, task_type=self.task_type)

    def retry(self, task_id: int):
        task = self.get(task_id)
        self._clear_detail(task)
        reset_task(task)
        result = self._celery_task.delay(task.id, task.tenant_id)
        set_celery_task_id(task, result.id)
        return task

    def stop(self, task_id: int):
        """停止任务：pending → 从队列撤销；running → 终止执行进程。"""
        from celery_app import celery

        task = self.get(task_id)
        if task.status not in ("pending", "running"):
            raise BusinessError(ErrorCode.VALIDATION_ERROR, "仅进行中或等待中的任务可停止")
        if task.celery_task_id:
            terminate = task.status == "running"
            celery.control.revoke(task.celery_task_id, terminate=terminate, signal="SIGTERM")
        mark_stopped(task)
        return task

    def delete(self, task_id: int) -> None:
        task = self.get(task_id)
        delete_task_record(task)

    def _clear_detail(self, task) -> None:
        """retry 时清空 detail 中的结果字段；子类按需覆盖。"""

    # ── 框架自动生成 Blueprint ────────────────────────────────────────────────

    def make_blueprint(self) -> Blueprint:
        """生成该任务类型的 Blueprint，包含标准的 5 个路由。"""

        bp = Blueprint(f"task_{self.task_type}", __name__)
        handler = self

        @bp.route("/", methods=["POST"])
        @jwt_required()
        @require_permission(Permission.TASK_CREATE)
        @limiter.limit(handler.rate_limit_submit)
        def _submit():
            user_id = int(get_jwt_identity())
            task = handler.submit(user_id)
            result = handler._celery_task.delay(task.id, g.tenant_id)
            set_celery_task_id(task, result.id)
            return created(handler.to_dict(task), message="任务已提交")

        @bp.route("/<int:task_id>", methods=["GET"])
        @jwt_required()
        @require_permission(Permission.TASK_READ)
        def _get(task_id):
            return ok(handler.to_dict(handler.get(task_id)))

        @bp.route("/", methods=["GET"])
        @jwt_required()
        @require_permission(Permission.TASK_READ)
        def _list():
            parsed, error = validate_schema(TaskQuerySchema(), request.args)
            if error:
                return error
            pg = handler.list(parsed["page"], parsed["per_page"])
            return paginated(
                items=[handler.to_dict(t) for t in pg.items],
                total=pg.total,
                page=pg.page,
                per_page=pg.per_page,
            )

        @bp.route("/<int:task_id>/retry", methods=["POST"])
        @jwt_required()
        @require_permission(Permission.TASK_CREATE)
        def _retry(task_id):
            return ok(handler.to_dict(handler.retry(task_id)), message="任务已重新提交")

        @bp.route("/<int:task_id>/stop", methods=["POST"])
        @jwt_required()
        @require_permission(Permission.TASK_CREATE)
        def _stop(task_id):
            return ok(handler.to_dict(handler.stop(task_id)), message="任务已停止")

        @bp.route("/<int:task_id>", methods=["DELETE"])
        @jwt_required()
        @require_permission(Permission.TASK_DELETE_ANY)
        def _delete(task_id):
            handler.delete(task_id)
            return ok(message="任务已删除")

        return bp

    # ── 框架自动生成 Celery task ──────────────────────────────────────────────

    def make_celery_task(self):
        """为该 handler 创建并注册对应的 Celery task，存入 self._celery_task。"""

        from celery_app import celery
        from app import db
        from app.utils.decorators import bypass_tenant_filter
        from app.utils.logger import get_logger

        handler = self
        log = get_logger(f"handler.{self.task_type}")
        task_name = f"tasks.{self.task_type}"

        @celery.task(bind=True, max_retries=0, name=task_name)
        def _task(self_task, task_id: int, tenant_id=None):
            log.info(f"Celery 任务启动: {handler.task_type} task_id={task_id}")
            try:
                with celery.flask_app.app_context():
                    with bypass_tenant_filter():
                        handler.execute(task_id)
                    db.session.remove()
            except Exception:
                log.exception(f"Celery 任务 {task_id} 致命异常")
                return {"task_id": task_id, "status": "error"}
            return {"task_id": task_id, "status": "completed"}

        self._celery_task = _task
        return _task
