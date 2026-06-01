"""CSV 数据质量检查接口"""

import os

from flask import Blueprint, g, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError

from app import limiter
from app.permissions import Permission
from app.schemas.csv_quality_schema import (
    MAX_CSV_TEXT_LENGTH,
    _validate_csv_text,
    validate_csv_filename,
    validate_task_name,
)
from app.schemas.task_schema import TaskQuerySchema
from app.services.csv_quality_service import (
    create_csv_quality_task,
    csv_quality_task_to_dict,
    delete_csv_quality_task,
    get_csv_quality_task,
    list_csv_quality_tasks,
    retry_csv_quality_task,
)
from app.tasks.csv_quality_task import check_csv_quality
from app.utils.decorators import require_permission
from app.utils.errors import BusinessError, ErrorCode
from app.utils.response import created, ok, paginated
from app.utils.validation import validate_schema

csv_quality_bp = Blueprint("csv_quality", __name__)


@csv_quality_bp.route("/", methods=["POST"])
@jwt_required()
@require_permission(Permission.TASK_CREATE)
@limiter.limit("20 per minute")
def submit_csv_quality():
    """提交 CSV 数据质量检查任务"""

    user_id = int(get_jwt_identity())
    if not request.form and not request.files:
        raise BusinessError(ErrorCode.EMPTY_BODY)

    try:
        task_name = validate_task_name(request.form.get("task_name", ""))
        upload = request.files.get("file")
        if not upload:
            raise ValidationError("CSV 文件不能为空")
        filename = validate_csv_filename(os.path.basename(upload.filename or ""))
        csv_text = _read_uploaded_csv(upload)
        _validate_csv_text(csv_text)
    except ValidationError as err:
        messages = err.messages
        if isinstance(messages, list):
            detail = messages[0]
        else:
            detail = str(messages)
        return jsonify({
            "code": ErrorCode.VALIDATION_ERROR.code,
            "message": f"{ErrorCode.VALIDATION_ERROR.message}: {detail}",
        }), ErrorCode.VALIDATION_ERROR.http

    task = create_csv_quality_task(
        user_id=user_id,
        task_name=task_name,
        csv_text=csv_text,
        filename=filename,
    )
    check_csv_quality.delay(task.id, g.tenant_id)

    return created(csv_quality_task_to_dict(task), message="任务已提交")


def _read_uploaded_csv(upload) -> str:
    """读取上传 CSV，限制大小并兼容常见编码"""

    raw = upload.stream.read(MAX_CSV_TEXT_LENGTH + 1)
    if len(raw) > MAX_CSV_TEXT_LENGTH:
        raise ValidationError("CSV 文件不能超过 200000 字节")

    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValidationError("CSV 文件编码仅支持 UTF-8 或 GB18030")


@csv_quality_bp.route("/<int:task_id>", methods=["GET"])
@jwt_required()
@require_permission(Permission.TASK_READ)
def get_csv_quality(task_id):
    """查询单个 CSV 数据质量检查任务"""

    task = get_csv_quality_task(task_id)
    return ok(csv_quality_task_to_dict(task))


@csv_quality_bp.route("/", methods=["GET"])
@jwt_required()
@require_permission(Permission.TASK_READ)
def list_csv_quality():
    """分页查询当前租户的 CSV 数据质量检查任务"""

    parsed, error = validate_schema(TaskQuerySchema(), request.args)
    if error:
        return error

    pagination = list_csv_quality_tasks(parsed["page"], parsed["per_page"])
    return paginated(
        items=[csv_quality_task_to_dict(t) for t in pagination.items],
        total=pagination.total,
        page=pagination.page,
        per_page=pagination.per_page,
    )


@csv_quality_bp.route("/<int:task_id>/retry", methods=["POST"])
@jwt_required()
@require_permission(Permission.TASK_CREATE)
def retry_csv_quality(task_id):
    """重新提交 CSV 数据质量检查任务"""

    task = retry_csv_quality_task(task_id)
    return ok(csv_quality_task_to_dict(task), message="任务已重新提交")


@csv_quality_bp.route("/<int:task_id>", methods=["DELETE"])
@jwt_required()
@require_permission(Permission.TASK_DELETE_ANY)
def delete_csv_quality(task_id):
    """删除 CSV 数据质量检查任务"""

    delete_csv_quality_task(task_id)
    return ok(message="任务已删除")
