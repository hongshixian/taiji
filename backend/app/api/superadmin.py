"""超级管理员接口 — 仅 is_superuser=true 用户可访问

提供跨租户的平台运维能力：
- 管理 tenants 表（增删改查）
- 跨租户查看所有用户 / 任务
- 切换"当前操作的租户"（签发 tenant_id claim 指向目标租户的新 access token）
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

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
@jwt_required()
@superuser_required
def get_tenants():
    return ok(list_tenants())


@superadmin_bp.route("/tenants/<int:tenant_id>", methods=["GET"])
@jwt_required()
@superuser_required
def get_one_tenant(tenant_id):
    return ok(tenant_to_dict(get_tenant(tenant_id), with_stats=True))


@superadmin_bp.route("/tenants", methods=["POST"])
@jwt_required()
@superuser_required
def add_tenant():
    data = request.get_json() or {}
    slug = (data.get("slug") or "").strip()
    name = (data.get("name") or "").strip()
    plan = data.get("plan", "free")

    if not slug or not name:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "slug 和 name 不能为空")
    tenant = create_tenant(slug, name, plan)
    add_user_membership(int(get_jwt_identity()), tenant.id, "admin", is_owner=True)
    return created(tenant_to_dict(tenant))


@superadmin_bp.route("/tenants/<int:tenant_id>", methods=["PUT"])
@jwt_required()
@superuser_required
def edit_tenant(tenant_id):
    data = request.get_json() or {}
    if not data:
        raise BusinessError(ErrorCode.EMPTY_BODY)
    tenant = update_tenant(tenant_id, data)
    return ok(tenant_to_dict(tenant))


@superadmin_bp.route("/tenants/<int:tenant_id>", methods=["DELETE"])
@jwt_required()
@superuser_required
def remove_tenant(tenant_id):
    delete_tenant(tenant_id)
    return ok(message="租户已删除")


@superadmin_bp.route("/switch-tenant", methods=["POST"])
@jwt_required()
@superuser_required
def switch_tenant():
    """切换当前会话的操作租户。超管也必须拥有对应租户 membership。"""
    data = request.get_json() or {}
    tenant_id = data.get("tenant_id")
    if tenant_id is None:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "tenant_id 不能为空")
    result = switch_user_tenant(int(get_jwt_identity()), tenant_id)
    return ok(result, message="租户已切换")


@superadmin_bp.route("/settings", methods=["GET"])
@jwt_required()
@superuser_required
def get_system_settings():
    return ok(list_settings())


@superadmin_bp.route("/settings", methods=["PUT"])
@jwt_required()
@superuser_required
def edit_system_settings():
    data = request.get_json() or {}
    if not data:
        raise BusinessError(ErrorCode.EMPTY_BODY)
    return ok(update_settings(data), message="系统设置已保存")


@superadmin_bp.route("/roles", methods=["GET"])
@jwt_required()
@superuser_required
def get_roles_for_superadmin():
    from app.services.role_service import list_roles
    return ok(list_roles())


@superadmin_bp.route("/superusers", methods=["GET"])
@jwt_required()
@superuser_required
def get_superusers():
    return ok(list_superusers())


@superadmin_bp.route("/superusers", methods=["POST"])
@jwt_required()
@superuser_required
def add_one_superuser():
    data = request.get_json() or {}
    identifier = (data.get("identifier") or "").strip()
    if not identifier:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "用户名或邮箱不能为空")
    user = add_superuser(identifier)
    from app.services.auth_service import user_to_dict
    return ok(user_to_dict(user, include_memberships=True), message="已添加超级管理员")


@superadmin_bp.route("/superusers/<int:user_id>", methods=["DELETE"])
@jwt_required()
@superuser_required
def remove_one_superuser(user_id):
    remove_superuser(user_id, int(get_jwt_identity()))
    return ok(message="已移除超级管理员")


@superadmin_bp.route("/tenants/<int:tenant_id>/members", methods=["GET"])
@jwt_required()
@superuser_required
def get_tenant_members(tenant_id):
    return ok(list_tenant_members(tenant_id))


@superadmin_bp.route("/tenants/<int:tenant_id>/members", methods=["POST"])
@jwt_required()
@superuser_required
def add_one_tenant_member(tenant_id):
    data = request.get_json() or {}
    identifier = (data.get("identifier") or "").strip()
    role = data.get("role") or "user"

    if not identifier:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "用户名或邮箱不能为空")
    user = add_tenant_member(tenant_id, identifier, role)
    from app.services.auth_service import get_current_membership, user_to_dict
    membership = get_current_membership(user.id, tenant_id)
    return ok(user_to_dict(user, membership), message="已添加租户成员")


@superadmin_bp.route("/tenants/<int:tenant_id>/members/<int:user_id>", methods=["DELETE"])
@jwt_required()
@superuser_required
def remove_one_tenant_member(tenant_id, user_id):
    remove_tenant_member(tenant_id, user_id)
    return ok(message="已移除租户成员")
