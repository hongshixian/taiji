"""Engine 层模块（BenchmarkEngine ABC + Registry + 具体实现）"""

from app.benchmark.engine.base import BenchmarkEngine
from app.benchmark.engine.registry import engine_registry

__all__ = ["BenchmarkEngine", "engine_registry"]
