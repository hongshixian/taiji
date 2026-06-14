"""模型配置业务逻辑（租户隔离）"""

from app import db
from app.models.model_config import ModelConfig
from app.utils.errors import BusinessError, ErrorCode


def model_config_to_dict(m: ModelConfig) -> dict:
    return {
        "id": m.id,
        "display_name": m.display_name,
        "api_base_url": m.api_base_url,
        "api_protocol": m.api_protocol,
        "model_name": m.model_name,
        "description": m.description,
        "extra_params": m.extra_params or {},
        "is_active": m.is_active,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
    }


def list_model_configs(page: int = 1, per_page: int = 50, include_inactive: bool = False):
    q = ModelConfig.query
    if not include_inactive:
        q = q.filter_by(is_active=True)
    q = q.order_by(ModelConfig.display_name)
    return q.paginate(page=page, per_page=per_page, error_out=False)


def get_model_config_or_404(config_id: int) -> ModelConfig:
    m = db.session.get(ModelConfig, config_id)
    if not m:
        raise BusinessError(ErrorCode.MODEL_CONFIG_NOT_FOUND)
    return m


def create_model_config(
    tenant_id: int,
    display_name: str,
    api_base_url: str,
    api_protocol: str,
    model_name: str,
    description: str | None = None,
    extra_params: dict | None = None,
) -> ModelConfig:
    exists = ModelConfig.query.filter_by(display_name=display_name).first()
    if exists:
        raise BusinessError(ErrorCode.MODEL_CONFIG_NAME_EXISTS)

    m = ModelConfig(
        tenant_id=tenant_id,
        display_name=display_name,
        api_base_url=api_base_url,
        api_protocol=api_protocol,
        model_name=model_name,
        description=description,
        extra_params=extra_params or {},
        is_active=True,
    )
    db.session.add(m)
    db.session.commit()
    return m


def update_model_config(config_id: int, data: dict) -> ModelConfig:
    m = get_model_config_or_404(config_id)

    if "display_name" in data and data["display_name"] != m.display_name:
        exists = ModelConfig.query.filter_by(display_name=data["display_name"]).first()
        if exists:
            raise BusinessError(ErrorCode.MODEL_CONFIG_NAME_EXISTS)
        m.display_name = data["display_name"]

    for field in ("api_base_url", "api_protocol", "model_name", "description", "extra_params", "is_active"):
        if field in data:
            setattr(m, field, data[field])

    db.session.commit()
    return m


def delete_model_config(config_id: int) -> None:
    m = get_model_config_or_404(config_id)
    db.session.delete(m)
    db.session.commit()
