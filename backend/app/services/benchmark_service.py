"""Benchmark 测评任务业务逻辑（空壳实现）"""

from app import db
from app.models.benchmark_task import BenchmarkTask
from app.models.task import Task, TaskType
from app.services.task_service import (
    create_task_record,
    task_base_to_dict,
    mark_running,
    mark_success,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def create_benchmark_task(
    user_id: int,
    task_name: str,
    model_name: str,
    model_endpoint: str | None,
    model_api_key: str | None,
    benchmark_suite: str,
    benchmark_config: dict | None,
) -> Task:
    """创建 Benchmark 测评任务"""

    task = create_task_record(user_id, TaskType.BENCHMARK)
    detail = BenchmarkTask(
        tenant_id=task.tenant_id,
        task_id=task.id,
        task_name=task_name,
        model_name=model_name,
        model_endpoint=model_endpoint,
        model_api_key=model_api_key,
        benchmark_suite=benchmark_suite,
        benchmark_config=benchmark_config,
    )
    db.session.add(detail)
    db.session.commit()
    return task


def execute_benchmark(task_id: int) -> None:
    """执行 Benchmark 测评（空壳：直接标记成功）"""

    task = db.session.get(Task, task_id)
    if not task or task.task_type != TaskType.BENCHMARK:
        logger.error(f"Benchmark 任务 {task_id} 不存在")
        return

    mark_running(task)
    # TODO: 实现实际测评逻辑
    pass
    mark_success(task)


def benchmark_task_to_dict(task: Task) -> dict:
    """将 Benchmark 任务序列化为字典"""

    base = task_base_to_dict(task)
    detail = task.benchmark
    if not detail:
        return base
    return {
        **base,
        "task_name": detail.task_name,
        "model_name": detail.model_name,
        "model_endpoint": detail.model_endpoint,
        "model_api_key": "***" if detail.model_api_key else None,
        "benchmark_suite": detail.benchmark_suite,
        "benchmark_config": detail.benchmark_config,
        "result": detail.result,
    }
