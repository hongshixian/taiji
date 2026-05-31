"""分析接口"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.services.analyze_service import (
    create_task,
    get_task,
    get_user_tasks,
    retry_task,
    task_to_dict,
)
from app.tasks.analyze_task import analyze_webpage
from app.schemas.analyze_schema import AnalyzeSubmitSchema, AnalyzeQuerySchema
from app.utils.validation import validate_schema
from app.utils.response import ok, created, paginated
from app.utils.errors import BusinessError, ErrorCode
from app import limiter

analyze_bp = Blueprint("analyze", __name__)


@analyze_bp.route("/", methods=["POST"])
@jwt_required()
@limiter.limit("30 per minute")
def submit_analysis():
    """提交网页分析任务 — 限流 30次/分钟"""
    user_id = int(get_jwt_identity())

    data = request.get_json()
    if not data:
        raise BusinessError(ErrorCode.EMPTY_BODY)

    parsed, error = validate_schema(AnalyzeSubmitSchema(), data)
    if error:
        return error

    # 创建任务
    task = create_task(user_id, parsed["url"])

    # 提交到 Celery
    analyze_webpage.delay(task.id)

    return created(task_to_dict(task), message="任务已提交")


@analyze_bp.route("/<int:task_id>", methods=["GET"])
@jwt_required()
def get_analysis(task_id):
    """查询单个任务状态和结果"""
    user_id = int(get_jwt_identity())
    task = get_task(task_id, user_id)
    if not task:
        raise BusinessError(ErrorCode.TASK_NOT_FOUND)
    return ok(task_to_dict(task))


@analyze_bp.route("/", methods=["GET"])
@jwt_required()
def list_analyses():
    """分页查询历史任务"""
    user_id = int(get_jwt_identity())

    parsed, error = validate_schema(AnalyzeQuerySchema(), request.args)
    if error:
        return error

    pagination = get_user_tasks(user_id, parsed["page"], parsed["per_page"])

    return paginated(
        items=[task_to_dict(t) for t in pagination.items],
        total=pagination.total,
        page=pagination.page,
        per_page=pagination.per_page,
    )


@analyze_bp.route("/<int:task_id>/retry", methods=["POST"])
@jwt_required()
def retry_analysis(task_id):
    """重新提交失败/超时任务"""
    user_id = int(get_jwt_identity())
    task = retry_task(task_id, user_id)
    if not task:
        raise BusinessError(ErrorCode.TASK_NOT_FOUND)
    return ok(task_to_dict(task), message="任务已重新提交")
