"""Idempotent projection of IAM identities into Taiji's local relational model."""

from datetime import datetime, timezone

from sqlalchemy import or_

from app import db
from app.models.role import Role
from app.models.tenant import Tenant
from app.models.tenant_membership import TenantMembership
from app.models.user import User
from app.utils.decorators import bypass_tenant_filter
from app.utils.errors import BusinessError, ErrorCode


IAM_ROLE_TO_LOCAL_ROLE = {
    "tenant_admin": "admin",
    "member": "user",
}


def project_login(userinfo: dict, identity: dict, is_superuser: bool = False):
    tenants = _active_tenants(identity.get("tenants", []))
    if not tenants:
        raise BusinessError(ErrorCode.TENANT_NOT_FOUND, "IAM 未返回可用租户")

    with bypass_tenant_filter():
        user = _project_user(userinfo, identity["user_id"], is_superuser)
        selected = _select_tenant(user, tenants)
        tenant, membership = _project_tenant_membership(user, selected)
        user.last_iam_tenant_id = selected["id"]
        db.session.commit()
        return user, tenant, membership, selected, tenants


def project_selected_tenant(user_id: int, tenant_payload: dict):
    with bypass_tenant_filter():
        user = db.session.get(User, user_id)
        if user is None:
            raise BusinessError(ErrorCode.USER_NOT_FOUND)
        tenant, membership = _project_tenant_membership(user, tenant_payload)
        user.last_iam_tenant_id = tenant_payload["id"]
        db.session.commit()
        return tenant, membership


def tenant_options(tenants: list[dict]) -> list[dict]:
    ids = [item["id"] for item in tenants]
    with bypass_tenant_filter():
        local = {
            tenant.iam_tenant_id: tenant.id
            for tenant in Tenant.query.filter(Tenant.iam_tenant_id.in_(ids)).all()
        } if ids else {}
    return [dict(item, local_id=local.get(item["id"])) for item in tenants]


def project_iam_tenant_membership(user: User, payload: dict):
    """Project one trusted IAM response without committing the caller's transaction."""
    return _project_tenant_membership(user, payload)


def _project_user(userinfo: dict, iam_user_id: str, is_superuser: bool) -> User:
    subject = _required(userinfo, "sub")
    username = userinfo.get("preferred_username") or userinfo.get("username") or subject
    email = userinfo.get("email") or f"{iam_user_id}@iam.invalid"
    now = datetime.now(timezone.utc)

    user = User.query.filter_by(iam_user_id=iam_user_id).first()
    if user is None:
        user = User.query.filter_by(keycloak_subject=subject).first()
    if user is None:
        collision = User.query.filter(or_(User.username == username, User.email == email)).first()
        if collision is not None:
            raise BusinessError(
                ErrorCode.IDENTITY_CONFLICT,
                "用户名或邮箱已属于尚未迁移的本地账号",
            )
    if user is not None and user.iam_user_id not in {None, iam_user_id}:
        raise BusinessError(ErrorCode.IDENTITY_CONFLICT, "本地用户已绑定其他 IAM 身份")
    if user is None:
        user = User(username=username, email=email, password_hash=None)
        db.session.add(user)
    else:
        collision = User.query.filter(
            User.id != user.id,
            or_(User.username == username, User.email == email),
        ).first()
        if collision is not None:
            raise BusinessError(
                ErrorCode.IDENTITY_CONFLICT,
                "IAM 用户资料与其他本地账号冲突",
            )

    user.iam_user_id = iam_user_id
    user.keycloak_subject = subject
    user.username = username
    user.email = email
    user.is_active = True
    user.is_superuser = is_superuser
    user.last_synced_at = now
    db.session.flush()
    return user


def _project_tenant_membership(user: User, payload: dict):
    iam_tenant_id = _required(payload, "id")
    iam_role = _required(payload, "role")
    local_role_name = IAM_ROLE_TO_LOCAL_ROLE.get(iam_role)
    if local_role_name is None:
        raise BusinessError(ErrorCode.INVALID_ROLE, "IAM 返回了不支持的固定角色")

    tenant = Tenant.query.filter_by(iam_tenant_id=iam_tenant_id).first()
    if tenant is None and payload.get("keycloak_org_id"):
        tenant = Tenant.query.filter_by(keycloak_org_id=payload["keycloak_org_id"]).first()
    if tenant is not None and tenant.iam_tenant_id not in {None, iam_tenant_id}:
        raise BusinessError(ErrorCode.IDENTITY_CONFLICT, "本地租户已绑定其他 IAM 身份")
    if tenant is None:
        tenant = Tenant(slug=_available_slug(payload), name=payload["name"])
        db.session.add(tenant)

    keycloak_org_id = payload.get("keycloak_org_id")
    if keycloak_org_id:
        collision = Tenant.query.filter(
            Tenant.id != tenant.id,
            Tenant.keycloak_org_id == keycloak_org_id,
        ).first()
        if collision is not None:
            raise BusinessError(ErrorCode.IDENTITY_CONFLICT, "Keycloak 租户映射发生冲突")

    now = datetime.now(timezone.utc)
    tenant.iam_tenant_id = iam_tenant_id
    tenant.keycloak_org_id = keycloak_org_id
    tenant.name = payload["name"]
    tenant.tenant_type = payload.get("tenant_type", "enterprise")
    tenant.lifecycle_status = payload.get("lifecycle_status", "active")
    tenant.is_active = bool(payload.get("enabled", True)) and tenant.lifecycle_status == "active"
    tenant.is_protected = bool(payload.get("protected", False))
    tenant.last_synced_at = now
    db.session.flush()

    role = Role.query.filter_by(tenant_id=None, name=local_role_name).first()
    if role is None:
        raise BusinessError(ErrorCode.INTERNAL_ERROR, f"缺少本地固定角色 {local_role_name}")
    membership = TenantMembership.query.filter_by(user_id=user.id, tenant_id=tenant.id).first()
    if membership is None:
        membership = TenantMembership(user_id=user.id, tenant_id=tenant.id, role_id=role.id)
        db.session.add(membership)
    membership.role_id = role.id
    membership.iam_role = iam_role
    membership.is_active = tenant.is_active
    membership.is_owner = tenant.tenant_type == "personal"
    membership.sync_version = int(now.timestamp() * 1000)
    membership.last_synced_at = now
    db.session.flush()
    return tenant, membership


def _select_tenant(user: User, tenants: list[dict]) -> dict:
    if user.last_iam_tenant_id:
        for tenant in tenants:
            if tenant["id"] == user.last_iam_tenant_id:
                return tenant
    for tenant in tenants:
        if tenant.get("tenant_type") == "personal":
            return tenant
    return tenants[0]


def _active_tenants(tenants: list[dict]) -> list[dict]:
    return [
        tenant for tenant in tenants
        if tenant.get("enabled", True) and tenant.get("lifecycle_status", "active") == "active"
        and tenant.get("role") in IAM_ROLE_TO_LOCAL_ROLE
    ]


def _available_slug(payload: dict) -> str:
    base = (payload.get("alias") or f"iam-{payload['id']}")[:50]
    existing = Tenant.query.filter_by(slug=base).first()
    if existing is None or existing.iam_tenant_id == payload["id"]:
        return base
    suffix = payload["id"].replace("-", "")[:8]
    return f"{base[:41]}-{suffix}"


def _required(payload: dict, key: str) -> str:
    value = payload.get(key)
    if value is None or str(value).strip() == "":
        raise BusinessError(ErrorCode.INTERNAL_ERROR, f"IAM 响应缺少 {key}")
    return str(value)
