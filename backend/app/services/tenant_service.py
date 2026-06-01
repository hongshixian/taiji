"""租户管理业务逻辑（仅 superuser 可调）"""

from app import db
from app.models.tenant import Tenant
from app.models.tenant_membership import TenantMembership
from app.models.task import Task
from app.utils.errors import BusinessError, ErrorCode


def tenant_to_dict(tenant: Tenant, with_stats: bool = False) -> dict:
    """转 dict；with_stats=True 时附带用户数 / 任务数"""
    d = {
        "id": tenant.id,
        "slug": tenant.slug,
        "name": tenant.name,
        "is_active": tenant.is_active,
        "is_system": tenant.is_system,
        "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
    }
    if with_stats:
        from app.utils.decorators import bypass_tenant_filter
        with bypass_tenant_filter():
            d["user_count"] = TenantMembership.query.filter_by(tenant_id=tenant.id).count()
            d["task_count"] = Task.query.filter_by(tenant_id=tenant.id).count()
    return d


def list_tenants() -> list[dict]:
    """列出所有租户（含统计）"""
    return [tenant_to_dict(t, with_stats=True)
            for t in Tenant.query.order_by(Tenant.id).all()]


def get_tenant(tenant_id: int) -> Tenant:
    t = db.session.get(Tenant, tenant_id)
    if not t:
        raise BusinessError(ErrorCode.TENANT_NOT_FOUND)
    return t


def create_tenant(slug: str, name: str) -> Tenant:
    if Tenant.query.filter_by(slug=slug).first():
        raise BusinessError(ErrorCode.TENANT_EXISTS)
    tenant = Tenant(slug=slug, name=name, is_system=False)
    db.session.add(tenant)
    db.session.commit()
    return tenant


def update_tenant(tenant_id: int, data: dict) -> Tenant:
    tenant = get_tenant(tenant_id)
    if tenant.is_system and "slug" in data and data["slug"] != tenant.slug:
        raise BusinessError(ErrorCode.SYSTEM_TENANT_PROTECTED, "系统租户 slug 不可改")

    if "slug" in data and data["slug"] != tenant.slug:
        if Tenant.query.filter_by(slug=data["slug"]).first():
            raise BusinessError(ErrorCode.TENANT_EXISTS)
        tenant.slug = data["slug"]
    if "name" in data:
        tenant.name = data["name"]
    if "is_active" in data:
        tenant.is_active = data["is_active"]

    db.session.commit()
    return tenant


def delete_tenant(tenant_id: int):
    tenant = get_tenant(tenant_id)
    if tenant.is_system:
        raise BusinessError(ErrorCode.SYSTEM_TENANT_PROTECTED, "系统租户不可删除")

    # 检查租户内是否还有用户或任务
    from app.utils.decorators import bypass_tenant_filter
    with bypass_tenant_filter():
        if TenantMembership.query.filter_by(tenant_id=tenant_id).first():
            raise BusinessError(ErrorCode.TENANT_IN_USE, "租户内仍有用户")
        if Task.query.filter_by(tenant_id=tenant_id).first():
            raise BusinessError(ErrorCode.TENANT_IN_USE, "租户内仍有任务")

    db.session.delete(tenant)
    db.session.commit()
