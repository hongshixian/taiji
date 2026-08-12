"""Benchmark 执行范围配置测试。"""

from types import SimpleNamespace

from app.benchmark.dto import BenchmarkParams, ModelSpec, SuiteDescriptor
from app.benchmark.engine.inspect_evals.engine import InspectEvalsEngine
from app.benchmark.engine.inspect_evals.hooks import _ProgressState, _update_total_from_event
from app.benchmark.engine.inspect_evals.suite_loader import default_execution_config


def _params(execution_config: dict, *, sample_count: int | None = None) -> BenchmarkParams:
    return BenchmarkParams(
        suite=SuiteDescriptor(
            key="test_suite",
            engine="inspect_evals",
            display_name="Test Suite",
            category="capability",
            sample_count=sample_count,
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


def test_full_execution_uses_suite_count_only_as_progress_hint():
    engine = InspectEvalsEngine.__new__(InspectEvalsEngine)
    params = _params({}, sample_count=1273)
    merged = engine._merge_exec_config(params)

    assert engine._progress_total_hint(params.suite, merged) == 1273
    assert "limit" not in merged


def test_partial_execution_uses_limit_as_progress_hint():
    engine = InspectEvalsEngine.__new__(InspectEvalsEngine)
    params = _params({"limit": 20}, sample_count=1273)
    merged = engine._merge_exec_config(params)

    assert engine._progress_total_hint(params.suite, merged) == 20


def test_progress_without_known_total_does_not_fake_completed_as_total():
    state = _ProgressState(progress=None, total_hint=0, logger=None)
    state.completed = 6

    assert _update_total_from_event(state, SimpleNamespace()) == 0


def test_progress_accepts_runtime_discovered_total():
    state = _ProgressState(progress=None, total_hint=0, logger=None)

    assert _update_total_from_event(state, SimpleNamespace(total_samples=1273)) == 1273


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
