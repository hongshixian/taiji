"""Benchmark 测评任务处理器"""

from flask import request

from app.handlers.base import BaseTaskHandler
from app.handlers.registry import registry
from app.schemas.benchmark_schema import BenchmarkSubmitSchema
from app.services.benchmark_service import (
    benchmark_task_to_dict,
    create_benchmark_task,
    execute_benchmark,
)
from app.utils.errors import BusinessError, ErrorCode
from app.utils.validation import validate_schema


class BenchmarkHandler(BaseTaskHandler):
    task_type = "benchmark"
    task_type_name = "Benchmark 测评"
    url_prefix = "benchmark"
    rate_limit_submit = "20 per minute"

    def submit(self, user_id: int):
        data = request.get_json()
        if not data:
            raise BusinessError(ErrorCode.EMPTY_BODY)
        parsed, error = validate_schema(BenchmarkSubmitSchema(), data)
        if error:
            raise BusinessError(ErrorCode.VALIDATION_ERROR)
        return create_benchmark_task(
            user_id=user_id,
            task_name=parsed["task_name"].strip(),
            model_name=parsed["model_name"].strip(),
            model_endpoint=parsed.get("model_endpoint"),
            model_api_key=parsed.get("model_api_key"),
            benchmark_suite=parsed["benchmark_suite"],
            benchmark_config=parsed.get("benchmark_config"),
        )

    def execute(self, task_id: int) -> None:
        execute_benchmark(task_id)

    def to_dict(self, task) -> dict:
        return benchmark_task_to_dict(task)

    def _clear_detail(self, task) -> None:
        if task.benchmark:
            task.benchmark.result = None


_handler = BenchmarkHandler()
registry.register(_handler)
