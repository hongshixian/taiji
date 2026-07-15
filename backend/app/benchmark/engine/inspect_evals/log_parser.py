"""EvalLog → BenchmarkResult 解析（懒导入 inspect_ai，避免 import 顺序问题）

只依赖 inspect_ai 官方公开 API：
  * inspect_ai.log.read_eval_log
  * EvalLog.results / .stats / .samples / .status / .error
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


_SAMPLES_PREVIEW_LIMIT = 50
_PREVIEW_TEXT_MAX = 500


def parse_eval_log_file(path: Path, engine: str) -> dict:
    """读取一个 .eval / .json log 文件并翻成 BenchmarkResult 的原始 dict。

    返回 dict 由 InspectEvalsEngine.run() 装成 BenchmarkResult。
    """

    from inspect_ai.log import read_eval_log

    log = read_eval_log(str(path))

    # ---- metrics ----
    metrics: dict[str, Any] = {}
    try:
        results = getattr(log, "results", None)
        if results and getattr(results, "scores", None):
            for score in results.scores:
                score_name = getattr(score, "name", None) or getattr(score, "scorer", "score")
                for metric_name, metric_obj in (getattr(score, "metrics", {}) or {}).items():
                    val = getattr(metric_obj, "value", metric_obj)
                    key = metric_name if len(results.scores) == 1 else f"{score_name}.{metric_name}"
                    metrics[key] = val
    except Exception:  # 结果解析失败也不阻断，只是没指标
        pass

    # ---- totals ----
    total = 0
    completed = 0
    failed = 0
    try:
        results = getattr(log, "results", None)
        total = int(getattr(results, "total_samples", 0) or 0)
        completed = int(getattr(results, "completed_samples", 0) or 0)
    except Exception:
        pass

    # ---- usage ----
    usage: dict = {}
    try:
        stats = getattr(log, "stats", None)
        model_usage = getattr(stats, "model_usage", None) if stats else None
        if model_usage:
            # 聚合所有模型的 tokens
            input_tokens = 0
            output_tokens = 0
            total_tokens = 0
            for _model, u in (model_usage.items() if hasattr(model_usage, "items") else []):
                input_tokens += int(getattr(u, "input_tokens", 0) or 0)
                output_tokens += int(getattr(u, "output_tokens", 0) or 0)
                total_tokens += int(getattr(u, "total_tokens", 0) or 0)
            usage = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens or (input_tokens + output_tokens),
            }
    except Exception:
        pass

    # ---- samples preview + grid ----
    samples_preview: list[dict] = []
    sample_grid: list[dict] = []
    try:
        samples = list(getattr(log, "samples", None) or [])
        # 详情预览（前 N 条，带完整文本，供点击方块查看）
        for s in samples[:_SAMPLES_PREVIEW_LIMIT]:
            score = getattr(s, "score", None)
            score_value = None
            score_explain = None
            if score is not None:
                score_value = getattr(score, "value", None)
                score_explain = getattr(score, "explanation", None)
            out = getattr(s, "output", None)
            completion = ""
            if out is not None:
                completion = getattr(out, "completion", "") or ""
            samples_preview.append({
                "id": getattr(s, "id", None),
                "input": _shorten(_stringify(getattr(s, "input", ""))),
                "target": _shorten(_stringify(getattr(s, "target", ""))),
                "output": _shorten(completion),
                "score": _stringify(score_value),
                "explanation": _shorten(_stringify(score_explain)) if score_explain else None,
                "error": _shorten(_stringify(getattr(s, "error", None))) if getattr(s, "error", None) else None,
            })
        # 网格状态（全部样本，仅 id + status，紧凑；供 contribution-graph 式方块展示）
        for s in samples:
            st = _sample_status(s)
            sample_grid.append({"id": getattr(s, "id", None), "status": st})
            if st == "error":
                failed += 1
    except Exception:
        pass

    # ---- status / error ----
    status = getattr(log, "status", "success") or "success"
    error_field = getattr(log, "error", None)
    error_msg = _stringify(error_field) if error_field else None
    if status == "success" and failed > 0 and failed < total:
        status = "partial_success"

    return {
        "metrics": metrics,
        "total_samples": total,
        "completed_samples": completed,
        "failed_samples": failed,
        "model_usage": usage,
        "samples_preview": samples_preview,
        "sample_grid": sample_grid,
        "artifact_paths": [str(path)],
        "engine": engine,
        "engine_metadata": {},
        "status": status,
        "error": error_msg,
    }


def _sample_status(s) -> str:
    """判定单个样本的执行状态（只看是否拿到结果，不看答对答错）：
      error   —— 执行报错，未拿到结果
      success —— 执行成功，拿到了结果（有分数或有输出，不论对错/分值）
      none    —— 未执行 / 无任何产出
    """
    if getattr(s, "error", None):
        return "error"
    score = getattr(s, "score", None)
    if score is not None and getattr(score, "value", None) is not None:
        return "success"
    out = getattr(s, "output", None)
    completion = getattr(out, "completion", None) if out is not None else None
    if completion:
        return "success"
    return "none"


def _stringify(v) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    try:
        return str(v)
    except Exception:
        return "<unrepresentable>"


def _shorten(text: str) -> str:
    if not text:
        return ""
    text = str(text)
    if len(text) <= _PREVIEW_TEXT_MAX:
        return text
    return text[:_PREVIEW_TEXT_MAX] + "…"
