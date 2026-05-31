"""角色管理业务逻辑"""

from app import db
from app.models.role import Role, Permission
from app.permissions import PERMISSIONS_REGISTRY
from app.utils.errors import BusinessError, ErrorCode


def role_to_dict(role: Role) -> dict:
    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "is_system": role.is_system,
        "permissions": role.permission_codes,
        "created_at": role.created_at.isoformat() if role.created_at else None,
        "updated_at": role.updated_at.isoformat() if role.updated_at else None,
    }


def list_roles() -> list[dict]:
    return [role_to_dict(r) for r in Role.query.order_by(Role.id).all()]


def list_permissions() -> list[dict]:
    """所有系统权限码（不可运行时增删）"""
    return [{"code": code, "description": desc}
            for code, desc in PERMISSIONS_REGISTRY.items()]


def get_role(role_id: int) -> Role:
    role = db.session.get(Role, role_id)
    if not role:
        raise BusinessError(ErrorCode.ROLE_NOT_FOUND)
    return role


def create_role(name: str, description: str, permission_codes: list[str]) -> Role:
    if Role.query.filter_by(name=name).first():
        raise BusinessError(ErrorCode.ROLE_EXISTS)
    role = Role(name=name, description=description, is_system=False)
    _set_role_permissions(role, permission_codes)
    db.session.add(role)
    db.session.commit()
    return role


def update_role(role_id: int, data: dict) -> Role:
    role = get_role(role_id)
    if role.is_system and "name" in data and data["name"] != role.name:
        raise BusinessError(ErrorCode.SYSTEM_ROLE_PROTECTED, "系统角色名不可修改")

    if "name" in data and data["name"] != role.name:
        if Role.query.filter_by(name=data["name"]).first():
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

    # 检查是否还有用户绑定该角色
    from app.models.user import User
    in_use = User.query.filter_by(role_id=role_id).first()
    if in_use:
        raise BusinessError(ErrorCode.ROLE_IN_USE,
                            f"角色仍在使用中（用户 {in_use.username} 等）")

    db.session.delete(role)
    db.session.commit()


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
    from app.services.auth_service import _revoke_marker

    marker = _revoke_marker()
    User.query.filter_by(role_id=role_id).update({"tokens_revoked_at": marker})
    db.session.commit()
