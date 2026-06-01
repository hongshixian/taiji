"""通用任务接口"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.schemas.task_schema import TaskQuerySchema
from app.services.task_service import list_tasks, task_base_to_dict
from app.permissions import Permission
from app.utils.decorators import require_permission
from app.utils.response import paginated
from app.utils.validation import validate_schema

task_bp = Blueprint("task", __name__)


@task_bp.route("/", methods=["GET"])
@jwt_required()
@require_permission(Permission.TASK_READ)
def list_all_tasks():
    """分页查询当前租户所有任务"""

    parsed, error = validate_schema(TaskQuerySchema(), request.args)
    if error:
        return error

    pagination = list_tasks(parsed["page"], parsed["per_page"])
    return paginated(
        items=[task_base_to_dict(t) for t in pagination.items],
        total=pagination.total,
        page=pagination.page,
        per_page=pagination.per_page,
    )
