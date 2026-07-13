"""InspectEvalsEngine —— 一期唯一的 BenchmarkEngine 实现

关键设计：
  * 所有 inspect_ai 特有的行为（model spec 拼接、model role、评委参数名、EvalLog 解析）
    都关在这个包里，暴露给 taiji 的只是 BenchmarkEngine 接口。
  * 参数翻译流程：
        SuiteDescriptor + BenchmarkParams
             │
             ▼
      1) task_id  = engine_ref  ("inspect_evals/mmlu")
      2) model    = target_model → "openai-api/<name>"，同时设 env
      3) task_args = {
             判断 needs_judge + judge_arg → {"judge_llm": "openai/gpt-4o", ...}
             合并 suite_config
         }
      4) model_roles = {role: judge_spec for role in judge_role_bindings}
      5) limit / epochs / max_connections / GenerateConfig 从 execution_config 取
"""

from __future__ import annotations

import os
from importlib import metadata as _metadata
from pathlib import Path

from app.benchmark.context import TaskExecutionContext
from app.benchmark.dto import (
    BenchmarkParams,
    BenchmarkResult,
    SuiteDescriptor,
)
from app.benchmark.engine.base import BenchmarkEngine
from app.benchmark.engine.inspect_evals import hooks as taiji_hooks
from app.benchmark.engine.inspect_evals.log_parser import parse_eval_log_file
from app.benchmark.engine.inspect_evals.suite_loader import (
    default_execution_config,
    load_suites,
    suite_raw,
)
from app.benchmark.engine.inspect_evals.translate import (
    build_generate_config,
    model_spec_to_inspect_model,
    with_model_env,
)


class InspectEvalsEngine(BenchmarkEngine):
    name = "inspect_evals"

    def __init__(self):
        self._suites = load_suites()
        try:
            self.version = _metadata.version("inspect-evals")
        except Exception:
            self.version = "unknown"

    # ------------------------------------------------------------------

    def list_suites(self) -> list[SuiteDescriptor]:
        return list(self._suites)

    # ------------------------------------------------------------------
    # 执行入口
    # ------------------------------------------------------------------

    def run(self, params: BenchmarkParams, ctx: TaskExecutionContext) -> BenchmarkResult:
        suite = params.suite
        if suite.disabled:
            raise RuntimeError(f"suite {suite.key} 已被禁用：{suite.disabled_reason}")
        if not suite.engine_ref:
            raise RuntimeError(f"suite {suite.key} 未配置 engine_ref")

        # 1) 环境准备
        env_overrides = self._prepare_env(ctx, params)
        specs = [params.target_model]
        if params.judge_model:
            specs.append(params.judge_model)

        # 2) 参数翻译
        task_args = self._build_task_args(params)
        model_roles = self._build_model_roles(params)
        exec_cfg = self._merge_exec_config(params)

        # 3) 惰性注册 hook
        taiji_hooks.ensure_registered(ctx.logger)
        taiji_hooks.bind(ctx.progress, total_hint=int(exec_cfg.get("limit") or 0), logger=ctx.logger)

        # 4) 记录一条 run_started 日志
        ctx.logger.info(
            step="run",
            event="engine_started",
            msg=f"启动 inspect_evals：{suite.key}",
            data={
                "engine_ref": suite.engine_ref,
                "target_model": model_spec_to_inspect_model(params.target_model),
                "judge_model": model_spec_to_inspect_model(params.judge_model) if params.judge_model else None,
                "limit": exec_cfg.get("limit"),
                "epochs": exec_cfg.get("epochs"),
                "max_connections": exec_cfg.get("max_connections"),
                "task_args": {k: v for k, v in task_args.items() if k not in _SECRET_KEYS},
                "model_roles": {k: v for k, v in model_roles.items()},
            },
        )

        # 5) 真正调 inspect_ai
        log_dir = ctx.workspace / "inspect_logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        prev_env = {k: os.environ.get(k) for k in env_overrides}
        try:
            os.environ.update(env_overrides)
            with with_model_env(specs):
                logs = self._invoke_inspect(
                    suite=suite,
                    params=params,
                    task_args=task_args,
                    model_roles=model_roles,
                    exec_cfg=exec_cfg,
                    log_dir=log_dir,
                )
        finally:
            taiji_hooks.release()
            for k, prev in prev_env.items():
                if prev is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = prev

        # 6) 解析结果（取第一份 log 文件）
        artifact = self._pick_first_log(log_dir)
        engine_id = f"{self.name}@{self.version}"
        if artifact is None:
            ctx.logger.warn(
                step="run",
                event="no_log_found",
                msg="未找到 .eval log 文件，返回空结果",
                data={"log_dir": str(log_dir)},
            )
            return BenchmarkResult(
                metrics={},
                total_samples=0,
                completed_samples=0,
                engine=engine_id,
                status="failed",
                error="no log file produced",
            )

        raw = parse_eval_log_file(artifact, engine_id)
        result = BenchmarkResult(
            metrics=raw["metrics"],
            total_samples=raw["total_samples"],
            completed_samples=raw["completed_samples"],
            failed_samples=raw["failed_samples"],
            model_usage=raw["model_usage"],
            samples_preview=raw["samples_preview"],
            artifact_paths=raw["artifact_paths"],
            engine=engine_id,
            engine_metadata=raw["engine_metadata"],
            status=raw["status"],
            error=raw["error"],
        )

        ctx.logger.info(
            step="run",
            event="engine_finished",
            msg="inspect_evals 执行完成",
            data={
                "status": result.status,
                "metrics": result.metrics,
                "total": result.total_samples,
                "completed": result.completed_samples,
                "failed": result.failed_samples,
            },
        )
        return result

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _prepare_env(self, ctx: TaskExecutionContext, params: BenchmarkParams) -> dict:
        """构造要覆盖的环境变量（HF 缓存路径、HF token、镜像）。"""

        env = {
            "HF_HOME": str(ctx.hf_cache_dir),
            "HF_DATASETS_CACHE": str(ctx.hf_cache_dir / "datasets"),
            "HUGGINGFACE_HUB_CACHE": str(ctx.hf_cache_dir / "hub"),
        }
        # HF 镜像
        hf_endpoint = os.environ.get("HF_ENDPOINT", "https://hf-mirror.com")
        env["HF_ENDPOINT"] = hf_endpoint
        # HF token（gated 数据集用）
        if params.hf_token:
            env["HF_TOKEN"] = params.hf_token
            env["HUGGING_FACE_HUB_TOKEN"] = params.hf_token
        # ctx 里可能有额外注入
        env.update(ctx.extra_env or {})
        return env

    def _build_task_args(self, params: BenchmarkParams) -> dict:
        """把评委模型 spec 塞进 task_args；再合并用户提交的 suite_config。"""

        args: dict = {}
        suite = params.suite
        raw = suite_raw(suite.key)

        if suite.needs_judge and params.judge_model:
            judge_spec = model_spec_to_inspect_model(params.judge_model)
            if suite.judge_arg:
                args[suite.judge_arg] = judge_spec
            # agentharm 双评委：suites.yaml 里可以再声明一个 judge_arg_extra
            extra_arg = raw.get("judge_arg_extra")
            if extra_arg:
                args[extra_arg] = judge_spec

        # 合并 suite 特有配置
        if params.suite_config:
            for k, v in params.suite_config.items():
                if v is None:
                    continue
                args[k] = v
        return args

    def _build_model_roles(self, params: BenchmarkParams) -> dict:
        roles: dict = {}
        suite = params.suite
        if params.judge_model and suite.judge_role_bindings:
            spec = model_spec_to_inspect_model(params.judge_model)
            for role in suite.judge_role_bindings:
                roles[role] = spec
        return roles

    def _merge_exec_config(self, params: BenchmarkParams) -> dict:
        exec_cfg = default_execution_config()
        exec_cfg.update(params.suite.default_config.get("execution", {}) or {})
        exec_cfg.update({k: v for k, v in (params.execution_config or {}).items() if v is not None})
        return exec_cfg

    def _invoke_inspect(
        self,
        *,
        suite: SuiteDescriptor,
        params: BenchmarkParams,
        task_args: dict,
        model_roles: dict,
        exec_cfg: dict,
        log_dir: Path,
    ):
        """调用 inspect_ai.eval —— 单独一层是为了方便测试打桩。"""

        from inspect_ai import eval as inspect_eval

        target_model = model_spec_to_inspect_model(params.target_model)
        generate_cfg = build_generate_config(params.target_model)

        limit = exec_cfg.get("limit")
        epochs = exec_cfg.get("epochs") or 1
        max_connections = exec_cfg.get("max_connections") or 10

        kwargs: dict = {
            "tasks": suite.engine_ref,
            "model": target_model,
            "log_dir": str(log_dir),
            "log_format": "eval",
            "epochs": epochs,
            "max_connections": max_connections,
            "fail_on_error": False,   # sample 失败继续
            "retry_on_error": 1,      # sample 级别重试一次
            "display": "plain",
        }
        if task_args:
            kwargs["task_args"] = task_args
        if model_roles:
            kwargs["model_roles"] = model_roles
        if limit is not None:
            kwargs["limit"] = limit
        for k, v in generate_cfg.items():
            kwargs[k] = v

        return inspect_eval(**kwargs)

    def _pick_first_log(self, log_dir: Path) -> Path | None:
        candidates = sorted(log_dir.glob("*.eval"))
        if not candidates:
            candidates = sorted(log_dir.glob("*.json"))
        return candidates[0] if candidates else None


_SECRET_KEYS = {"api_key", "hf_token"}
