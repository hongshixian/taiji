"""Benchmark 数据集可访问性检测服务

用 inspect_ai 内置 mockllm 模型对某 suite 跑 limit=1：
  * 数据集能加载完（status=success）=> 可访问（网络连通 + gated 权限 OK）；
  * gated 无权限 / 网络失败 / 数据集缺失 => 加载阶段抛错 => 检测失败。

覆盖所有数据源（HF gated / 普通 HF / GitHub raw / 包内置），与真正评测走同一 HF 环境。
mockllm 返回固定输出，故无需真实模型/评委——needs_judge 的 suite 把评委 role 也绑到 mockllm。
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from app.benchmark.engine.inspect_evals.env import build_hf_env
from app.benchmark.engine.registry import engine_registry
from app.services.benchmark_service import _hf_cache_root
from app.services.system_setting_service import get_setting_value
from app.utils.logger import get_logger


logger = get_logger(__name__)

_CHECK_LIMIT = 1
_MOCK_MODEL = "mockllm/model"


def run_accessibility_check(suite_key: str) -> tuple[bool, str | None, int, int | None]:
    """跑一次 mockllm limit=1，返回 (ok, error, elapsed_ms, sample_count)。须在 app context 内调用。"""

    started = time.monotonic()

    suite = None
    for s in engine_registry.all_suites(include_disabled=True):
        if s.key == suite_key:
            suite = s
            break
    if suite is None:
        return False, f"未知 suite：{suite_key}", 0, None
    if not suite.engine_ref:
        return False, f"suite {suite_key} 未配置 engine_ref", 0, None
    if suite.needs_sandbox:
        return False, "该 suite 需要 Docker sandbox，暂不支持可达性检测", 0, None

    hf_token = get_setting_value("integrations.hf_token") or None
    log_dir = _hf_cache_root() / "_access_checks" / suite_key
    env = build_hf_env(_hf_cache_root(), hf_token)

    prev_env = {k: os.environ.get(k) for k in env}
    sample_count: int | None = None
    try:
        os.environ.update(env)
        ok, error, sample_count = _invoke(suite, str(log_dir))
    except Exception as exc:  # noqa: BLE001
        logger.warning("可达性检测异常 %s: %s", suite_key, exc)
        ok, error = False, f"{type(exc).__name__}: {exc}"[:800]
    finally:
        for k, prev in prev_env.items():
            if prev is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = prev

    return ok, error, int((time.monotonic() - started) * 1000), sample_count


def _invoke(suite, log_dir: str) -> tuple[bool, str | None]:
    from inspect_ai import eval as inspect_eval
    from app.benchmark.engine.inspect_evals.suite_loader import suite_raw

    kwargs: dict = {
        "tasks": suite.engine_ref,
        "model": _MOCK_MODEL,
        "limit": _CHECK_LIMIT,
        "log_dir": log_dir,
        "log_format": "eval",
        "display": "none",
        "fail_on_error": False,  # 让评测跑完以便拿到样本，再自行判定“数据集是否可达”
        "retry_on_error": 0,
    }
    # 需评委的 suite：把评委也绑到 mockllm，避免因缺评委在 scoring 阶段回退到
    # 默认 OpenAI 报错（假阴性）。评委有两种传法，都要覆盖：
    #   1) judge_role_bindings：通过 model_roles 传
    #   2) judge_arg / judge_arg_extra：通过 task_args 传（suite 函数参数）
    if suite.needs_judge:
        if suite.judge_role_bindings:
            kwargs["model_roles"] = {role: _MOCK_MODEL for role in suite.judge_role_bindings}
        raw = suite_raw(suite.key) or {}
        task_args: dict = {}
        for arg_key in (suite.judge_arg, raw.get("judge_arg_extra")):
            if arg_key:
                task_args[arg_key] = _MOCK_MODEL
        if task_args:
            kwargs["task_args"] = task_args

    logs = inspect_eval(**kwargs)
    if not logs:
        return False, "未产生 eval log", None
    log = logs[0]

    # 数据集样本总数：即使 limit=1，eval log 的 dataset.samples 记录了完整数据集大小
    sample_count: int | None = None
    try:
        ds = getattr(getattr(log, "eval", None), "dataset", None)
        n = getattr(ds, "samples", None) if ds is not None else None
        if isinstance(n, int) and n > 0:
            sample_count = n
    except Exception:  # noqa: BLE001
        pass

    # 判定标准是「数据集能否加载」，而非「整体评测成功」。
    # mockllm 返回固定文本，某些 suite 的 grader（如 tool-call 评分）会在 scoring
    # 阶段失败，但这与数据集可达性无关。只要至少一条样本被成功加载并产出 output，
    # 即视为数据集可访问；否则（0 样本 / 加载阶段报错）判为不可达。
    samples = list(getattr(log, "samples", None) or [])
    produced = any(
        getattr(getattr(s, "output", None), "completion", None) is not None
        for s in samples
    )
    if samples and produced:
        return True, None, sample_count

    status = getattr(log, "status", None)
    err = getattr(log, "error", None)
    if err:
        return False, str(err)[:800], sample_count
    if not samples:
        return False, "数据集未加载出任何样本", sample_count
    return False, f"状态：{status}", sample_count
