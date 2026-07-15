"""Benchmark 评测抽象层

分三层：
  Layer 1  Handler       — 任务生命周期（app/handlers/benchmark.py）
  Layer 2  Engine        — 引擎接口，本模块负责（BenchmarkEngine ABC + Registry）
  Layer 3  底层 SDK      — 目前是 inspect_ai / inspect_evals

Engine 层的核心承诺：
  * 只依赖 dto 与 context（不依赖 ORM / Flask / Celery）
  * 引擎特定 quirks（inspect_ai 的模型 spec、参数名、role binding）关在实现类内部
  * SuiteDescriptor 是引擎无关的 suite 元数据，供前端/后端共同消费
"""

from app.benchmark.dto import (
    BenchmarkParams,
    BenchmarkResult,
    ModelSpec,
    SuiteDescriptor,
)
from app.benchmark.context import (
    ProgressReporter,
    TaskExecutionContext,
)
from app.benchmark.engine.base import BenchmarkEngine
from app.benchmark.engine.registry import engine_registry

__all__ = [
    "BenchmarkParams",
    "BenchmarkResult",
    "ModelSpec",
    "SuiteDescriptor",
    "ProgressReporter",
    "TaskExecutionContext",
    "BenchmarkEngine",
    "engine_registry",
]
