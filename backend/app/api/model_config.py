"""模型配置接口（租户隔离，需相应权限）"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt

from app import limiter
from app.permissions import Permission
from app.utils.decorators import require_permission
from app.utils.errors import BusinessError, ErrorCode
from app.utils.response import ok, created, paginated
from app.services.model_config_service import (
    list_model_configs,
    get_model_config_or_404,
    create_model_config,
    update_model_config,
    delete_model_config,
    model_config_to_dict,
)

model_config_bp = Blueprint("model_config", __name__)

_PROTOCOLS = ("openai", "anthropic", "gemini", "ollama", "custom")


@model_config_bp.route("/", methods=["GET"])
@jwt_required()
@require_permission(Permission.MODEL_READ)
def get_model_configs():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 200)
    include_inactive = request.args.get("include_inactive", "false").lower() == "true"
    pg = list_model_configs(page=page, per_page=per_page, include_inactive=include_inactive)
    return paginated(
        items=[model_config_to_dict(m) for m in pg.items],
        total=pg.total,
        page=pg.page,
        per_page=pg.per_page,
    )


@model_config_bp.route("/<int:config_id>", methods=["GET"])
@jwt_required()
@require_permission(Permission.MODEL_READ)
def get_model_config(config_id):
    m = get_model_config_or_404(config_id)
    return ok(model_config_to_dict(m))


@model_config_bp.route("/", methods=["POST"])
@jwt_required()
@require_permission(Permission.MODEL_WRITE)
@limiter.limit("30 per minute")
def add_model_config():
    from flask_jwt_extended import get_jwt
    claims = get_jwt()
    tenant_id = claims.get("tenant_id")

    data = request.get_json() or {}
    display_name = (data.get("display_name") or "").strip()
    api_base_url = (data.get("api_base_url") or "").strip()
    api_protocol = (data.get("api_protocol") or "").strip()
    model_name = (data.get("model_name") or "").strip()

    if not display_name:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "显示名称不能为空")
    if not api_base_url:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "API 地址不能为空")
    if api_protocol not in _PROTOCOLS:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, f"协议须为 {', '.join(_PROTOCOLS)} 之一")
    if not model_name:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "模型名称不能为空")

    extra_params = data.get("extra_params") or {}
    if not isinstance(extra_params, dict):
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "extra_params 须为对象")

    m = create_model_config(
        tenant_id=tenant_id,
        display_name=display_name,
        api_base_url=api_base_url,
        api_protocol=api_protocol,
        model_name=model_name,
        description=data.get("description", ""),
        extra_params=extra_params,
    )
    return created(model_config_to_dict(m), message="模型配置已创建")


@model_config_bp.route("/<int:config_id>", methods=["PUT"])
@jwt_required()
@require_permission(Permission.MODEL_WRITE)
def edit_model_config(config_id):
    data = request.get_json() or {}
    if not data:
        raise BusinessError(ErrorCode.EMPTY_BODY)

    if "api_protocol" in data and data["api_protocol"] not in _PROTOCOLS:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, f"协议须为 {', '.join(_PROTOCOLS)} 之一")
    if "extra_params" in data and not isinstance(data.get("extra_params"), dict):
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "extra_params 须为对象")

    m = update_model_config(config_id, data)
    return ok(model_config_to_dict(m), message="已更新")


@model_config_bp.route("/<int:config_id>", methods=["DELETE"])
@jwt_required()
@require_permission(Permission.MODEL_DELETE)
def remove_model_config(config_id):
    delete_model_config(config_id)
    return ok(message="已删除")
