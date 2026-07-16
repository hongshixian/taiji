"""Benchmark 资产管理接口（租户级启用状态 + 数据集可访问性检测）

挂在 /api/v1/benchmarks 下，路径段用 /manage/ 避开 benchmark_meta 的 /suites。
"""

from flask import Blueprint, g, request
from flask_jwt_extended import jwt_required

from app import limiter
from app.permissions import Permission
from app.services.benchmark_state_service import (
    is_check_pending,
    list_suites_with_state,
    mark_check_pending,
    set_enabled,
)
from app.utils.decorators import require_permission
from app.utils.errors import BusinessError, ErrorCode
from app.utils.response import ok

benchmark_mgmt_bp = Blueprint("benchmark_mgmt", __name__)


@benchmark_mgmt_bp.route("/manage/suites", methods=["GET"])
@jwt_required()
@require_permission(Permission.BENCHMARK_READ)
def list_suites():
    items = list_suites_with_state()
    return ok({"items": items, "total": len(items)})


@benchmark_mgmt_bp.route("/manage/suites/<suite_key>", methods=["PATCH"])
@jwt_required()
@require_permission(Permission.BENCHMARK_WRITE)
def patch_suite(suite_key):
    data = request.get_json(silent=True) or {}
    if "enabled" not in data:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "缺少 enabled 字段")
    enabled = data.get("enabled")
    if enabled not in (True, False, None):
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "enabled 必须为 true / false / null")
    item = set_enabled(g.tenant_id, suite_key, enabled)
    return ok(item, message="已更新")


@benchmark_mgmt_bp.route("/manage/suites/<suite_key>/check", methods=["POST"])
@jwt_required()
@require_permission(Permission.BENCHMARK_WRITE)
@limiter.limit("6 per minute")
def check_suite(suite_key):
    # 校验 suite 存在（set_enabled 内部也校验，这里借 is_check_pending 前先校验）
    from app.services.benchmark_state_service import _validate_suite_key

    _validate_suite_key(suite_key)
    if is_check_pending(suite_key):
        raise BusinessError(ErrorCode.VALIDATION_ERROR, "该 benchmark 正在检测中")
    mark_check_pending(g.tenant_id, suite_key)

    from app.tasks.benchmark_check import benchmark_check_task
    benchmark_check_task.delay(g.tenant_id, suite_key)
    return ok({"status": "pending"}, message="检测已启动")
