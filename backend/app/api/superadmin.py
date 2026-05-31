"""超级管理员接口 — 仅 is_superuser=true 用户可访问

提供跨租户的平台运维能力：
- 管理 tenants 表（增删改查）
- 跨租户查看所有用户 / 任务
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.services.tenant_service import (
    list_tenants, get_tenant, create_tenant, update_tenant, delete_tenant,
    tenant_to_dict,
)
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
