"""模型配置连通性测试服务

设计原则：
  * 一个统一的 test_model_config(m) 函数，无论 provider 如何，都发出一次极简的
    "hello" 请求，返回 { ok, latency_ms, sample_output, error, model_info }。
  * 不依赖 inspect_ai 的 hook 生命周期（那是评测用的），直接走 provider 各自的
    Python SDK：openai / anthropic / google-genai / ollama，以及 mockllm 的
    模拟返回。
  * 所有敏感值（api_key）都不下发前端；只回执"是否成功 + 简短输出 + 错误摘要"。
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from app.models.model_config import ModelConfig
from app.utils.logger import get_logger


logger = get_logger(__name__)


@dataclass
class ModelTestResult:
    ok: bool
    latency_ms: int
    sample_output: str | None
    error: str | None
    provider: str
    model: str

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "latency_ms": self.latency_ms,
            "sample_output": self.sample_output,
            "error": self.error,
            "provider": self.provider,
            "model": self.model,
        }


# ---------------------------------------------------------------------------

_TEST_PROMPT = "Reply with only the word 'ok'."
_TEST_MAX_TOKENS = 16
_TEST_TIMEOUT_SEC = 20


def test_model_config(m: ModelConfig) -> ModelTestResult:
    """对一个 ModelConfig 发一次实际的 chat completion 请求。"""

    protocol = (m.api_protocol or "").lower()
    started = time.monotonic()
    try:
        if protocol == "openai" or protocol == "custom":
            text = _test_openai(m)
        elif protocol == "anthropic":
            text = _test_anthropic(m)
        elif protocol == "gemini":
            text = _test_gemini(m)
        elif protocol == "ollama":
            text = _test_ollama(m)
        elif protocol == "mockllm":
            text = _test_mockllm(m)
        else:
            raise RuntimeError(f"未支持的 protocol: {m.api_protocol}")
        return ModelTestResult(
            ok=True,
            latency_ms=int((time.monotonic() - started) * 1000),
            sample_output=(text or "")[:200],
            error=None,
            provider=m.api_protocol,
            model=m.model_name,
        )
    except Exception as exc:
        logger.warning("模型测试失败 %s: %s", m.display_name, exc)
        return ModelTestResult(
            ok=False,
            latency_ms=int((time.monotonic() - started) * 1000),
            sample_output=None,
            error=f"{type(exc).__name__}: {exc}"[:500],
            provider=m.api_protocol,
            model=m.model_name,
        )


# ---------------------------------------------------------------------------
# Provider 实现
# ---------------------------------------------------------------------------

def _test_openai(m: ModelConfig) -> str:
    """OpenAI 兼容协议（含 DeepSeek/Kimi/Qwen 等）"""
    from openai import OpenAI

    client = OpenAI(
        api_key=(m.api_key or "sk-placeholder"),
        base_url=m.api_base_url,
        timeout=_TEST_TIMEOUT_SEC,
        max_retries=0,
    )
    kwargs = dict(
        model=m.model_name,
        messages=[{"role": "user", "content": _TEST_PROMPT}],
        max_tokens=_TEST_MAX_TOKENS,
    )
    _merge_generate_args(kwargs, m.extra_params, keys=("temperature", "top_p"))
    resp = client.chat.completions.create(**kwargs)
    return _extract_openai_text(resp)


def _test_anthropic(m: ModelConfig) -> str:
    from anthropic import Anthropic

    client = Anthropic(
        api_key=(m.api_key or ""),
        base_url=m.api_base_url or None,
        timeout=_TEST_TIMEOUT_SEC,
        max_retries=0,
    )
    kwargs = dict(
        model=m.model_name,
        max_tokens=_TEST_MAX_TOKENS,
        messages=[{"role": "user", "content": _TEST_PROMPT}],
    )
    _merge_generate_args(kwargs, m.extra_params, keys=("temperature", "top_p"))
    resp = client.messages.create(**kwargs)
    if resp.content and getattr(resp.content[0], "text", None):
        return resp.content[0].text
    return str(resp)


def _test_gemini(m: ModelConfig) -> str:
    from google import genai

    client = genai.Client(api_key=(m.api_key or ""))
    resp = client.models.generate_content(
        model=m.model_name,
        contents=_TEST_PROMPT,
    )
    return getattr(resp, "text", "") or str(resp)


def _test_ollama(m: ModelConfig) -> str:
    """Ollama 也走 OpenAI 兼容协议（默认 /v1）"""
    from openai import OpenAI

    base = m.api_base_url or "http://localhost:11434/v1"
    client = OpenAI(
        api_key=(m.api_key or "ollama"),
        base_url=base,
        timeout=_TEST_TIMEOUT_SEC,
        max_retries=0,
    )
    resp = client.chat.completions.create(
        model=m.model_name,
        messages=[{"role": "user", "content": _TEST_PROMPT}],
        max_tokens=_TEST_MAX_TOKENS,
    )
    return _extract_openai_text(resp)


def _test_mockllm(m: ModelConfig) -> str:
    """mockllm 不打网络，直接返回固定内容"""
    return "Default output from mockllm/model"


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

def _extract_openai_text(resp) -> str:
    try:
        return resp.choices[0].message.content or ""
    except Exception:
        return str(resp)


def _merge_generate_args(kwargs: dict, extra: dict | None, keys=()):
    if not extra:
        return
    for k in keys:
        v = extra.get(k)
        if v is not None:
            kwargs[k] = v
