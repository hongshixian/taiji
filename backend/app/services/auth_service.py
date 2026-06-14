"""认证与租户成员业务逻辑"""

from datetime import datetime, timedelta, timezone

from flask import g
from flask_jwt_extended import create_access_token, create_refresh_token
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.models.tenant import GUEST_TENANT_SLUG, Tenant
from app.models.tenant_membership import TenantMembership
from app.models.user import User
from app.utils.decorators import bypass_tenant_filter
from app.utils.errors import BusinessError, ErrorCode


def _revoke_marker() -> datetime:
    """生成 tokens_revoked_at 时间戳：向上取整到下一秒。"""
    now = datetime.now(timezone.utc)
    return now.replace(microsecond=0) + timedelta(seconds=1)


def membership_to_dict(membership: TenantMembership) -> dict:
    tenant = membership.tenant
    role = membership.role
    return {
        "id": membership.id,
        "tenant_id": membership.tenant_id,
        "tenant_slug": tenant.slug if tenant else None,
        "tenant_name": tenant.name if tenant else None,
        "role_id": membership.role_id,
        "role": role.name if role else None,
        "role_name": role.name if role else None,
        "permissions": membership.permission_codes,
        "is_active": membership.is_active,
        "is_owner": membership.is_owner,
        "created_at": membership.created_at.isoformat() if membership.created_at else None,
    }


def user_to_dict(user: User, membership: TenantMembership | None = None,
                 include_memberships: bool = False) -> dict:
    data = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }
    if membership:
        m = membership_to_dict(membership)
        data.update({
            "membership_id": m["id"],
            "role": m["role"],
            "role_id": m["role_id"],
            "role_name": m["role_name"],
            "permissions": m["permissions"],
            "membership_active": m["is_active"],
            "current_tenant": {
                "id": m["tenant_id"],
                "slug": m["tenant_slug"],
                "name": m["tenant_name"],
            },
        })
    else:
        data.update({
            "membership_id": None,
            "role": None,
            "role_id": None,
            "role_name": None,
            "permissions": [],
            "membership_active": None,
            "current_tenant": None,
        })
    if include_memberships:
        with bypass_tenant_filter():
            data["memberships"] = [
                membership_to_dict(m) for m in _list_user_memberships(user.id)
            ]
    return data


def register_user(username: str, email: str, password: str,
                  tenant_slug: str | None = None) -> User:
    """注册全局用户，并自动加入系统设置指定的默认租户。"""
    with bypass_tenant_filter():
        if tenant_slug is None:
            from app.services.system_setting_service import get_default_registration_tenant_slug
            tenant_slug = get_default_registration_tenant_slug()
        tenant = Tenant.query.filter_by(slug=tenant_slug).first()
        if not tenant:
            raise BusinessError(ErrorCode.TENANT_NOT_FOUND)
        if not tenant.is_active:
            raise BusinessError(ErrorCode.AUTH_DISABLED, "租户已禁用")
        if User.query.filter_by(username=username).first():
            raise BusinessError(ErrorCode.USER_EXISTS)
        if User.query.filter_by(email=email).first():
            raise BusinessError(ErrorCode.EMAIL_EXISTS)

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
        )
        db.session.add(user)
        db.session.flush()
        _add_membership(user.id, tenant.id, "user")
        db.session.commit()
        return user


def login_user(username: str, password: str) -> dict:
    """登录全局用户，并进入第一个可用租户身份。"""
    with bypass_tenant_filter():
        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password_hash, password):
            raise BusinessError(ErrorCode.INVALID_CREDENTIAL)
        if not user.is_active:
            raise BusinessError(ErrorCode.ACCOUNT_DISABLED)

        membership = _select_login_membership(user.id)
        claims = _claims_for_membership(user, membership)
        access_token = create_access_token(identity=str(user.id), additional_claims=claims)
        refresh_token = create_refresh_token(identity=str(user.id), additional_claims=claims)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user_to_dict(user, membership, include_memberships=True),
        }


def refresh_access_token(user_id: int, tenant_id: int | None) -> str:
    with bypass_tenant_filter():
        user = db.session.get(User, user_id)
        if not user or not user.is_active:
            raise BusinessError(ErrorCode.ACCOUNT_DISABLED)
        membership = _membership_for_tenant(user, tenant_id)
        claims = _claims_for_membership(user, membership)
        return create_access_token(identity=str(user.id), additional_claims=claims)


def switch_tenant(user_id: int, tenant_id: int) -> dict:
    """切换当前操作租户。普通用户必须有 active membership。"""
    with bypass_tenant_filter():
        user = db.session.get(User, user_id)
        if not user or not user.is_active:
            raise BusinessError(ErrorCode.ACCOUNT_DISABLED)
        membership = _membership_for_tenant(user, tenant_id)
        claims = _claims_for_membership(user, membership)
        access_token = create_access_token(identity=str(user.id), additional_claims=claims)
        return {
            "access_token": access_token,
            "tenant": membership_to_dict(membership),
        }


def get_user_by_id(user_id: int) -> User | None:
    return db.session.get(User, user_id)


def get_current_membership(user_id: int, tenant_id: int | None = None) -> TenantMembership:
    tenant_id = tenant_id if tenant_id is not None else getattr(g, "tenant_id", None)
    with bypass_tenant_filter():
        user = db.session.get(User, user_id)
        if not user:
            raise BusinessError(ErrorCode.USER_NOT_FOUND)
        return _membership_for_tenant(user, tenant_id)


def list_current_user_memberships(user_id: int) -> list[dict]:
    with bypass_tenant_filter():
        return [membership_to_dict(m) for m in _list_user_memberships(user_id)]


def add_user_membership(user_id: int, tenant_id: int, role: str = "user",
                        is_owner: bool = False) -> TenantMembership:
    """给已有全局用户添加租户成员身份。"""
    with bypass_tenant_filter():
        user = db.session.get(User, user_id)
        tenant = db.session.get(Tenant, tenant_id)
        if not user:
            raise BusinessError(ErrorCode.USER_NOT_FOUND)
        if not tenant:
            raise BusinessError(ErrorCode.TENANT_NOT_FOUND)
        existing = TenantMembership.query.filter_by(
            user_id=user_id, tenant_id=tenant_id,
        ).first()
        if existing:
            return existing
        membership = _add_membership(user_id, tenant_id, role, is_owner=is_owner)
        db.session.flush()
        from app.services.audit_log_service import record_audit_log
        record_audit_log(
            action="tenant_member.add",
            resource_type="tenant_member",
            resource_id=membership.id,
            resource_name=user.username,
            tenant_id=tenant_id,
            after_data=_membership_audit_snapshot(membership),
        )
        db.session.commit()
        return membership


def list_superusers() -> list[dict]:
    with bypass_tenant_filter():
        users = User.query.filter_by(is_superuser=True).order_by(User.id).all()
        return [user_to_dict(u, include_memberships=True) for u in users]


def add_superuser(identifier: str) -> User:
    with bypass_tenant_filter():
        user = _find_user(identifier)
        if not user:
            raise BusinessError(ErrorCode.USER_NOT_FOUND)
        if not user.is_superuser:
            user.is_superuser = True
            user.tokens_revoked_at = _revoke_marker()
            from app.services.audit_log_service import record_audit_log
            record_audit_log(
                action="superuser.grant",
                resource_type="user",
                resource_id=user.id,
                resource_name=user.username,
                tenant_id=None,
                after_data=_user_audit_snapshot(user),
            )
            db.session.commit()
        return user


def remove_superuser(user_id: int, current_user_id: int) -> User:
    if user_id == current_user_id:
        raise BusinessError(ErrorCode.CANNOT_DELETE_SELF, "不能移除自己的超级管理员权限")
    with bypass_tenant_filter():
        user = db.session.get(User, user_id)
        if not user:
            raise BusinessError(ErrorCode.USER_NOT_FOUND)
        before = _user_audit_snapshot(user)
        user.is_superuser = False
        user.tokens_revoked_at = _revoke_marker()
        from app.services.audit_log_service import record_audit_log
        record_audit_log(
            action="superuser.revoke",
            resource_type="user",
            resource_id=user.id,
            resource_name=user.username,
            tenant_id=None,
            before_data=before,
            after_data=_user_audit_snapshot(user),
        )
        db.session.commit()
        return user


def list_tenant_members(tenant_id: int) -> list[dict]:
    with bypass_tenant_filter():
        if not db.session.get(Tenant, tenant_id):
            raise BusinessError(ErrorCode.TENANT_NOT_FOUND)
        memberships = (
            TenantMembership.query
            .filter_by(tenant_id=tenant_id)
            .order_by(TenantMembership.created_at.desc())
            .all()
        )
        return [user_to_dict(m.user, m) for m in memberships]


def add_tenant_member(tenant_id: int, identifier: str, role: str = "user") -> User:
    """超级管理员向任意租户添加已有全局用户为成员。"""
    with bypass_tenant_filter():
        if not db.session.get(Tenant, tenant_id):
            raise BusinessError(ErrorCode.TENANT_NOT_FOUND)
        user = _find_user(identifier)
        if not user:
            raise BusinessError(ErrorCode.USER_NOT_FOUND)
        if TenantMembership.query.filter_by(
            tenant_id=tenant_id, user_id=user.id,
        ).first():
            raise BusinessError(ErrorCode.USER_EXISTS, "该用户已是该租户成员")
        membership = _add_membership(user.id, tenant_id, role)
        user.tokens_revoked_at = _revoke_marker()
        db.session.flush()
        from app.services.audit_log_service import record_audit_log
        record_audit_log(
            action="tenant_member.add",
            resource_type="tenant_member",
            resource_id=membership.id,
            resource_name=user.username,
            tenant_id=tenant_id,
            after_data=_membership_audit_snapshot(membership),
        )
        db.session.commit()
        return user


def remove_tenant_member(tenant_id: int, user_id: int) -> User:
    with bypass_tenant_filter():
        user = db.session.get(User, user_id)
        if not user:
            raise BusinessError(ErrorCode.USER_NOT_FOUND)
        membership = TenantMembership.query.filter_by(
            tenant_id=tenant_id,
            user_id=user_id,
        ).first()
        if not membership:
            raise BusinessError(ErrorCode.USER_NOT_FOUND)
        before = _membership_audit_snapshot(membership)
        db.session.delete(membership)
        user.tokens_revoked_at = _revoke_marker()
        from app.services.audit_log_service import record_audit_log
        record_audit_log(
            action="tenant_member.remove",
            resource_type="tenant_member",
            resource_id=membership.id,
            resource_name=user.username,
            tenant_id=tenant_id,
            before_data=before,
        )
        db.session.commit()
        return user


def list_users(page: int, per_page: int) -> tuple[list, int]:
    """分页查询当前租户成员。"""
    pagination = (
        TenantMembership.query
        .order_by(TenantMembership.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    return [user_to_dict(m.user, m) for m in pagination.items], pagination.total


def create_user(username: str, email: str, password: str | None, role: str,
                tenant_id: int | None = None) -> User:
    """在指定租户创建成员；用户为全局唯一。"""
    if tenant_id is None:
        tenant_id = getattr(g, "tenant_id", None)
    if tenant_id is None:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "未指定租户")

    with bypass_tenant_filter():
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            raise BusinessError(ErrorCode.TENANT_NOT_FOUND)
        if not tenant.is_active:
            raise BusinessError(ErrorCode.AUTH_DISABLED, "租户已禁用")

        by_username = User.query.filter_by(username=username).first()
        by_email = User.query.filter_by(email=email).first()
        if by_username and by_email and by_username.id != by_email.id:
            raise BusinessError(ErrorCode.VALIDATION_ERROR, "用户名与邮箱属于不同用户")

        user = by_username or by_email
        if user:
            if TenantMembership.query.filter_by(user_id=user.id, tenant_id=tenant_id).first():
                raise BusinessError(ErrorCode.USER_EXISTS, "该用户已是当前租户成员")
        else:
            if not password:
                raise BusinessError(ErrorCode.VALIDATION_ERROR, "新用户密码不能为空")
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
            )
            db.session.add(user)
            db.session.flush()

        membership = _add_membership(user.id, tenant_id, role)
        db.session.flush()
        from app.services.audit_log_service import record_audit_log
        record_audit_log(
            action="user.create",
            resource_type="user",
            resource_id=user.id,
            resource_name=user.username,
            tenant_id=tenant_id,
            after_data={
                "user": _user_audit_snapshot(user),
                "membership": _membership_audit_snapshot(membership),
            },
        )
        db.session.commit()
        return user


def update_user(user_id: int, data: dict) -> User:
    """更新全局用户字段，以及当前租户下的 membership 角色/状态。"""
    with bypass_tenant_filter():
        user = db.session.get(User, user_id)
        if not user:
            raise BusinessError(ErrorCode.USER_NOT_FOUND)
        membership = _membership_for_tenant(user, getattr(g, "tenant_id", None))
        before = {
            "user": _user_audit_snapshot(user),
            "membership": _membership_audit_snapshot(membership),
        }

        revoke_tokens = False
        password_changed = False

        if "username" in data and data["username"] != user.username:
            if User.query.filter_by(username=data["username"]).first():
                raise BusinessError(ErrorCode.USER_EXISTS)
            user.username = data["username"]
        if "email" in data and data["email"] != user.email:
            if User.query.filter_by(email=data["email"]).first():
                raise BusinessError(ErrorCode.EMAIL_EXISTS)
            user.email = data["email"]
        if "role" in data:
            role_id = _role_id_by_name(data["role"], membership.tenant_id)
            if role_id is None:
                raise BusinessError(ErrorCode.INVALID_ROLE)
            if role_id != membership.role_id:
                membership.role_id = role_id
                revoke_tokens = True
        if "membership_active" in data and data["membership_active"] != membership.is_active:
            membership.is_active = data["membership_active"]
            revoke_tokens = True
        if "is_active" in data and data["is_active"] != user.is_active:
            user.is_active = data["is_active"]
            revoke_tokens = True
        if "password" in data and data["password"]:
            user.password_hash = generate_password_hash(data["password"])
            revoke_tokens = True
            password_changed = True

        if revoke_tokens:
            user.tokens_revoked_at = _revoke_marker()

        after = {
            "user": _user_audit_snapshot(user),
            "membership": _membership_audit_snapshot(membership),
        }
        if before != after or password_changed:
            from app.services.audit_log_service import record_audit_log
            record_audit_log(
                action=_user_update_action(before["user"], after["user"]),
                resource_type="user",
                resource_id=user.id,
                resource_name=user.username,
                tenant_id=membership.tenant_id,
                before_data=before,
                after_data=after,
                metadata={"password_changed": password_changed} if password_changed else None,
            )
        db.session.commit()
        return user


def change_password(user_id: int, old_password: str, new_password: str) -> User:
    user = db.session.get(User, user_id)
    if not user:
        raise BusinessError(ErrorCode.USER_NOT_FOUND)
    if not check_password_hash(user.password_hash, old_password):
        raise BusinessError(ErrorCode.INVALID_CREDENTIAL, "旧密码错误")

    user.password_hash = generate_password_hash(new_password)
    user.tokens_revoked_at = _revoke_marker()
    from app.services.audit_log_service import record_audit_log
    record_audit_log(
        action="password.change",
        resource_type="user",
        resource_id=user.id,
        resource_name=user.username,
        tenant_id=getattr(g, "tenant_id", None),
    )
    db.session.commit()
    return user


def delete_user(user_id: int, current_user_id: int):
    """从当前租户移除成员；如果用户没有任何成员身份，则删除全局用户。"""
    if user_id == current_user_id:
        raise BusinessError(ErrorCode.CANNOT_DELETE_SELF)
    tenant_id = getattr(g, "tenant_id", None)
    if tenant_id is None:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "未指定租户")

    with bypass_tenant_filter():
        user = db.session.get(User, user_id)
        if not user:
            raise BusinessError(ErrorCode.USER_NOT_FOUND)
        membership = TenantMembership.query.filter_by(
            user_id=user_id, tenant_id=tenant_id,
        ).first()
        if not membership:
            raise BusinessError(ErrorCode.USER_NOT_FOUND)
        before = {
            "user": _user_audit_snapshot(user),
            "membership": _membership_audit_snapshot(membership),
        }
        db.session.delete(membership)
        user.tokens_revoked_at = _revoke_marker()
        db.session.flush()
        will_delete_user = not TenantMembership.query.filter_by(user_id=user_id).first()
        from app.services.audit_log_service import record_audit_log
        record_audit_log(
            action="user.delete",
            resource_type="user",
            resource_id=user.id,
            resource_name=user.username,
            tenant_id=tenant_id,
            before_data=before,
            metadata={"deleted_global_user": will_delete_user},
        )
        if will_delete_user:
            db.session.delete(user)
        db.session.commit()


def seed_admin(username: str, email: str, password: str,
               tenant_slug: str = GUEST_TENANT_SLUG, is_superuser: bool = True):
    """确保存在平台管理员账号，并让其加入指定租户（默认 guest）。"""
    with bypass_tenant_filter():
        admin_role_id = _role_id_by_name("admin", tenant_id=None)
        existing = (
            User.query
            .join(TenantMembership, TenantMembership.user_id == User.id)
            .filter(TenantMembership.role_id == admin_role_id)
            .first()
        )
        if existing:
            return existing

        tenant = Tenant.query.filter_by(slug=tenant_slug).first()
        if not tenant:
            raise BusinessError(ErrorCode.TENANT_NOT_FOUND)

        admin = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            is_superuser=is_superuser,
        )
        db.session.add(admin)
        db.session.flush()
        _add_membership(admin.id, tenant.id, "admin", is_owner=True)
        db.session.commit()
        return admin


def _select_login_membership(user_id: int) -> TenantMembership:
    query = TenantMembership.query.join(Tenant).filter(
        TenantMembership.user_id == user_id,
        TenantMembership.is_active.is_(True),
        Tenant.is_active.is_(True),
    )
    # 优先选非 guest 租户；若用户只有 guest 则回退到 guest
    non_guest = query.filter(Tenant.slug != GUEST_TENANT_SLUG).order_by(TenantMembership.id).first()
    if non_guest:
        return non_guest
    membership = query.order_by(TenantMembership.id).first()
    if not membership:
        raise BusinessError(ErrorCode.INVALID_CREDENTIAL)
    return membership


def _membership_for_tenant(user: User, tenant_id: int | None) -> TenantMembership:
    if tenant_id is None:
        raise BusinessError(ErrorCode.TENANT_NOT_FOUND)
    membership = TenantMembership.query.filter_by(
        user_id=user.id, tenant_id=tenant_id,
    ).first()
    if not membership or not membership.is_active:
        raise BusinessError(ErrorCode.PERMISSION_DENIED, "用户不属于该租户或成员身份已禁用")
    if not membership.tenant or not membership.tenant.is_active:
        raise BusinessError(ErrorCode.AUTH_DISABLED, "租户已禁用")
    return membership


def _list_user_memberships(user_id: int) -> list[TenantMembership]:
    return (
        TenantMembership.query
        .filter_by(user_id=user_id)
        .order_by(TenantMembership.id)
        .all()
    )


def _claims_for_membership(user: User, membership: TenantMembership) -> dict:
    return {
        "perms": membership.permission_codes,
        "tenant_id": membership.tenant_id,
        "membership_id": membership.id,
        "is_superuser": user.is_superuser,
    }


def _add_membership(user_id: int, tenant_id: int, role_name: str,
                    is_owner: bool = False) -> TenantMembership:
    role_id = _role_id_by_name(role_name, tenant_id)
    if role_id is None:
        raise BusinessError(ErrorCode.INVALID_ROLE)
    membership = TenantMembership(
        user_id=user_id,
        tenant_id=tenant_id,
        role_id=role_id,
        is_owner=is_owner,
    )
    db.session.add(membership)
    return membership


def _role_id_by_name(name: str, tenant_id: int | None = None) -> int | None:
    from app.services.role_service import find_role_by_name
    role = find_role_by_name(name, tenant_id)
    return role.id if role else None


def _find_user(identifier: str) -> User | None:
    identifier = (identifier or "").strip()
    if not identifier:
        return None
    query = User.query
    if "@" in identifier:
        return query.filter_by(email=identifier).first()
    return query.filter_by(username=identifier).first()


def _user_audit_snapshot(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
    }


def _membership_audit_snapshot(membership: TenantMembership) -> dict:
    role = membership.role
    return {
        "id": membership.id,
        "tenant_id": membership.tenant_id,
        "user_id": membership.user_id,
        "role_id": membership.role_id,
        "role_name": role.name if role else None,
        "is_active": membership.is_active,
        "is_owner": membership.is_owner,
    }


def _user_update_action(before_user: dict, after_user: dict) -> str:
    if before_user.get("is_active") is True and after_user.get("is_active") is False:
        return "user.disable"
    if before_user.get("is_active") is False and after_user.get("is_active") is True:
        return "user.enable"
    return "user.update"
