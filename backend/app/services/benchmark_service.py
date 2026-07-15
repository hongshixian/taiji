"""Benchmark 测评任务业务逻辑（真正驱动引擎）"""

from __future__ import annotations

from pathlib import Path

from flask import current_app

from app import db
from app.benchmark.context import build_context
from app.benchmark.dto import BenchmarkParams, ModelSpec
from app.benchmark.engine.registry import engine_registry
from app.models.benchmark_task import BenchmarkTask
from app.models.model_config import ModelConfig
from app.models.task import Task, TaskType
from app.services.model_config_service import model_config_to_dict
from app.services.system_setting_service import get_setting_value
from app.services.task_log_service import create_task_logger
from app.services.task_service import (
    create_task_record,
    mark_failed,
    mark_running,
    mark_success,
    task_base_to_dict,
)
from app.utils.errors import BusinessError, ErrorCode
from app.utils.logger import get_logger


logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 创建任务
# ---------------------------------------------------------------------------

def create_benchmark_task(
    *,
    user_id: int,
    task_name: str,
    notes: str | None,
    benchmark_suite: str,
    target_model_id: int,
    judge_model_id: int | None,
    execution_config: dict | None,
    suite_config: dict | None,
) -> Task:
    target = db.session.get(ModelConfig, target_model_id)
    if not target:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, f"被测模型不存在：{target_model_id}")
    if judge_model_id:
        judge = db.session.get(ModelConfig, judge_model_id)
        if not judge:
            raise BusinessError(ErrorCode.VALIDATION_ERROR, f"评委模型不存在：{judge_model_id}")

    engine = engine_registry.find_engine_for_suite(benchmark_suite)
    if engine is None:
        raise BusinessError(ErrorCode.VALIDATION_ERROR, f"未知评测集：{benchmark_suite}")
    suite = engine.get_suite(benchmark_suite)
    if suite is None or suite.disabled:
        reason = suite.disabled_reason if suite else "未收录"
        raise BusinessError(ErrorCode.VALIDATION_ERROR, f"评测集不可用：{reason}")

    task = create_task_record(user_id, TaskType.BENCHMARK)
    detail = BenchmarkTask(
        tenant_id=task.tenant_id,
        task_id=task.id,
        task_name=task_name,
        notes=(notes or None),
        engine=engine.name,
        benchmark_suite=benchmark_suite,
        target_model_id=target_model_id,
        judge_model_id=judge_model_id,
        benchmark_config={
            "execution_config": execution_config or {},
            "suite_config": suite_config or {},
        },
    )
    db.session.add(detail)
    db.session.commit()
    return task


# ---------------------------------------------------------------------------
# 执行任务（Celery worker 里被调用）
# ---------------------------------------------------------------------------

def execute_benchmark(task_id: int) -> None:
    task = db.session.get(Task, task_id)
    if not task or task.task_type != TaskType.BENCHMARK:
        logger.error(f"Benchmark 任务 {task_id} 不存在")
        return
    detail: BenchmarkTask | None = task.benchmark
    if detail is None:
        logger.error(f"Benchmark 任务 {task_id} 缺少详情记录")
        mark_failed(task, "缺少 BenchmarkTask 详情记录")
        return

    task_logger = create_task_logger(task)
    db.session.commit()  # 确保 log_path 落库

    try:
        mark_running(task)
        task_logger.info(
            step="start",
            event="benchmark_started",
            msg=f"开始执行 {detail.benchmark_suite}",
            data={
                "engine": detail.engine,
                "suite": detail.benchmark_suite,
                "target_model_id": detail.target_model_id,
                "judge_model_id": detail.judge_model_id,
            },
        )

        engine = engine_registry.get(detail.engine)
        if engine is None:
            raise RuntimeError(f"未知评测引擎：{detail.engine}")
        suite = engine.get_suite(detail.benchmark_suite)
        if suite is None:
            raise RuntimeError(f"suite 缺失：{detail.benchmark_suite}")

        target_model = _model_config_to_spec(detail.target_model)
        judge_model = _model_config_to_spec(detail.judge_model) if detail.judge_model else None

        cfg = detail.benchmark_config or {}
        params = BenchmarkParams(
            suite=suite,
            target_model=target_model,
            judge_model=judge_model,
            execution_config=cfg.get("execution_config") or {},
            suite_config=cfg.get("suite_config") or {},
            hf_token=get_setting_value("integrations.hf_token") or None,
        )

        workspace_root = _artifact_root() / f"tenant_{task.tenant_id}" / f"task_{task.id}"
        hf_cache = _hf_cache_root()
        ctx = build_context(
            task_id=task.id,
            tenant_id=task.tenant_id,
            workspace=workspace_root,
            hf_cache_dir=hf_cache,
            task_logger=task_logger,
        )

        result = engine.run(params, ctx)

        detail.result = result.to_dict()
        db.session.commit()

        if result.status == "failed":
            mark_failed(task, result.error or "评测失败")
            task_logger.error(
                step="end",
                event="benchmark_failed",
                msg="评测失败",
                data={"error": result.error},
            )
        else:
            mark_success(task)
            task_logger.info(
                step="end",
                event="benchmark_succeeded",
                msg=f"评测完成（{result.status}）",
                data={
                    "status": result.status,
                    "metrics": result.metrics,
                    "completed": result.completed_samples,
                    "total": result.total_samples,
                },
            )
    except Exception as exc:
        logger.exception(f"Benchmark 任务 {task_id} 异常")
        try:
            task_logger.error(step="end", event="benchmark_exception", msg=str(exc))
        except Exception:
            pass
        mark_failed(task, f"{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# 序列化
# ---------------------------------------------------------------------------

def benchmark_task_to_dict(task: Task) -> dict:
    base = task_base_to_dict(task)
    detail: BenchmarkTask | None = task.benchmark
    if not detail:
        return base

    return {
        **base,
        "task_name": detail.task_name,
        "notes": detail.notes,
        "engine": detail.engine,
        "benchmark_suite": detail.benchmark_suite,
        "target_model_id": detail.target_model_id,
        "judge_model_id": detail.judge_model_id,
        "target_model": _safe_model_dict(detail.target_model),
        "judge_model": _safe_model_dict(detail.judge_model),
        "benchmark_config": detail.benchmark_config,
        "result": detail.result,
        "progress": task.progress,
    }


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------

def _model_config_to_spec(m: ModelConfig | None) -> ModelSpec | None:
    if m is None:
        return None
    return ModelSpec(
        id=m.id,
        display_name=m.display_name,
        model_name=m.model_name,
        api_base_url=m.api_base_url,
        api_protocol=m.api_protocol,
        api_key=m.api_key,
        extra_params=dict(m.extra_params or {}),
    )


def _safe_model_dict(m: ModelConfig | None) -> dict | None:
    if m is None:
        return None
    d = model_config_to_dict(m)
    d.pop("api_key", None)
    return d


def _artifact_root() -> Path:
    root = Path(current_app.config.get("BENCHMARK_ARTIFACT_ROOT") or
                Path(current_app.config["TASK_LOG_ROOT"]) / "benchmark_artifacts")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _hf_cache_root() -> Path:
    root = Path(current_app.config.get("HF_CACHE_ROOT") or
                Path(current_app.config["TASK_LOG_ROOT"]).parent / "hf_cache")
    root.mkdir(parents=True, exist_ok=True)
    return root
