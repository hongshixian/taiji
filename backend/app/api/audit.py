"""审计日志接口"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.permissions import Permission
from app.services.audit_log_service import list_audit_logs
from app.utils.decorators import require_permission
from app.utils.response import paginated

audit_bp = Blueprint("audit", __name__)


@audit_bp.route("", methods=["GET"])
@jwt_required()
@require_permission(Permission.SYSTEM_AUDIT)
def get_audit_logs():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    tenant_id = request.args.get("tenant_id", type=int)
    actor_user_id = request.args.get("actor_user_id", type=int)
    action = request.args.get("action")
    resource_type = request.args.get("resource_type")
    resource_id = request.args.get("resource_id")
    result = request.args.get("result")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    items, total = list_audit_logs(
        page=page,
        per_page=per_page,
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        result=result,
        date_from=date_from,
        date_to=date_to,
    )
    return paginated(items=items, total=total, page=page, per_page=per_page)
