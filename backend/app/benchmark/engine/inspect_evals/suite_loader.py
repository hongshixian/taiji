"""suites.yaml → SuiteDescriptor 列表 + execution schema 加载

单独抽出来是为了：
  1) 允许 create_app() 时预加载（避免每次评测都重读磁盘）
  2) 方便 API 层直接暴露 execution_schema 给前端
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from app.benchmark.dto import SuiteDescriptor


_HERE = Path(__file__).parent
_SUITES_YAML = _HERE / "suites.yaml"


@lru_cache(maxsize=1)
def _load_yaml() -> dict:
    with _SUITES_YAML.open("r", encoding="utf-8") as fp:
        return yaml.safe_load(fp)


def load_suites() -> list[SuiteDescriptor]:
    data = _load_yaml()
    result = []
    for raw in data.get("suites", []):
        result.append(SuiteDescriptor(
            key=raw["key"],
            engine="inspect_evals",
            display_name=raw["display_name"],
            category=raw.get("category", "capability"),
            description=raw.get("description", ""),
            needs_judge=raw.get("needs_judge", False),
            judge_arg=raw.get("judge_arg"),
            judge_role_bindings=list(raw.get("judge_role_bindings", []) or []),
            needs_sandbox=raw.get("needs_sandbox", False),
            engine_ref=raw.get("engine_ref", ""),
            default_config=raw.get("default_config", {}) or {},
            config_schema=raw.get("config_schema", {}) or {},
            disabled=raw.get("disabled", False),
            disabled_reason=raw.get("disabled_reason"),
            gated=raw.get("gated", False),
            notes=raw.get("notes"),
        ))
    return result


def default_execution_config() -> dict:
    return dict(_load_yaml().get("default_execution_config", {}) or {})


def execution_schema() -> dict:
    return dict(_load_yaml().get("execution_schema", {}) or {})


# ---------------------------------------------------------------------------
# 少量 suite 额外携带的字段（如 agentharm 的 semantic_judge）从原始 dict 里取
# ---------------------------------------------------------------------------

def suite_raw(key: str) -> dict:
    for raw in _load_yaml().get("suites", []):
        if raw["key"] == key:
            return raw
    return {}
