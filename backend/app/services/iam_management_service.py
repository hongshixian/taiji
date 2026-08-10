"""Taiji management operations backed by the controlled IAM API."""

from __future__ import annotations

from uuid import uuid4

from flask import g

from app import db
from app.models.tenant import Tenant
from app.models.tenant_membership import TenantMembership
from app.models.user import User
from app.services.auth_service import user_to_dict
from app.services.iam_client import IamClient, IamHttpError, as_business_error
from app.services.iam_projection_service import (
    project_iam_members,
    project_iam_tenant,
    project_platform_admin,
    project_platform_admins,
)
from app.services.oidc_session_service import current_iam_access_token
from app.utils.decorators import bypass_tenant_filter
from app.utils.errors import BusinessError, ErrorCode


ROLE_ALIASES = {
    "tenant_admin": "tenant_admin",
    "member": "member",
    "admin": "tenant_admin",
    "user": "member",
}


def list_members(page: int, per_page: int, tenant_id: int | None = None):
    tenant = _tenant(tenant_id)
    _require_enterprise(tenant)
    payload = _iam_call(
        IamClient().list_members,
        current_iam_access_token(),
        _iam_tenant_id(tenant),
    )
    remote_members = payload.get("members", [])
    if not isinstance(remote_members, list):
        raise BusinessError(ErrorCode.INTERNAL_ERROR, "IAM 成员列表格式无效")
    projected = project_iam_members(tenant, remote_members)
    items = [user_to_dict(user, membership) for user, membership in projected]
    total = len(items)
    start = max(page - 1, 0) * per_page
    return items[start:start + per_page], total


def get_member(local_user_id: int, tenant_id: int | None = None) -> dict:
    items, _ = list_members(page=1, per_page=10000, tenant_id=tenant_id)
    member = next((item for item in items if item["id"] == local_user_id), None)
    if member is None:
        raise BusinessError(ErrorCode.USER_NOT_FOUND, "该用户不是当前租户成员")
    return member


def add_member(identifier: str, role: str, tenant_id: int | None = None) -> dict:
    tenant = _tenant(tenant_id)
    _require_enterprise(tenant)
    result = _iam_call(
        IamClient().add_member,
        current_iam_access_token(),
        _iam_tenant_id(tenant),
        {"identifier": identifier, "role": _iam_role(role)},
    )
    if "invitation_id" in result:
        return {"kind": "invitation", **result}
    projected = project_iam_members(tenant, [result])
    user, membership = projected[0]
    _audit_member("tenant_member.add", tenant, user, membership)
    return {"kind": "member", **user_to_dict(user, membership)}


def update_member(local_user_id: int, data: dict, tenant_id: int | None = None) -> dict:
    tenant = _tenant(tenant_id)
    _require_enterprise(tenant)
    user, membership = _local_member(tenant, local_user_id)
    payload = {}
    if "role" in data and data["role"] is not None:
        payload["role"] = _iam_role(data["role"])
    active = data.get("active", data.get("membership_active"))
    if active is not None:
        payload["active"] = _boolean(active, "active")
    if not payload:
        raise BusinessError(ErrorCode.EMPTY_BODY, "角色或成员状态不能为空")
    result = _iam_call(
        IamClient().update_member,
        current_iam_access_token(),
        _iam_tenant_id(tenant),
        _iam_user_id(user),
        payload,
    )
    projected_user, projected_membership = project_iam_members(tenant, [result])[0]
    _audit_member("tenant_member.update", tenant, projected_user, projected_membership)
    return user_to_dict(projected_user, projected_membership)


def deactivate_member(local_user_id: int, actor_user_id: int, tenant_id: int | None = None):
    if local_user_id == actor_user_id:
        raise BusinessError(ErrorCode.CANNOT_DELETE_SELF, "不能移除自己的当前租户身份")
    tenant = _tenant(tenant_id)
    _require_enterprise(tenant)
    user, _membership = _local_member(tenant, local_user_id)
    result = _iam_call(
        IamClient().deactivate_member,
        current_iam_access_token(),
        _iam_tenant_id(tenant),
        _iam_user_id(user),
    )
    projected_user, projected_membership = project_iam_members(tenant, [result])[0]
    _audit_member("tenant_member.remove", tenant, projected_user, projected_membership)
    return user_to_dict(projected_user, projected_membership)


def create_enterprise_tenant(name: str, initial_admin: str, idempotency_key: str | None):
    result = _iam_call(
        IamClient().create_tenant,
        current_iam_access_token(),
        {"name": name, "initialAdmin": initial_admin},
        idempotency_key or str(uuid4()),
    )
    return project_iam_tenant(result)


def update_enterprise_tenant(local_tenant_id: int, data: dict):
    tenant = _tenant(local_tenant_id)
    _require_enterprise(tenant)
    payload = {}
    if "name" in data:
        name = data["name"]
        if not isinstance(name, str) or not name.strip():
            raise BusinessError(ErrorCode.VALIDATION_ERROR, "租户名称不能为空")
        payload["name"] = name.strip()
    if "enabled" in data:
        payload["enabled"] = _boolean(data["enabled"], "enabled")
    elif "is_active" in data:
        payload["enabled"] = _boolean(data["is_active"], "is_active")
    if not payload:
        raise BusinessError(ErrorCode.EMPTY_BODY, "租户名称或状态不能为空")
    result = _iam_call(
        IamClient().update_tenant,
        current_iam_access_token(),
        _iam_tenant_id(tenant),
        payload,
    )
    return project_iam_tenant(result)


def list_platform_admins() -> list[dict]:
    result = _iam_call(IamClient().list_platform_admins, current_iam_access_token())
    payloads = result.get("platform_admins", [])
    if not isinstance(payloads, list):
        raise BusinessError(ErrorCode.INTERNAL_ERROR, "IAM 平台管理员列表格式无效")
    return [user_to_dict(user, include_memberships=True) for user in project_platform_admins(payloads)]


def grant_platform_admin(identifier: str) -> dict:
    result = _iam_call(
        IamClient().grant_platform_admin,
        current_iam_access_token(),
        identifier,
    )
    return user_to_dict(project_platform_admin(result), include_memberships=True)


def revoke_platform_admin(local_user_id: int, actor_user_id: int) -> dict:
    if local_user_id == actor_user_id:
        raise BusinessError(ErrorCode.CANNOT_DELETE_SELF, "不能移除自己的平台管理员权限")
    with bypass_tenant_filter():
        user = db.session.get(User, local_user_id)
    if user is None:
        raise BusinessError(ErrorCode.USER_NOT_FOUND)
    result = _iam_call(
        IamClient().revoke_platform_admin,
        current_iam_access_token(),
        _iam_user_id(user),
    )
    return user_to_dict(project_platform_admin(result), include_memberships=True)


def _tenant(local_tenant_id: int | None = None) -> Tenant:
    resolved = local_tenant_id if local_tenant_id is not None else getattr(g, "tenant_id", None)
    if resolved is None:
        raise BusinessError(ErrorCode.TENANT_NOT_FOUND)
    with bypass_tenant_filter():
        tenant = db.session.get(Tenant, int(resolved))
    if tenant is None:
        raise BusinessError(ErrorCode.TENANT_NOT_FOUND)
    return tenant


def _local_member(tenant: Tenant, local_user_id: int) -> tuple[User, TenantMembership]:
    with bypass_tenant_filter():
        membership = TenantMembership.query.filter_by(
            tenant_id=tenant.id,
            user_id=local_user_id,
        ).first()
    if membership is None:
        raise BusinessError(ErrorCode.USER_NOT_FOUND, "该用户不是当前租户成员")
    return membership.user, membership


def _iam_tenant_id(tenant: Tenant) -> str:
    if not tenant.iam_tenant_id:
        raise BusinessError(ErrorCode.IDENTITY_CONFLICT, "本地租户尚未绑定 IAM")
    return tenant.iam_tenant_id


def _require_enterprise(tenant: Tenant) -> None:
    if tenant.tenant_type != "enterprise":
        raise BusinessError(ErrorCode.IAM_CONFLICT, "个人空间不能管理成员或企业租户设置")


def _iam_user_id(user: User) -> str:
    if not user.iam_user_id:
        raise BusinessError(ErrorCode.IDENTITY_CONFLICT, "本地用户尚未绑定 IAM")
    return user.iam_user_id


def _iam_role(value: str) -> str:
    if not isinstance(value, str):
        raise BusinessError(ErrorCode.INVALID_ROLE, "只支持 tenant_admin 或 member")
    role = ROLE_ALIASES.get((value or "").strip())
    if role is None:
        raise BusinessError(ErrorCode.INVALID_ROLE, "只支持 tenant_admin 或 member")
    return role


def _boolean(value, field: str) -> bool:
    if not isinstance(value, bool):
        raise BusinessError(ErrorCode.VALIDATION_ERROR, f"{field} 必须是布尔值")
    return value


def _iam_call(method, *args):
    try:
        return method(*args)
    except IamHttpError as error:
        raise as_business_error(error) from error


def _audit_member(action: str, tenant: Tenant, user: User, membership: TenantMembership):
    from app.services.audit_log_service import record_audit_log

    record_audit_log(
        action=action,
        resource_type="tenant_member",
        resource_id=membership.id,
        resource_name=user.username,
        tenant_id=tenant.id,
        after_data={
            "iam_user_id": user.iam_user_id,
            "iam_role": membership.iam_role,
            "is_active": membership.is_active,
        },
    )
    db.session.commit()
