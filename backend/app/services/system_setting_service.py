"""平台系统设置服务"""

from app import db
from app.models.system_setting import SystemSetting
from app.models.tenant import GUEST_TENANT_SLUG, Tenant
from app.utils.decorators import bypass_tenant_filter
from app.utils.errors import BusinessError, ErrorCode


DEFAULT_REGISTRATION_TENANT_KEY = "public.default_registration_tenant_slug"

SETTING_DEFINITIONS = {
    DEFAULT_REGISTRATION_TENANT_KEY: {
        "description": "新注册用户默认加入的租户 slug",
        "default": GUEST_TENANT_SLUG,
    },
}


def get_setting_value(key: str):
    setting = db.session.get(SystemSetting, key)
    if setting:
        return setting.value
    definition = SETTING_DEFINITIONS.get(key)
    return definition["default"] if definition else None


def get_default_registration_tenant_slug() -> str:
    return get_setting_value(DEFAULT_REGISTRATION_TENANT_KEY) or GUEST_TENANT_SLUG


def list_settings() -> list[dict]:
    return [_setting_to_dict(key) for key in SETTING_DEFINITIONS]


def update_settings(data: dict) -> list[dict]:
    allowed = set(SETTING_DEFINITIONS)
    unknown = set(data) - allowed
    if unknown:
        raise BusinessError(
            ErrorCode.VALIDATION_ERROR,
            f"未知系统设置: {', '.join(sorted(unknown))}",
        )

    if DEFAULT_REGISTRATION_TENANT_KEY in data:
        slug = (data.get(DEFAULT_REGISTRATION_TENANT_KEY) or "").strip()
        if not slug:
            raise BusinessError(ErrorCode.VALIDATION_ERROR, "默认注册租户不能为空")
        with bypass_tenant_filter():
            tenant = Tenant.query.filter_by(slug=slug).first()
        if not tenant:
            raise BusinessError(ErrorCode.TENANT_NOT_FOUND)
        if not tenant.is_active:
            raise BusinessError(ErrorCode.AUTH_DISABLED, "默认注册租户已禁用")
        _upsert_setting(DEFAULT_REGISTRATION_TENANT_KEY, slug)

    db.session.commit()
    return list_settings()


def _setting_to_dict(key: str) -> dict:
    definition = SETTING_DEFINITIONS[key]
    value = get_setting_value(key)
    setting = db.session.get(SystemSetting, key)
    return {
        "key": key,
        "value": value,
        "description": definition["description"],
        "updated_at": setting.updated_at.isoformat() if setting and setting.updated_at else None,
    }


def _upsert_setting(key: str, value):
    definition = SETTING_DEFINITIONS[key]
    setting = db.session.get(SystemSetting, key)
    if setting:
        setting.value = value
        setting.description = definition["description"]
    else:
        db.session.add(SystemSetting(
            key=key,
            value=value,
            description=definition["description"],
        ))
