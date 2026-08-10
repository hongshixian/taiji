"""超级管理员接口 — 仅 is_superuser=true 用户可访问

提供跨租户的平台运维能力：
- 管理 tenants 表（增删改查）
- 跨租户查看所有用户 / 任务
- 切换"当前操作的租户"（签发 tenant_id claim 指向目标租户的新 access token）
"""

from flask import Blueprint, request
from app.auth_context import current_user_id, login_required, oidc_mode

from app.services.tenant_service import (
    list_tenants, get_tenant, create_tenant, update_tenant, delete_tenant,
    tenant_to_dict,
)
from app.services.auth_service import (
    add_user_membership,
    add_superuser,
    add_tenant_member,
    list_superusers,
    list_tenant_members,
    remove_superuser,
    remove_tenant_member,
    switch_tenant as switch_user_tenant,
)
from app.services.system_setting_service import list_settings, update_settings
from app.utils.decorators import superuser_required
from app.utils.response import ok, created
from app.utils.errors import BusinessError, ErrorCode

superadmin_bp = Blueprint("superadmin", __name__)


@superadmin_bp.route("/tenants", methods=["GET"])
@login_required()
@superuser_required
def get_tenants():
    return ok(list_tenants())


@superadmin_bp.route("/tenants/<int:tenant_id>", methods=["GET"])
@login_required()
@superuser_required
def get_one_tenant(tenant_id):
    return ok(tenant_to_dict(get_tenant(tenant_id), with_stats=True))


@superadmin_bp.route("/tenants", methods=["POST"])
@login_required()
@superuser_required
def add_tenant():
    data = request.get_json() or {}
    if oidc_mode():
        name = (data.get("name") or "").strip()
        initial_admin = (data.get("initial_admin") or data.get("initialAdmin") or "").strip()
        if not name or not initial_admin:
            raise BusinessError(ErrorCode.VALIDATION_ERROR, "租户名称和初始管理员不能为空")
        from app.services.iam_management_service import create_enterprise_tenant
        tenant = create_enterprise_tenant(
            name,
            initial_admin,
            request.headers.get("Idempotency-Key"),
        )
        return created(tenant_to_dict(tenant))

    slug = (data.get("slug") or "").strip()
    name = (data.get("name") or "").strip()

    if not slug or not name:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "slug 和 name 不能为空")
    tenant = create_tenant(slug, name)
    add_user_membership(current_user_id(), tenant.id, "admin", is_owner=True)
    return created(tenant_to_dict(tenant))


@superadmin_bp.route("/tenants/<int:tenant_id>", methods=["PUT"])
@login_required()
@superuser_required
def edit_tenant(tenant_id):
    data = request.get_json() or {}
    if not data:
        raise BusinessError(ErrorCode.EMPTY_BODY)
    if oidc_mode():
        if "slug" in data:
            raise BusinessError(ErrorCode.VALIDATION_ERROR, "IAM 租户 slug 不可编辑")
        from app.services.iam_management_service import update_enterprise_tenant
        return ok(tenant_to_dict(update_enterprise_tenant(tenant_id, data)))
    tenant = update_tenant(tenant_id, data)
    return ok(tenant_to_dict(tenant))


@superadmin_bp.route("/tenants/<int:tenant_id>", methods=["DELETE"])
@login_required()
@superuser_required
def remove_tenant(tenant_id):
    if oidc_mode():
        from app.services.iam_management_service import update_enterprise_tenant
        update_enterprise_tenant(tenant_id, {"enabled": False})
        return ok(message="租户已停用")
    delete_tenant(tenant_id)
    return ok(message="租户已删除")


@superadmin_bp.route("/switch-tenant", methods=["POST"])
@login_required()
@superuser_required
def switch_tenant():
    """切换当前会话的操作租户。超管也必须拥有对应租户 membership。"""
    data = request.get_json() or {}
    tenant_id = data.get("tenant_id")
    if tenant_id is None:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "tenant_id 不能为空")
    if oidc_mode():
        tenant = get_tenant(int(tenant_id))
        if not tenant.iam_tenant_id:
            raise BusinessError(ErrorCode.IDENTITY_CONFLICT, "本地租户尚未绑定 IAM")
        from app.services.oidc_session_service import refresh_identity, switch_to_tenant
        tenants = refresh_identity(force=True)
        selected = next((item for item in tenants if item["id"] == tenant.iam_tenant_id), None)
        if selected is None:
            raise BusinessError(ErrorCode.TENANT_NOT_FOUND, "当前用户不是该租户成员")
        projected, membership = switch_to_tenant(selected, tenants=tenants)
        return ok({
            "tenant": dict(selected, local_id=projected.id),
            "role": membership.iam_role,
            "permissions": membership.permission_codes,
        }, message="租户已切换")
    result = switch_user_tenant(current_user_id(), tenant_id)
    return ok(result, message="租户已切换")


@superadmin_bp.route("/settings", methods=["GET"])
@login_required()
@superuser_required
def get_system_settings():
    return ok(list_settings())


@superadmin_bp.route("/settings", methods=["PUT"])
@login_required()
@superuser_required
def edit_system_settings():
    data = request.get_json() or {}
    if not data:
        raise BusinessError(ErrorCode.EMPTY_BODY)
    return ok(update_settings(data), message="系统设置已保存")


@superadmin_bp.route("/roles", methods=["GET"])
@login_required()
@superuser_required
def get_roles_for_superadmin():
    if oidc_mode():
        from app.api.admin import _fixed_iam_roles
        return ok(_fixed_iam_roles())
    from app.services.role_service import list_roles
    tenant_id = request.args.get("tenant_id", type=int)
    return ok(list_roles(tenant_id=tenant_id))


@superadmin_bp.route("/superusers", methods=["GET"])
@login_required()
@superuser_required
def get_superusers():
    if oidc_mode():
        from app.services.iam_management_service import list_platform_admins
        return ok(list_platform_admins())
    return ok(list_superusers())


@superadmin_bp.route("/superusers", methods=["POST"])
@login_required()
@superuser_required
def add_one_superuser():
    data = request.get_json() or {}
    identifier = (data.get("identifier") or "").strip()
    if not identifier:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "用户名或邮箱不能为空")
    if oidc_mode():
        from app.services.iam_management_service import grant_platform_admin
        return ok(grant_platform_admin(identifier), message="已添加平台管理员")
    user = add_superuser(identifier)
    from app.services.auth_service import user_to_dict
    return ok(user_to_dict(user, include_memberships=True), message="已添加超级管理员")


@superadmin_bp.route("/superusers/<int:user_id>", methods=["DELETE"])
@login_required()
@superuser_required
def remove_one_superuser(user_id):
    if oidc_mode():
        from app.services.iam_management_service import revoke_platform_admin
        revoke_platform_admin(user_id, current_user_id())
        return ok(message="已移除平台管理员")
    remove_superuser(user_id, current_user_id())
    return ok(message="已移除超级管理员")


@superadmin_bp.route("/tenants/<int:tenant_id>/members", methods=["GET"])
@login_required()
@superuser_required
def get_tenant_members(tenant_id):
    if oidc_mode():
        from app.services.iam_management_service import list_members
        members, _total = list_members(page=1, per_page=10000, tenant_id=tenant_id)
        return ok(members)
    return ok(list_tenant_members(tenant_id))


@superadmin_bp.route("/tenants/<int:tenant_id>/members", methods=["POST"])
@login_required()
@superuser_required
def add_one_tenant_member(tenant_id):
    data = request.get_json() or {}
    identifier = (data.get("identifier") or "").strip()
    role = data.get("role") or ("member" if oidc_mode() else "user")

    if not identifier:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "用户名或邮箱不能为空")
    if oidc_mode():
        from app.services.iam_management_service import add_member
        result = add_member(identifier, role, tenant_id=tenant_id)
        if result.get("kind") == "invitation":
            return ok(result, message="邀请已发送", status=202)
        return ok(result, message="已添加租户成员")
    user = add_tenant_member(tenant_id, identifier, role)
    from app.services.auth_service import get_current_membership, user_to_dict
    membership = get_current_membership(user.id, tenant_id)
    return ok(user_to_dict(user, membership), message="已添加租户成员")


@superadmin_bp.route("/tenants/<int:tenant_id>/members/<int:user_id>", methods=["DELETE"])
@login_required()
@superuser_required
def remove_one_tenant_member(tenant_id, user_id):
    if oidc_mode():
        from app.services.iam_management_service import deactivate_member
        deactivate_member(user_id, current_user_id(), tenant_id=tenant_id)
        return ok(message="已移除租户成员")
    remove_tenant_member(tenant_id, user_id)
    return ok(message="已移除租户成员")
