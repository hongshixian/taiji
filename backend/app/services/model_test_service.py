"""模型配置连通性测试服务

关键原则：**测试路径与评测路径完全对齐**。
  测试功能直接复用 benchmark 引擎的 translate（model spec + 环境变量）+
  inspect_ai.get_model().generate()，因此测试测到的请求拼接、provider 通道、
  端点（/chat/completions vs /responses）、鉴权方式，与真正跑评测时 inspect_ai
  发出的请求完全一致。测试通过 == 评测能连通。

不下发任何敏感值给前端，只回执 { ok, latency_ms, sample_output, error,
provider, model }。
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from app.benchmark.dto import ModelSpec
from app.benchmark.engine.inspect_evals.translate import (
    build_generate_config,
    model_spec_to_inspect_model,
    with_model_env,
)
from app.models.model_config import ModelConfig
from app.utils.logger import get_logger


logger = get_logger(__name__)

_TEST_PROMPT = "Reply with only the word 'ok'."
_TEST_MAX_TOKENS = 32
_TEST_TIMEOUT_SEC = 30


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


def _spec_from_config(m: ModelConfig) -> ModelSpec:
    return ModelSpec(
        id=m.id,
        display_name=m.display_name,
        model_name=m.model_name,
        api_base_url=m.api_base_url,
        api_protocol=m.api_protocol,
        api_key=m.api_key,
        extra_params=dict(m.extra_params or {}),
    )


def test_model_config(m: ModelConfig) -> ModelTestResult:
    """用与评测完全相同的通道发一次极简请求，验证连通性。"""

    spec = _spec_from_config(m)
    inspect_model = model_spec_to_inspect_model(spec)
    started = time.monotonic()

    try:
        text = _run_generate(spec, inspect_model)
        return ModelTestResult(
            ok=True,
            latency_ms=int((time.monotonic() - started) * 1000),
            sample_output=(text or "")[:200],
            error=None,
            provider=m.api_protocol,
            model=inspect_model,
        )
    except Exception as exc:
        logger.warning("模型测试失败 %s: %s", m.display_name, exc)
        return ModelTestResult(
            ok=False,
            latency_ms=int((time.monotonic() - started) * 1000),
            sample_output=None,
            error=f"{type(exc).__name__}: {exc}"[:800],
            provider=m.api_protocol,
            model=inspect_model,
        )


def _run_generate(spec: ModelSpec, inspect_model: str) -> str:
    """在临时环境变量下用 inspect_ai 跑一次 generate（带整体超时）。"""

    from inspect_ai.model import get_model, GenerateConfig

    gen_cfg = build_generate_config(spec)
    gen_cfg.setdefault("max_tokens", _TEST_MAX_TOKENS)

    async def _go() -> str:
        model = get_model(
            inspect_model,
            config=GenerateConfig(**gen_cfg),
            memoize=False,   # 每次测试都新建，避免拿到旧缓存的鉴权
        )
        output = await asyncio.wait_for(
            model.generate(input=_TEST_PROMPT),
            timeout=_TEST_TIMEOUT_SEC,
        )
        return output.completion or ""

    with with_model_env([spec]):
        return asyncio.run(_go())
