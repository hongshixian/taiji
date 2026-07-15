"""平台系统设置服务"""

from app import db
from app.models.system_setting import SystemSetting
from app.models.tenant import GUEST_TENANT_SLUG, Tenant
from app.utils.decorators import bypass_tenant_filter
from app.utils.errors import BusinessError, ErrorCode


DEFAULT_REGISTRATION_TENANT_KEY = "public.default_registration_tenant_slug"
HF_TOKEN_KEY = "integrations.hf_token"
DEFAULT_JUDGE_MODEL_ID_KEY = "benchmark.default_judge_model_id"

SETTING_DEFINITIONS = {
    DEFAULT_REGISTRATION_TENANT_KEY: {
        "description": "新注册用户默认加入的租户 slug",
        "default": GUEST_TENANT_SLUG,
    },
    HF_TOKEN_KEY: {
        "description": "HuggingFace 访问令牌（用于 gated 数据集）",
        "default": "",
        "secret": True,
    },
    DEFAULT_JUDGE_MODEL_ID_KEY: {
        "description": "Benchmark 默认评委模型 ID（前端预填）",
        "default": None,
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

    def _for_audit(key):
        val = get_setting_value(key)
        if SETTING_DEFINITIONS.get(key, {}).get("secret"):
            return "***" if val else ""
        return val

    before = {key: _for_audit(key) for key in data if key in allowed}

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

    if HF_TOKEN_KEY in data:
        token = (data.get(HF_TOKEN_KEY) or "").strip()
        _upsert_setting(HF_TOKEN_KEY, token)

    if DEFAULT_JUDGE_MODEL_ID_KEY in data:
        raw = data.get(DEFAULT_JUDGE_MODEL_ID_KEY)
        model_id = None
        if raw not in (None, "", 0):
            try:
                model_id = int(raw)
            except (TypeError, ValueError):
                raise BusinessError(ErrorCode.VALIDATION_ERROR, "评委模型 ID 必须为整数")
        _upsert_setting(DEFAULT_JUDGE_MODEL_ID_KEY, model_id)

    after = {key: _for_audit(key) for key in data if key in allowed}
    if before != after:
        from app.services.audit_log_service import record_audit_log
        record_audit_log(
            action="system_setting.update",
            resource_type="system_setting",
            resource_id=",".join(sorted(after)),
            resource_name="系统设置",
            tenant_id=None,
            before_data=before,
            after_data=after,
        )
    db.session.commit()
    return list_settings()


def _setting_to_dict(key: str) -> dict:
    definition = SETTING_DEFINITIONS[key]
    value = get_setting_value(key)
    # 隐藏敏感值：只返回是否已设置
    if definition.get("secret"):
        display_value = bool(value)
    else:
        display_value = value
    setting = db.session.get(SystemSetting, key)
    return {
        "key": key,
        "value": display_value,
        "is_secret": bool(definition.get("secret")),
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
