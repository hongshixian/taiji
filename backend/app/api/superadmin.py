"""超级管理员接口 — 仅 is_superuser=true 用户可访问

提供跨租户的平台运维能力：
- 管理 tenants 表（增删改查）
- 跨租户查看所有用户 / 任务
- 切换"当前操作的租户"（签发 tenant_id claim 指向目标租户的新 access token）
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token

from app import db
from app.models.user import User
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


@superadmin_bp.route("/switch-tenant", methods=["POST"])
@jwt_required()
@superuser_required
def switch_tenant():
    """切换当前会话的"操作租户" — 签发携带目标 tenant_id claim 的新 access token

    JWT identity (用户自己) 不变；只是 tenant_id claim 改成目标租户 id，
    后续请求 before_request 钩子会把 g.tenant_id 装成目标值。
    is_superuser=true 仍然成立，所以全局 tenant filter 依旧 bypass，
    用户在 UI 上看到的就是目标租户的数据。
    """
    data = request.get_json() or {}
    tenant_id = data.get("tenant_id")
    if tenant_id is None:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "tenant_id 不能为空")

    tenant = get_tenant(tenant_id)   # 不存在时 raise TENANT_NOT_FOUND

    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        raise BusinessError(ErrorCode.USER_NOT_FOUND)

    claims = {
        "perms": user.permissions,
        "tenant_id": tenant.id,                # ★ 目标租户，非用户自己的 tenant
        "is_superuser": user.is_superuser,
    }
    access_token = create_access_token(identity=str(user.id), additional_claims=claims)
    return ok({
        "access_token": access_token,
        "tenant": tenant_to_dict(tenant),
    }, message=f"已切换到租户 {tenant.name}")
