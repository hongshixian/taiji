"""ModelConfig / ModelSpec → inspect_ai 可用的字符串 spec + 环境变量

inspect_ai 的 model 语法：<provider>/<model_name>
  * OpenAI 系: "openai/gpt-4o-mini" (走官方 OpenAI SDK)
  * Anthropic: "anthropic/claude-...."
  * Gemini:    "google/gemini-..."
  * Ollama:    "ollama/..."
  * 自建/兼容: "openai-api/<name>"（通用 OpenAI 兼容协议，任意 base_url）
"""

from __future__ import annotations

from contextlib import contextmanager
import os

from app.benchmark.dto import ModelSpec


# taiji 的 api_protocol 到 inspect_ai provider 前缀的映射
_PROVIDER_MAP = {
    "openai": "openai",
    "anthropic": "anthropic",
    "gemini": "google",
    "ollama": "ollama",
    "custom": "openai-api",  # 一律走 openai 兼容协议
    "mockllm": "mockllm",    # 内建 mock provider（供开发/测试用）
}


def model_spec_to_inspect_model(spec: ModelSpec) -> str:
    """把 ModelSpec 翻译成 inspect_ai 认识的 model 字符串。"""

    provider = _PROVIDER_MAP.get(spec.api_protocol, "openai-api")
    if provider == "mockllm":
        return "mockllm/model"  # inspect_ai 只承认 mockllm/model
    return f"{provider}/{spec.model_name}"


def _env_prefix(spec: ModelSpec) -> tuple[str, str]:
    """返回 (BASE_URL 环境变量名, API_KEY 环境变量名)"""

    protocol = spec.api_protocol
    if protocol == "openai":
        return "OPENAI_BASE_URL", "OPENAI_API_KEY"
    if protocol == "anthropic":
        return "ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY"
    if protocol == "gemini":
        # inspect_ai 的 google provider 用 GOOGLE_API_KEY
        return "GOOGLE_BASE_URL", "GOOGLE_API_KEY"
    if protocol == "ollama":
        return "OLLAMA_BASE_URL", "OLLAMA_API_KEY"
    # openai 兼容协议 → 用统一环境变量前缀 INSPECT_EVAL_MODEL_BASE_URL / _API_KEY
    return "OPENAI_BASE_URL", "OPENAI_API_KEY"


@contextmanager
def with_model_env(specs: list[ModelSpec]):
    """在 with 块里临时设置模型鉴权环境变量，退出时恢复。

    多个 spec 如果指向不同 provider，各自设置一份；如果指向同一 provider（如都是
    openai 兼容），后写入的会覆盖前一份 —— 因此 spec 顺序：被测模型在前，评委在后
    时评委生效。**要求调用方保证同一 provider 下的所有 spec 共用同一套鉴权**。
    """

    saved: dict[str, str | None] = {}
    try:
        for spec in specs:
            base_url_env, api_key_env = _env_prefix(spec)
            for key, val in (
                (base_url_env, spec.api_base_url),
                (api_key_env, spec.api_key or ""),
            ):
                if key not in saved:
                    saved[key] = os.environ.get(key)
                os.environ[key] = val or ""
        yield
    finally:
        for key, prev in saved.items():
            if prev is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = prev


def build_generate_config(spec: ModelSpec) -> dict:
    """从 ModelSpec.extra_params 里抽出 inspect_ai GenerateConfig 关心的字段。"""

    extra = spec.extra_params or {}
    keys = ("temperature", "top_p", "top_k", "max_tokens", "stop_seqs",
            "stop_sequences", "presence_penalty", "frequency_penalty", "seed")
    out: dict = {}
    for k in keys:
        if k in extra and extra[k] is not None:
            # inspect_ai 用 stop_seqs（列表），前端可能起名 stop_sequences
            out_key = "stop_seqs" if k == "stop_sequences" else k
            out[out_key] = extra[k]
    return out
