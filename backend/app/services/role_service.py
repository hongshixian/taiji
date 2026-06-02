"""角色管理业务逻辑"""

from flask import g
from sqlalchemy import or_

from app import db
from app.models.role import Role, Permission
from app.permissions import SYSTEM_ROLES
from app.permissions import PERMISSIONS_REGISTRY
from app.utils.errors import BusinessError, ErrorCode


def role_to_dict(role: Role) -> dict:
    return {
        "id": role.id,
        "tenant_id": role.tenant_id,
        "name": role.name,
        "description": role.description,
        "is_system": role.is_system,
        "scope": "system" if role.tenant_id is None else "tenant",
        "permissions": role.permission_codes,
        "created_at": role.created_at.isoformat() if role.created_at else None,
        "updated_at": role.updated_at.isoformat() if role.updated_at else None,
    }


def list_roles(tenant_id: int | None = None) -> list[dict]:
    tenant_id = _resolve_tenant_id(tenant_id)
    query = _scoped_roles_query(tenant_id)
    return [role_to_dict(r) for r in query.order_by(Role.is_system.desc(), Role.id).all()]


def list_permissions() -> list[dict]:
    """所有系统权限码（不可运行时增删）"""
    return [{"code": code, "description": desc}
            for code, desc in PERMISSIONS_REGISTRY.items()]


def get_role(role_id: int, tenant_id: int | None = None) -> Role:
    tenant_id = _resolve_tenant_id(tenant_id)
    role = db.session.get(Role, role_id)
    if not role or not _role_visible_in_tenant(role, tenant_id):
        raise BusinessError(ErrorCode.ROLE_NOT_FOUND)
    return role


def create_role(name: str, description: str, permission_codes: list[str],
                tenant_id: int | None = None) -> Role:
    tenant_id = _resolve_tenant_id(tenant_id)
    if tenant_id is None:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "未指定租户")
    if _is_system_role_name(name):
        raise BusinessError(ErrorCode.ROLE_EXISTS, "角色名与系统角色冲突")
    if Role.query.filter_by(tenant_id=tenant_id, name=name).first():
        raise BusinessError(ErrorCode.ROLE_EXISTS)
    role = Role(tenant_id=tenant_id, name=name, description=description, is_system=False)
    _set_role_permissions(role, permission_codes)
    db.session.add(role)
    db.session.commit()
    return role


def update_role(role_id: int, data: dict) -> Role:
    role = get_role(role_id)
    if role.is_system:
        raise BusinessError(ErrorCode.SYSTEM_ROLE_PROTECTED, "系统角色不可修改")

    if "name" in data and data["name"] != role.name:
        if _is_system_role_name(data["name"]):
            raise BusinessError(ErrorCode.ROLE_EXISTS, "角色名与系统角色冲突")
        if Role.query.filter_by(tenant_id=role.tenant_id, name=data["name"]).first():
            raise BusinessError(ErrorCode.ROLE_EXISTS)
        role.name = data["name"]
    if "description" in data:
        role.description = data["description"]
    if "permissions" in data:
        _set_role_permissions(role, data["permissions"])

    db.session.commit()

    # 角色权限变更时，需要踢出所有该角色用户的旧 token
    if "permissions" in data:
        _revoke_users_of_role(role_id)

    return role


def delete_role(role_id: int):
    role = get_role(role_id)
    if role.is_system:
        raise BusinessError(ErrorCode.SYSTEM_ROLE_PROTECTED, "系统角色不可删除")

    # 检查是否还有租户成员绑定该角色
    from app.models.tenant_membership import TenantMembership
    in_use = TenantMembership.query.filter_by(role_id=role_id).first()
    if in_use:
        raise BusinessError(ErrorCode.ROLE_IN_USE,
                            f"角色仍在使用中（成员身份 #{in_use.id} 等）")

    db.session.delete(role)
    db.session.commit()


def find_role_by_name(name: str, tenant_id: int | None = None) -> Role | None:
    """按租户作用域解析角色名：租户自定义角色优先，系统角色兜底。"""
    if not name:
        return None
    tenant_id = _resolve_tenant_id(tenant_id)
    if tenant_id is not None:
        role = Role.query.filter_by(tenant_id=tenant_id, name=name).first()
        if role:
            return role
    return Role.query.filter_by(tenant_id=None, name=name).first()


# ─── 内部工具 ────────────────────────────────

def _set_role_permissions(role: Role, codes: list[str]):
    """重置角色权限列表"""
    if codes is None:
        return
    perms = Permission.query.filter(Permission.code.in_(codes)).all()
    found = {p.code for p in perms}
    missing = set(codes) - found
    if missing:
        raise BusinessError(
            ErrorCode.VALIDATION_ERROR,
            f"未知权限码: {', '.join(sorted(missing))}",
        )
    role.permissions = perms


def _revoke_users_of_role(role_id: int):
    """角色权限变更后，把使用该角色的所有用户的 tokens_revoked_at 设为下一秒"""
    from app.models.user import User
    from app.models.tenant_membership import TenantMembership
    from app.services.auth_service import _revoke_marker

    marker = _revoke_marker()
    user_ids = [
        row.user_id for row in db.session.query(TenantMembership.user_id)
        .filter_by(role_id=role_id)
        .distinct()
        .all()
    ]
    if user_ids:
        User.query.filter(User.id.in_(user_ids)).update(
            {"tokens_revoked_at": marker},
            synchronize_session=False,
        )
    db.session.commit()


def _resolve_tenant_id(tenant_id: int | None = None) -> int | None:
    return tenant_id if tenant_id is not None else getattr(g, "tenant_id", None)


def _scoped_roles_query(tenant_id: int | None):
    if tenant_id is None:
        return Role.query.filter(Role.tenant_id.is_(None))
    return Role.query.filter(or_(Role.tenant_id.is_(None), Role.tenant_id == tenant_id))


def _role_visible_in_tenant(role: Role, tenant_id: int | None) -> bool:
    return role.tenant_id is None or (tenant_id is not None and role.tenant_id == tenant_id)


def _is_system_role_name(name: str) -> bool:
    return name in SYSTEM_ROLES
