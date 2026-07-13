"""BenchmarkEngine 抽象基类"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.benchmark.context import TaskExecutionContext
from app.benchmark.dto import BenchmarkParams, BenchmarkResult, SuiteDescriptor


class BenchmarkEngine(ABC):
    """所有 Benchmark 执行引擎的抽象基类。"""

    name: str = ""
    version: str = ""

    @abstractmethod
    def list_suites(self) -> list[SuiteDescriptor]:
        """返回该引擎当前提供的 suite 元数据（用于前端下拉与后端校验）。"""

    def get_suite(self, key: str) -> SuiteDescriptor | None:
        for s in self.list_suites():
            if s.key == key:
                return s
        return None

    def supports(self, key: str) -> bool:
        s = self.get_suite(key)
        return bool(s and not s.disabled)

    @abstractmethod
    def run(self, params: BenchmarkParams, ctx: TaskExecutionContext) -> BenchmarkResult:
        """执行一次评测。抛出异常等价于任务失败。"""
