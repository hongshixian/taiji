"""Benchmark 执行范围配置测试。"""

from app.benchmark.dto import BenchmarkParams, ModelSpec, SuiteDescriptor
from app.benchmark.engine.inspect_evals.engine import InspectEvalsEngine
from app.benchmark.engine.inspect_evals.suite_loader import default_execution_config


def _params(execution_config: dict) -> BenchmarkParams:
    return BenchmarkParams(
        suite=SuiteDescriptor(
            key="test_suite",
            engine="inspect_evals",
            display_name="Test Suite",
            category="capability",
        ),
        target_model=ModelSpec(
            id=1,
            display_name="Test Model",
            model_name="test-model",
            api_base_url="https://example.test/v1",
            api_protocol="openai",
        ),
        judge_model=None,
        execution_config=execution_config,
        suite_config={},
    )


def test_default_execution_config_has_no_sample_limit():
    assert "limit" not in default_execution_config()


def test_explicit_null_limit_removes_inherited_limit(monkeypatch):
    monkeypatch.setattr(
        "app.benchmark.engine.inspect_evals.engine.default_execution_config",
        lambda: {"limit": 20, "epochs": 1, "max_connections": 10},
    )

    engine = InspectEvalsEngine.__new__(InspectEvalsEngine)
    merged = engine._merge_exec_config(_params({"limit": None}))

    assert "limit" not in merged


def test_partial_execution_keeps_requested_limit():
    engine = InspectEvalsEngine.__new__(InspectEvalsEngine)

    merged = engine._merge_exec_config(_params({"limit": 20}))

    assert merged["limit"] == 20


def test_full_execution_does_not_pass_limit_to_inspect(monkeypatch, tmp_path):
    captured = {}

    def fake_eval(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("inspect_ai.eval", fake_eval)
    engine = InspectEvalsEngine.__new__(InspectEvalsEngine)
    params = _params({})

    engine._invoke_inspect(
        suite=params.suite,
        params=params,
        task_args={},
        model_roles={},
        exec_cfg={"epochs": 1, "max_connections": 10},
        log_dir=tmp_path,
    )

    assert "limit" not in captured
