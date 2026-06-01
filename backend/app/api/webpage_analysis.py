"""网页内容分析接口"""

from flask import Blueprint, g, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import limiter
from app.permissions import Permission
from app.schemas.task_schema import TaskQuerySchema
from app.schemas.webpage_analysis_schema import WebpageAnalysisSubmitSchema
from app.services.webpage_analysis_service import (
    create_webpage_analysis_task,
    delete_webpage_analysis_task,
    get_webpage_analysis_task,
    list_webpage_analysis_tasks,
    retry_webpage_analysis_task,
    webpage_analysis_task_to_dict,
)
from app.tasks.webpage_analysis_task import analyze_webpage
from app.utils.decorators import require_permission
from app.utils.errors import BusinessError, ErrorCode
from app.utils.response import created, ok, paginated
from app.utils.validation import validate_schema

webpage_analysis_bp = Blueprint("webpage_analysis", __name__)


@webpage_analysis_bp.route("/", methods=["POST"])
@jwt_required()
@require_permission(Permission.TASK_CREATE)
@limiter.limit("30 per minute")
def submit_webpage_analysis():
    """提交网页内容分析任务"""

    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data:
        raise BusinessError(ErrorCode.EMPTY_BODY)

    parsed, error = validate_schema(WebpageAnalysisSubmitSchema(), data)
    if error:
        return error

    task = create_webpage_analysis_task(user_id, parsed["url"].strip())
    analyze_webpage.delay(task.id, g.tenant_id)

    return created(webpage_analysis_task_to_dict(task), message="任务已提交")


@webpage_analysis_bp.route("/<int:task_id>", methods=["GET"])
@jwt_required()
@require_permission(Permission.TASK_READ)
def get_webpage_analysis(task_id):
    """查询单个网页内容分析任务"""

    task = get_webpage_analysis_task(task_id)
    return ok(webpage_analysis_task_to_dict(task))


@webpage_analysis_bp.route("/", methods=["GET"])
@jwt_required()
@require_permission(Permission.TASK_READ)
def list_webpage_analyses():
    """分页查询当前租户的网页内容分析任务"""

    parsed, error = validate_schema(TaskQuerySchema(), request.args)
    if error:
        return error

    pagination = list_webpage_analysis_tasks(parsed["page"], parsed["per_page"])
    return paginated(
        items=[webpage_analysis_task_to_dict(t) for t in pagination.items],
        total=pagination.total,
        page=pagination.page,
        per_page=pagination.per_page,
    )


@webpage_analysis_bp.route("/<int:task_id>/retry", methods=["POST"])
@jwt_required()
@require_permission(Permission.TASK_CREATE)
def retry_webpage_analysis(task_id):
    """重新提交网页内容分析任务"""

    task = retry_webpage_analysis_task(task_id)
    return ok(webpage_analysis_task_to_dict(task), message="任务已重新提交")


@webpage_analysis_bp.route("/<int:task_id>", methods=["DELETE"])
@jwt_required()
@require_permission(Permission.TASK_DELETE_ANY)
def delete_webpage_analysis(task_id):
    """删除网页内容分析任务"""

    delete_webpage_analysis_task(task_id)
    return ok(message="任务已删除")
