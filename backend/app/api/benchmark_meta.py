"""Benchmark 元数据 API（供前端 dynamic form 使用）

  GET /api/v1/benchmarks/suites         — 全部 suite descriptor
  GET /api/v1/benchmarks/execution-schema — 执行配置字段声明
"""

from flask import Blueprint
from flask_jwt_extended import jwt_required

from app.benchmark.engine.registry import engine_registry
from app.benchmark.engine.inspect_evals.suite_loader import execution_schema
from app.utils.response import ok


benchmark_meta_bp = Blueprint("benchmark_meta", __name__)


@benchmark_meta_bp.route("/suites", methods=["GET"])
@jwt_required()
def list_suites():
    suites = engine_registry.all_suites(include_disabled=True)
    payload = [s.to_dict() for s in suites]
    return ok({
        "items": payload,
        "total": len(payload),
    })


@benchmark_meta_bp.route("/execution-schema", methods=["GET"])
@jwt_required()
def get_execution_schema():
    return ok(execution_schema())
