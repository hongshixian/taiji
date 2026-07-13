"""Benchmark 测评任务输入校验 Schema"""

from marshmallow import Schema, ValidationError, fields, validate, validates, validates_schema

from app.benchmark.engine.registry import engine_registry


def _enabled_suite_keys() -> list[str]:
    """启用的 suite key 白名单（从引擎注册表动态取）。"""

    keys = engine_registry.enabled_suite_keys()
    return keys or ["_placeholder_"]  # 引擎未加载时给个占位，避免 OneOf 空列表


class BenchmarkSubmitSchema(Schema):
    task_name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=100),
    )
    notes = fields.String(load_default=None, validate=validate.Length(max=500))

    benchmark_suite = fields.String(required=True)

    target_model_id = fields.Integer(required=True, strict=True)
    judge_model_id = fields.Integer(load_default=None, allow_none=True, strict=True)

    # 引擎无关的执行控制参数
    execution_config = fields.Dict(load_default=dict)
    # suite 特有参数（DynamicField 提交的 KV）
    suite_config = fields.Dict(load_default=dict)

    @validates("task_name")
    def validate_task_name(self, value):
        if not value.strip():
            raise ValidationError("任务名称不能为空白")

    @validates("benchmark_suite")
    def validate_benchmark_suite(self, value):
        keys = _enabled_suite_keys()
        if value not in keys:
            raise ValidationError(f"未启用的 benchmark suite：{value}")

    @validates_schema
    def validate_judge_when_needed(self, data, **_kwargs):
        suite_key = data.get("benchmark_suite")
        engine = engine_registry.find_engine_for_suite(suite_key) if suite_key else None
        suite = engine.get_suite(suite_key) if engine else None
        if suite and suite.needs_judge and not data.get("judge_model_id"):
            raise ValidationError({"judge_model_id": ["该评测需要指定评委模型"]})
