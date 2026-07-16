"""ModelConfig / ModelSpec → inspect_ai 可用的字符串 spec + 环境变量

inspect_ai 的 model 语法：<provider>/<model_name>

为什么 openai / custom / ollama 都走 `openai-api` 而不是 `openai`：
  * inspect_ai 的 `openai` provider 默认走 OpenAI 新的 Responses API
    (POST /responses)，第三方 litellm/OpenAI 兼容网关通常只实现
    /chat/completions，会 404。
  * `openai-api/<service>/<model>` 通道强制走标准 /chat/completions，且用
    <SERVICE>_BASE_URL / <SERVICE>_API_KEY 环境变量鉴权，专为兼容网关设计。
  * 用 svc{id} 作为唯一 service 名，保证同一次评测里被测模型与评委模型（可能
    base_url / key 不同）各自的环境变量不互相覆盖。
"""

from __future__ import annotations

from contextlib import contextmanager
import os

from app.benchmark.dto import ModelSpec


def _service_name(spec: ModelSpec) -> str:
    """为 openai-api 通道生成唯一 service 名（纯字母数字，避免环境变量冲突）。"""
    return f"svc{spec.id}"


def _service_env_names(service: str) -> tuple[str, str]:
    up = service.upper()
    return f"{up}_BASE_URL", f"{up}_API_KEY"


def model_spec_to_inspect_model(spec: ModelSpec) -> str:
    """把 ModelSpec 翻译成 inspect_ai 认识的 model 字符串。"""

    protocol = (spec.api_protocol or "").lower()
    if protocol == "mockllm":
        return "mockllm/model"  # inspect_ai 只承认 mockllm/model
    if protocol == "anthropic":
        return f"anthropic/{spec.model_name}"
    if protocol == "gemini":
        return f"google/{spec.model_name}"
    # openai / custom / ollama / 其它 → 统一走 openai 兼容通道
    service = _service_name(spec)
    return f"openai-api/{service}/{spec.model_name}"


def uses_openai_compatible(spec: ModelSpec) -> bool:
    """该 spec 是否走 openai-api（OpenAI-compatible /chat/completions）通道。

    只有这个通道的 provider 才接受 `stream` 初始化参数（openai_compatible.py）。
    anthropic / gemini / mockllm 有各自机制，不注入 stream。
    """
    protocol = (spec.api_protocol or "").lower()
    return protocol not in ("mockllm", "anthropic", "gemini")


def env_overrides_for_spec(spec: ModelSpec) -> dict[str, str]:
    """返回该 spec 需要设置的鉴权环境变量键值对。"""

    protocol = (spec.api_protocol or "").lower()
    if protocol == "mockllm":
        return {}
    if protocol == "anthropic":
        return {
            "ANTHROPIC_BASE_URL": spec.api_base_url or "",
            "ANTHROPIC_API_KEY": spec.api_key or "",
        }
    if protocol == "gemini":
        env = {"GOOGLE_API_KEY": spec.api_key or ""}
        if spec.api_base_url:
            env["GOOGLE_BASE_URL"] = spec.api_base_url
        return env
    # openai / custom / ollama → openai-api 通道，唯一 service 前缀
    service = _service_name(spec)
    base_env, key_env = _service_env_names(service)
    return {
        base_env: spec.api_base_url or "",
        key_env: spec.api_key or "",
    }


@contextmanager
def with_model_env(specs: list[ModelSpec]):
    """在 with 块里临时设置模型鉴权环境变量，退出时恢复。

    openai-api 通道用 svc{id} 唯一 service，因此多个模型的环境变量不会互相覆盖。
    anthropic / gemini 用全局环境变量，若同一次评测里出现两个同 provider 但不同
    base_url 的模型，后者会覆盖前者（一期评委通常与被测共用同一网关，可接受）。
    """

    saved: dict[str, str | None] = {}
    try:
        for spec in specs:
            for key, val in env_overrides_for_spec(spec).items():
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
