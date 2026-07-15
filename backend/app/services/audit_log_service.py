"""审计日志服务"""

from datetime import datetime, timezone

from flask import g, has_request_context, request
from flask_jwt_extended import get_jwt, get_jwt_identity

from app import db
from app.models.audit_log import AuditLog
from app.models.tenant import Tenant
from app.models.user import User
from app.utils.decorators import bypass_tenant_filter
from app.utils.errors import BusinessError, ErrorCode


def audit_log_to_dict(log: AuditLog) -> dict:
    tenant_name = None
    if log.tenant_id is not None:
        tenant = db.session.get(Tenant, log.tenant_id)
        tenant_name = tenant.name if tenant else None
    return {
        "id": log.id,
        "tenant_id": log.tenant_id,
        "tenant_name": tenant_name,
        "actor_user_id": log.actor_user_id,
        "actor_username": log.actor_username,
        "actor_is_superuser": log.actor_is_superuser,
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "resource_name": log.resource_name,
        "result": log.result,
        "before_data": log.before_data,
        "after_data": log.after_data,
        "metadata": log.metadata_data,
        "ip_address": log.ip_address,
        "user_agent": log.user_agent,
        "request_id": log.request_id,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


def record_audit_log(
    *,
    action: str,
    resource_type: str,
    resource_id: str | int | None = None,
    resource_name: str | None = None,
    tenant_id: int | None = None,
    result: str = "success",
    before_data: dict | None = None,
    after_data: dict | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    """追加一条审计日志；不在这里 commit，由调用方业务事务统一提交。"""
    actor_user_id, actor_username, actor_is_superuser = _current_actor()
    log = AuditLog(
        tenant_id=_resolve_tenant_id(tenant_id),
        actor_user_id=actor_user_id,
        actor_username=actor_username,
        actor_is_superuser=actor_is_superuser,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        resource_name=resource_name,
        result=result,
        before_data=before_data,
        after_data=after_data,
        metadata_data=metadata,
        ip_address=_request_ip(),
        user_agent=_request_user_agent(),
        request_id=_request_id(),
    )
    db.session.add(log)
    return log


def list_audit_logs(
    *,
    page: int = 1,
    per_page: int = 20,
    tenant_id: int | None = None,
    actor_user_id: int | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    result: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> tuple[list[dict], int]:
    query = AuditLog.query

    if getattr(g, "is_superuser", False):
        if tenant_id is not None:
            query = query.filter(AuditLog.tenant_id == tenant_id)
    else:
        current_tenant_id = getattr(g, "tenant_id", None)
        if current_tenant_id is None:
            raise BusinessError(ErrorCode.TENANT_NOT_FOUND)
        query = query.filter(AuditLog.tenant_id == current_tenant_id)

    if actor_user_id is not None:
        query = query.filter(AuditLog.actor_user_id == actor_user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if resource_id:
        query = query.filter(AuditLog.resource_id == resource_id)
    if result:
        query = query.filter(AuditLog.result == result)
    if date_from:
        query = query.filter(AuditLog.created_at >= _parse_dt(date_from))
    if date_to:
        query = query.filter(AuditLog.created_at <= _parse_dt(date_to))

    pagination = (
        query
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    return [audit_log_to_dict(item) for item in pagination.items], pagination.total


def _current_actor() -> tuple[int | None, str | None, bool]:
    if not has_request_context():
        return None, None, False
    try:
        actor_user_id = int(get_jwt_identity())
        claims = get_jwt()
    except Exception:
        return None, None, False

    actor_username = None
    with bypass_tenant_filter():
        user = db.session.get(User, actor_user_id)
        if user:
            actor_username = user.username
    return actor_user_id, actor_username, bool(claims.get("is_superuser", False))


def _resolve_tenant_id(tenant_id: int | None) -> int | None:
    return tenant_id if tenant_id is not None else getattr(g, "tenant_id", None)


def _request_ip() -> str | None:
    if not has_request_context():
        return None
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.remote_addr


def _request_user_agent() -> str | None:
    if not has_request_context():
        return None
    ua = request.headers.get("User-Agent")
    return ua[:512] if ua else None


def _request_id() -> str | None:
    if not has_request_context():
        return None
    return request.headers.get("X-Request-ID")


def _parse_dt(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "日期格式无效") from exc
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed
