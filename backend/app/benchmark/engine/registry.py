"""引擎注册表 —— 平台层从这里发现可用的评测引擎"""

from __future__ import annotations

from app.benchmark.dto import SuiteDescriptor
from app.benchmark.engine.base import BenchmarkEngine


class EngineRegistry:
    def __init__(self):
        self._engines: dict[str, BenchmarkEngine] = {}

    def register(self, engine: BenchmarkEngine) -> None:
        if not engine.name:
            raise ValueError("engine.name 必须非空")
        self._engines[engine.name] = engine

    def get(self, name: str) -> BenchmarkEngine | None:
        return self._engines.get(name)

    def all(self) -> list[BenchmarkEngine]:
        return list(self._engines.values())

    # ------------------------------------------------------------------
    # 便捷聚合方法（平台层用）
    # ------------------------------------------------------------------

    def find_engine_for_suite(self, suite_key: str) -> BenchmarkEngine | None:
        for e in self._engines.values():
            if e.get_suite(suite_key) is not None:
                return e
        return None

    def all_suites(self, include_disabled: bool = True) -> list[SuiteDescriptor]:
        result: list[SuiteDescriptor] = []
        for e in self._engines.values():
            for s in e.list_suites():
                if include_disabled or not s.disabled:
                    result.append(s)
        return result

    def enabled_suite_keys(self) -> list[str]:
        return [s.key for s in self.all_suites(include_disabled=False)]

    def all_suite_keys(self) -> list[str]:
        return [s.key for s in self.all_suites(include_disabled=True)]


engine_registry = EngineRegistry()


def discover() -> None:
    """加载并注册所有内置引擎。"""

    # 一期只有 inspect_evals 引擎
    from app.benchmark.engine.inspect_evals.engine import InspectEvalsEngine

    if engine_registry.get(InspectEvalsEngine.name) is None:
        engine_registry.register(InspectEvalsEngine())
