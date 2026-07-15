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
            notes=(parsed.get("notes") or None),
            benchmark_suite=parsed["benchmark_suite"],
            target_model_id=parsed["target_model_id"],
            judge_model_id=parsed.get("judge_model_id"),
            execution_config=parsed.get("execution_config") or {},
            suite_config=parsed.get("suite_config") or {},
        )

    def execute(self, task_id: int) -> None:
        execute_benchmark(task_id)

    def to_dict(self, task) -> dict:
        return benchmark_task_to_dict(task)

    def _clear_detail(self, task) -> None:
        if task.benchmark:
            task.benchmark.result = None
            # 重跑前清空进度
            task.progress = None


_handler = BenchmarkHandler()
registry.register(_handler)
