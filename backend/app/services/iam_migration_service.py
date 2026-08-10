"""Idempotent migration of legacy Taiji identities into the IAM service."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
import time
from typing import Callable
from uuid import UUID, uuid4

import requests
from sqlalchemy import inspect

from app import db
from app.models.iam_migration_record import IamMigrationRecord
from app.models.role import Role
from app.models.tenant import GUEST_TENANT_SLUG, Tenant
from app.models.tenant_membership import TenantMembership
from app.models.user import User
from app.services.iam_projection_service import project_iam_tenant_membership


class MigrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class MigrationApiError(MigrationError):
    status: int
    code: str
    message: str

    def __str__(self) -> str:
        return f"IAM {self.status} {self.code}: {self.message}"


@dataclass
class MigrationReport:
    dry_run: bool
    counts: dict[str, int]
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    migrated: dict[str, int] = field(
        default_factory=lambda: {"tenants": 0, "users": 0, "memberships": 0}
    )
    skipped: dict[str, int] = field(
        default_factory=lambda: {"tenants": 0, "users": 0, "memberships": 0}
    )

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict:
        return {
            "mode": "dry-run" if self.dry_run else "apply",
            "ok": self.ok,
            "counts": self.counts,
            "migrated": self.migrated,
            "skipped": self.skipped,
            "warnings": self.warnings,
            "errors": self.errors,
        }


class IamMigrationApi:
    """Narrow client authenticated as the one-time migrator service account."""

    def __init__(self, base_url: str, realm: str, client_id: str, client_secret: str):
        self.realm_url = f"{base_url.rstrip('/')}/realms/{realm}"
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = (3, 15)
        self._access_token: str | None = None
        self._expires_at = 0.0

    def migrate_tenant(self, tenant_id: str, payload: dict) -> dict:
        return self._request("PUT", f"taiji-iam/v1/migration/tenants/{tenant_id}", payload)

    def migrate_user(self, user_id: str, payload: dict) -> dict:
        return self._request("PUT", f"taiji-iam/v1/migration/users/{user_id}", payload)

    def migrate_membership(self, tenant_id: str, user_id: str, payload: dict) -> dict:
        return self._request(
            "PUT",
            f"taiji-iam/v1/migration/tenants/{tenant_id}/members/{user_id}",
            payload,
        )

    def _token(self, force: bool = False) -> str:
        if not force and self._access_token and time.monotonic() < self._expires_at:
            return self._access_token
        try:
            response = requests.post(
                f"{self.realm_url}/protocol/openid-connect/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise MigrationApiError(503, "iam_unavailable", "无法连接 IAM") from exc
        if response.status_code >= 400:
            payload = _json_or_empty(response)
            raise MigrationApiError(
                response.status_code,
                str(payload.get("error", "token_request_failed")),
                str(payload.get("error_description", "迁移服务账号认证失败")),
            )
        payload = response.json()
        self._access_token = payload["access_token"]
        self._expires_at = time.monotonic() + max(int(payload.get("expires_in", 60)) - 15, 1)
        return self._access_token

    def _request(self, method: str, path: str, payload: dict, retry_auth: bool = True) -> dict:
        try:
            response = requests.request(
                method,
                f"{self.realm_url}/{path}",
                headers={"Authorization": f"Bearer {self._token()}"},
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise MigrationApiError(503, "iam_unavailable", "无法连接 IAM") from exc
        if response.status_code == 401 and retry_auth:
            self._token(force=True)
            return self._request(method, path, payload, retry_auth=False)
        if response.status_code >= 400:
            body = _json_or_empty(response)
            raise MigrationApiError(
                response.status_code,
                str(body.get("code", "migration_request_failed")),
                str(body.get("message", "IAM 迁移请求失败")),
            )
        body = response.json()
        if not isinstance(body, dict):
            raise MigrationApiError(502, "invalid_iam_response", "IAM 返回了无效响应")
        return body


class LegacyIamMigrator:
    def __init__(
        self,
        api: IamMigrationApi,
        *,
        link_existing: set[str] | None = None,
        bootstrap_username: str = "admin",
        force: bool = False,
    ):
        self.api = api
        self.link_existing = {value.casefold() for value in (link_existing or set())}
        self.bootstrap_username = bootstrap_username.casefold()
        self.force = force
        self.report = MigrationReport(dry_run=False, counts=self._counts())

    @staticmethod
    def preflight() -> MigrationReport:
        schema_errors = _schema_errors()
        if schema_errors:
            return MigrationReport(dry_run=True, counts={}, errors=schema_errors)
        report = MigrationReport(dry_run=True, counts=LegacyIamMigrator._counts())
        fixed_roles = {
            role.name for role in Role.query.filter_by(tenant_id=None).all()
        }
        missing_roles = {"admin", "user"} - fixed_roles
        if missing_roles:
            report.errors.append(
                "缺少本地固定角色: " + ", ".join(sorted(missing_roles))
            )

        for label, values in (
            ("用户名", [user.username for user in User.query.all()]),
            ("邮箱", [user.email for user in User.query.all()]),
        ):
            duplicates = _casefold_duplicates(values)
            if duplicates:
                report.errors.append(f"{label}存在忽略大小写冲突: {', '.join(duplicates)}")

        for user in User.query.order_by(User.id).all():
            if not user.username or not user.email:
                report.errors.append(f"用户 {user.id} 缺少用户名或邮箱")
            if user.iam_user_id and not _is_uuid(user.iam_user_id):
                report.errors.append(f"用户 {user.id} 的 iam_user_id 不是 UUID")
            if user.password_hash and not _supported_legacy_hash(user.password_hash):
                report.errors.append(f"用户 {user.id} 的旧密码摘要格式不受支持")

        custom_role_members = 0
        for tenant in Tenant.query.order_by(Tenant.id).all():
            if tenant.iam_tenant_id and not _is_uuid(tenant.iam_tenant_id):
                report.errors.append(f"租户 {tenant.id} 的 iam_tenant_id 不是 UUID")
            members = TenantMembership.query.filter_by(tenant_id=tenant.id).all()
            if tenant.is_active and not any(
                member.is_active and _iam_role(member) == "tenant_admin"
                for member in members
            ):
                report.errors.append(f"有效租户 {tenant.id} 没有有效管理员")
            custom_role_members += sum(
                1 for member in members if member.role and member.role.tenant_id is not None
            )
        if custom_role_members:
            report.warnings.append(
                f"{custom_role_members} 个自定义角色成员将统一映射为 member"
            )
        return report

    def run(self) -> MigrationReport:
        preflight = self.preflight()
        self.report.warnings.extend(preflight.warnings)
        if preflight.errors:
            self.report.errors.extend(preflight.errors)
            return self.report

        for tenant_id in [row.id for row in Tenant.query.order_by(Tenant.id).all()]:
            self._migrate_tenant(tenant_id)
        for user_id in [row.id for row in User.query.order_by(User.id).all()]:
            self._migrate_user(user_id)
        for membership_id in [
            row.id for row in TenantMembership.query.order_by(TenantMembership.id).all()
            if row.tenant and row.tenant.tenant_type != "personal"
        ]:
            self._migrate_membership(membership_id)
        return self.report

    @staticmethod
    def _counts() -> dict[str, int]:
        custom = (
            TenantMembership.query.join(Role, TenantMembership.role_id == Role.id)
            .filter(Role.tenant_id.isnot(None))
            .count()
        )
        return {
            "users": User.query.count(),
            "tenants": Tenant.query.filter(
                (Tenant.tenant_type.is_(None)) | (Tenant.tenant_type != "personal")
            ).count(),
            "memberships": TenantMembership.query.join(Tenant).filter(
                (Tenant.tenant_type.is_(None)) | (Tenant.tenant_type != "personal")
            ).count(),
            "platform_admins": User.query.filter_by(is_superuser=True, is_active=True).count(),
            "custom_role_memberships": custom,
        }

    def _migrate_tenant(self, local_id: int) -> None:
        tenant = db.session.get(Tenant, local_id)
        if tenant is None or tenant.tenant_type == "personal":
            return
        stable_id, record = self._prepare_record(
            "tenant", str(local_id), tenant.iam_tenant_id
        )
        tenant.iam_tenant_id = stable_id
        db.session.commit()

        payload = {
            "name": tenant.name,
            "enabled": tenant.is_active,
            "protectedTenant": bool(tenant.is_system or tenant.slug == GUEST_TENANT_SLUG),
        }

        def apply_response(response: dict) -> str | None:
            current = db.session.get(Tenant, local_id)
            current.iam_tenant_id = _required_response(response, "id")
            current.keycloak_org_id = _required_response(response, "keycloak_org_id")
            current.tenant_type = str(response.get("tenant_type", "enterprise"))
            current.lifecycle_status = str(response.get("lifecycle_status", "active"))
            current.is_protected = bool(response.get("protected", payload["protectedTenant"]))
            current.last_synced_at = _now()
            return current.keycloak_org_id

        self._execute(
            record,
            "tenants",
            lambda: self.api.migrate_tenant(stable_id, payload),
            apply_response,
        )

    def _migrate_user(self, local_id: int) -> None:
        user = db.session.get(User, local_id)
        if user is None:
            return
        stable_id, record = self._prepare_record("user", str(local_id), user.iam_user_id)
        user.iam_user_id = stable_id
        db.session.commit()
        auto_link_admin = (
            user.is_superuser
            and user.is_active
            and user.username.casefold() == self.bootstrap_username
        )
        link_existing = auto_link_admin or user.username.casefold() in self.link_existing
        link_existing = link_existing or user.email.casefold() in self.link_existing
        payload = {
            "username": user.username,
            "email": user.email,
            "enabled": user.is_active,
            "platformAdmin": bool(user.is_superuser and user.is_active),
            "linkExisting": link_existing,
            "legacyPasswordHash": user.password_hash,
        }

        def apply_response(response: dict) -> str | None:
            current = db.session.get(User, local_id)
            actual_id = _required_response(response, "id")
            current.iam_user_id = actual_id
            current.keycloak_subject = _required_response(response, "keycloak_subject")
            current.last_synced_at = _now()
            personal = response.get("personal_tenant")
            if not isinstance(personal, dict):
                raise MigrationError("IAM 响应缺少 personal_tenant")
            project_iam_tenant_membership(current, personal)
            record_row = db.session.get(IamMigrationRecord, record.id)
            record_row.stable_id = actual_id
            return current.keycloak_subject

        self._execute(
            record,
            "users",
            lambda: self.api.migrate_user(stable_id, payload),
            apply_response,
        )

    def _migrate_membership(self, local_id: int) -> None:
        membership = db.session.get(TenantMembership, local_id)
        if membership is None or membership.tenant.tenant_type == "personal":
            return
        _, record = self._prepare_record("membership", str(local_id), None)
        role_name = _iam_role(membership)
        payload = {"role": role_name, "active": membership.is_active}

        def request() -> dict:
            current = db.session.get(TenantMembership, local_id)
            if not current.tenant.iam_tenant_id or not current.user.iam_user_id:
                raise MigrationError("成员关系依赖的用户或租户尚未迁移成功")
            return self.api.migrate_membership(
                current.tenant.iam_tenant_id, current.user.iam_user_id, payload
            )

        def apply_response(response: dict) -> str | None:
            current = db.session.get(TenantMembership, local_id)
            fixed_role_name = "admin" if role_name == "tenant_admin" else "user"
            fixed_role = Role.query.filter_by(tenant_id=None, name=fixed_role_name).first()
            if fixed_role is None:
                raise MigrationError(f"缺少本地固定角色 {fixed_role_name}")
            current.role_id = fixed_role.id
            current.iam_role = role_name
            current.sync_version = int(_now().timestamp() * 1000)
            current.last_synced_at = _now()
            return response.get("keycloak_subject")

        self._execute(record, "memberships", request, apply_response)

    def _prepare_record(
        self, entity_type: str, local_id: str, current_stable_id: str | None
    ) -> tuple[str, IamMigrationRecord]:
        record = IamMigrationRecord.query.filter_by(
            entity_type=entity_type, local_id=local_id
        ).first()
        if record and current_stable_id and record.stable_id != current_stable_id:
            raise MigrationError(
                f"{entity_type} {local_id} 的本地稳定 ID 与迁移记录不一致"
            )
        stable_id = current_stable_id or (record.stable_id if record else str(uuid4()))
        if not _is_uuid(stable_id):
            raise MigrationError(f"{entity_type} {local_id} 的稳定 ID 不是 UUID")
        if record is None:
            record = IamMigrationRecord(
                entity_type=entity_type,
                local_id=local_id,
                stable_id=stable_id,
                status="pending",
            )
            db.session.add(record)
            db.session.flush()
        return stable_id, record

    def _execute(
        self,
        record: IamMigrationRecord,
        counter: str,
        request: Callable[[], dict],
        apply_response: Callable[[dict], str | None],
    ) -> None:
        if record.status == "succeeded" and not self.force:
            self.report.skipped[counter] += 1
            return
        record.status = "running"
        record.attempts += 1
        record.last_error = None
        record.last_attempted_at = _now()
        db.session.commit()
        record_id = record.id
        try:
            response = request()
            keycloak_id = apply_response(response)
            current = db.session.get(IamMigrationRecord, record_id)
            current.status = "succeeded"
            current.keycloak_id = keycloak_id
            current.last_error = None
            current.completed_at = _now()
            db.session.commit()
            self.report.migrated[counter] += 1
        except Exception as exc:
            db.session.rollback()
            current = db.session.get(IamMigrationRecord, record_id)
            current.status = "failed"
            current.last_error = _safe_error(exc)
            db.session.commit()
            self.report.errors.append(
                f"{current.entity_type} {current.local_id}: {current.last_error}"
            )


def _iam_role(membership: TenantMembership) -> str:
    if membership.is_owner or (
        membership.role
        and membership.role.tenant_id is None
        and membership.role.name == "admin"
    ):
        return "tenant_admin"
    return "member"


def _supported_legacy_hash(value: str) -> bool:
    if len(value) > 1024:
        return False
    parts = value.split("$")
    if len(parts) != 3 or not parts[1] or not re.fullmatch(r"[0-9a-fA-F]{32,256}", parts[2]):
        return False
    method = parts[0].split(":")
    try:
        if method[0] == "scrypt" and len(method) == 4:
            n, r, p = (int(item) for item in method[1:])
            return (
                2 <= n <= 131072
                and n & (n - 1) == 0
                and 1 <= r <= 16
                and 1 <= p <= 4
                and n * r <= 1_048_576
            )
        if method[0] == "pbkdf2" and len(method) == 3:
            return method[1] in {"sha1", "sha256", "sha512"} and 1 <= int(method[2]) <= 2_000_000
    except ValueError:
        return False
    return False


def _casefold_duplicates(values: list[str]) -> list[str]:
    seen: dict[str, str] = {}
    duplicates: set[str] = set()
    for value in values:
        folded = (value or "").casefold()
        if folded in seen:
            duplicates.add(value)
            duplicates.add(seen[folded])
        else:
            seen[folded] = value
    return sorted(duplicates)


def _is_uuid(value: str) -> bool:
    try:
        return str(UUID(str(value))) == str(value).lower()
    except (ValueError, AttributeError, TypeError):
        return False


def _required_response(payload: dict, key: str) -> str:
    value = payload.get(key)
    if value is None or not str(value).strip():
        raise MigrationError(f"IAM 响应缺少 {key}")
    return str(value)


def _safe_error(error: Exception) -> str:
    if isinstance(error, MigrationApiError):
        value = str(error)
    elif isinstance(error, MigrationError):
        value = str(error)
    else:
        value = f"{type(error).__name__}: 本地投影更新失败"
    return value.replace("\n", " ")[:500]


def _json_or_empty(response) -> dict:
    try:
        payload = response.json()
        return payload if isinstance(payload, dict) else {}
    except ValueError:
        return {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _schema_errors() -> list[str]:
    required = {
        "users": {"iam_user_id", "keycloak_subject", "last_synced_at"},
        "tenants": {
            "iam_tenant_id",
            "keycloak_org_id",
            "tenant_type",
            "lifecycle_status",
            "is_protected",
            "last_synced_at",
        },
        "tenant_memberships": {"iam_role", "sync_version", "last_synced_at"},
        "iam_migration_records": {
            "entity_type",
            "local_id",
            "stable_id",
            "status",
            "attempts",
        },
    }
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    errors = []
    for table, columns in required.items():
        if table not in tables:
            errors.append(f"数据库缺少 {table}，请先执行 flask db upgrade")
            continue
        available = {column["name"] for column in inspector.get_columns(table)}
        missing = columns - available
        if missing:
            errors.append(
                f"数据库表 {table} 缺少字段 {', '.join(sorted(missing))}，"
                "请先执行 flask db upgrade"
            )
    return errors
