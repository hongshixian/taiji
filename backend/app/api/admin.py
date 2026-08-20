"""管理员接口（需相应权限）"""

from flask import Blueprint, g, request
from app.auth_context import current_user_id, login_required, oidc_mode

from app.services.auth_service import (
    list_users,
    create_user,
    update_user,
    delete_user,
    get_user_by_id,
    user_to_dict,
    get_current_membership,
)
from app.utils.decorators import require_permission
from app.utils.roles import Role
from app import limiter
from app.utils.response import ok, created, paginated
from app.utils.errors import BusinessError, ErrorCode
from app.permissions import Permission

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/users", methods=["GET"])
@login_required()
@require_permission(Permission.MEMBER_READ)
def get_users():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    users, total = list_users(page, per_page)
    return paginated(items=users, total=total, page=page, per_page=per_page)


@admin_bp.route("/users/<int:user_id>", methods=["GET"])
@login_required()
@require_permission(Permission.MEMBER_READ)
def get_user(user_id):
    user = get_user_by_id(user_id)
    if not user:
        raise BusinessError(ErrorCode.USER_NOT_FOUND)
    return ok(user_to_dict(user, get_current_membership(user_id)))


@admin_bp.route("/users", methods=["POST"])
@login_required()
@require_permission(Permission.MEMBER_WRITE)
@limiter.limit("20 per minute")
def add_user():
    data = request.get_json()
    if not data:
        raise BusinessError(ErrorCode.EMPTY_BODY)

    if oidc_mode():
        identifier = (data.get("identifier") or "").strip()
        if not identifier:
            raise BusinessError(ErrorCode.VALIDATION_ERROR, "完整用户名或邮箱不能为空")
        from app.services.auth_service import add_tenant_member
        user = add_tenant_member(g.tenant_id, identifier, data.get("role", "member"))
        return created(user_to_dict(user, get_current_membership(user.id)), message="成员已加入")

    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    role = data.get("role", Role.USER)

    if not username or not email or not password:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "用户名、邮箱、密码不能为空")
    if len(password) < 6:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "密码至少 6 位")
    if not Role.is_valid(role):
        raise BusinessError(ErrorCode.INVALID_ROLE)

    user = create_user(username, email, password, role)
    return created(user_to_dict(user, get_current_membership(user.id)))


@admin_bp.route("/users/<int:user_id>", methods=["PUT"])
@login_required()
@require_permission(Permission.MEMBER_WRITE)
def edit_user(user_id):
    data = request.get_json()
    if not data:
        raise BusinessError(ErrorCode.EMPTY_BODY)

    if oidc_mode():
        allowed = {"role", "active", "membership_active"}
        unsupported = set(data) - allowed
        if unsupported:
            raise BusinessError(
                ErrorCode.VALIDATION_ERROR,
                "IAM 模式只允许修改成员角色和成员状态",
            )
        normalized = dict(data)
        if "active" in normalized:
            normalized["membership_active"] = normalized.pop("active")
        user = update_user(user_id, normalized)
        return ok(user_to_dict(user, get_current_membership(user_id)))

    role = data.get("role")
    if role is not None and not Role.is_valid(role):
        raise BusinessError(ErrorCode.INVALID_ROLE)

    user = update_user(user_id, data)
    return ok(user_to_dict(user, get_current_membership(user_id)))


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@login_required()
@require_permission(Permission.MEMBER_REMOVE)
def remove_user(user_id):
    if oidc_mode():
        from app.services.auth_service import remove_tenant_member
        remove_tenant_member(g.tenant_id, user_id, current_user_id())
        return ok(message="已移出租户")
    delete_user(user_id, current_user_id())
    return ok(message="已删除")


# ─── 角色管理 ──────────────────────────────────────

@admin_bp.route("/roles", methods=["GET"])
@login_required()
@require_permission(Permission.MEMBER_READ)
def get_roles():
    if oidc_mode():
        return ok(_fixed_membership_roles())
    from app.services.role_service import list_roles
    return ok(list_roles())


@admin_bp.route("/roles/permissions", methods=["GET"])
@login_required()
@require_permission(Permission.MEMBER_READ)
def get_all_permissions():
    """列出系统所有权限码（用于角色编辑页面）"""
    if oidc_mode():
        from app.services.role_service import list_permissions
        return ok(list_permissions())
    from app.services.role_service import list_permissions
    return ok(list_permissions())


@admin_bp.route("/roles/<int:role_id>", methods=["GET"])
@login_required()
@require_permission(Permission.MEMBER_READ)
def get_role(role_id):
    if oidc_mode():
        role = next((item for item in _fixed_membership_roles() if item["id"] == role_id), None)
        if role is None:
            raise BusinessError(ErrorCode.ROLE_NOT_FOUND)
        return ok(role)
    from app.services.role_service import get_role as get_role_svc, role_to_dict
    return ok(role_to_dict(get_role_svc(role_id)))


@admin_bp.route("/roles", methods=["POST"])
@login_required()
@require_permission(Permission.MEMBER_WRITE)
@limiter.limit("20 per minute")
def add_role():
    if oidc_mode():
        raise BusinessError(ErrorCode.METHOD_NOT_ALLOWED, "IAM 模式使用固定角色")
    from app.services.role_service import create_role, role_to_dict
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    description = data.get("description", "")
    perms = data.get("permissions", [])

    if not name:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "角色名不能为空")
    if not isinstance(perms, list):
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "permissions 必须是数组")

    role = create_role(name, description, perms)
    return created(role_to_dict(role))


@admin_bp.route("/roles/<int:role_id>", methods=["PUT"])
@login_required()
@require_permission(Permission.MEMBER_WRITE)
def edit_role(role_id):
    if oidc_mode():
        raise BusinessError(ErrorCode.METHOD_NOT_ALLOWED, "IAM 模式使用固定角色")
    from app.services.role_service import update_role, role_to_dict
    data = request.get_json() or {}
    if not data:
        raise BusinessError(ErrorCode.EMPTY_BODY)
    role = update_role(role_id, data)
    return ok(role_to_dict(role))


@admin_bp.route("/roles/<int:role_id>", methods=["DELETE"])
@login_required()
@require_permission(Permission.MEMBER_WRITE)
def remove_role(role_id):
    if oidc_mode():
        raise BusinessError(ErrorCode.METHOD_NOT_ALLOWED, "IAM 模式使用固定角色")
    from app.services.role_service import delete_role
    delete_role(role_id)
    return ok(message="角色已删除")


def _fixed_membership_roles() -> list[dict]:
    from app.models.role import Role as RoleModel

    mapping = {"admin": "tenant_admin", "user": "member"}
    roles = RoleModel.query.filter(
        RoleModel.tenant_id.is_(None),
        RoleModel.name.in_(mapping),
    ).order_by(RoleModel.id).all()
    return [{
        "id": role.id,
        "tenant_id": None,
        "name": mapping[role.name],
        "description": role.description,
        "is_system": True,
        "scope": "system",
        "permissions": role.permission_codes,
    } for role in roles]
