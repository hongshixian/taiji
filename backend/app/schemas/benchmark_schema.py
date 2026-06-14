"""Benchmark 测评任务输入校验 Schema"""

from marshmallow import Schema, ValidationError, fields, validate, validates


BENCHMARK_SUITES = ["mmlu", "gsm8k", "hellaswag", "humaneval"]


class BenchmarkSubmitSchema(Schema):
    task_name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=100),
    )
    model_name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=200),
    )
    model_endpoint = fields.String(
        load_default=None,
        validate=validate.Length(max=500),
    )
    model_api_key = fields.String(
        load_default=None,
        validate=validate.Length(max=500),
    )
    benchmark_suite = fields.String(
        required=True,
        validate=validate.OneOf(BENCHMARK_SUITES),
    )
    benchmark_config = fields.Dict(load_default=None)

    @validates("task_name")
    def validate_task_name(self, value):
        if not value.strip():
            raise ValidationError("任务名称不能为空白")
