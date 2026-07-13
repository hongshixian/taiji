"""Benchmark 引擎层的数据契约（引擎无关）"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# 模型描述（从 ModelConfig 派生的 DTO，不带 ORM）
# ---------------------------------------------------------------------------

@dataclass
class ModelSpec:
    """被测模型 / 评委模型 的运行时描述。

    引擎层看不到 ORM，只用这份纯数据。
    """

    id: int
    display_name: str
    model_name: str            # API 请求时的模型名
    api_base_url: str
    api_protocol: str          # openai / anthropic / gemini / ollama / custom
    api_key: str | None = None
    extra_params: dict = field(default_factory=dict)  # temperature/top_p/max_tokens/stop_sequences 等


# ---------------------------------------------------------------------------
# Suite 描述（供前端 & 引擎共同消费）
# ---------------------------------------------------------------------------

@dataclass
class SuiteDescriptor:
    """Benchmark suite 元数据。

    这份数据来源：`inspect_evals/suites.yaml`；前端通过 GET /benchmarks/suites 拿到；
    后端在提交任务时用它做入参校验，在执行时用它翻译成引擎调用参数。
    """

    key: str                        # 平台内部唯一 key（snake_case）
    engine: str                     # 提供该 suite 的引擎名，如 "inspect_evals"
    display_name: str               # 前端显示名
    category: str                   # capability / safety / alignment
    description: str = ""
    needs_judge: bool = False
    judge_arg: str | None = None    # inspect_evals task 函数里的评委参数名（若通过参数传）
    judge_role_bindings: list[str] = field(default_factory=list)
    # ↑ 通过 --model-role 覆盖的辅助 role 列表，如 makemesay: ["judge", "manipulatee"]
    needs_sandbox: bool = False
    engine_ref: str = ""            # 引擎内部的 task 引用（如 "inspect_evals/mmlu"）
    default_config: dict = field(default_factory=dict)
    config_schema: dict = field(default_factory=dict)  # 供前端 dynamic form 使用
    disabled: bool = False
    disabled_reason: str | None = None
    notes: str | None = None        # 前端 tooltip

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "engine": self.engine,
            "display_name": self.display_name,
            "category": self.category,
            "description": self.description,
            "needs_judge": self.needs_judge,
            "needs_sandbox": self.needs_sandbox,
            "default_config": self.default_config,
            "config_schema": self.config_schema,
            "disabled": self.disabled,
            "disabled_reason": self.disabled_reason,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# 任务执行参数（Handler → Engine）
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkParams:
    suite: SuiteDescriptor
    target_model: ModelSpec
    judge_model: ModelSpec | None
    execution_config: dict           # {limit, epochs, max_connections, timeout_minutes}
    suite_config: dict               # per-suite 参数（默认 + 用户覆盖后的合并结果）
    hf_token: str | None = None      # 平台系统设置里的 HF token（gated dataset 用）


# ---------------------------------------------------------------------------
# 任务执行结果（Engine → Handler）
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkResult:
    metrics: dict[str, Any]                      # {"accuracy": 0.72, "stderr": 0.02, ...}
    total_samples: int
    completed_samples: int
    failed_samples: int = 0
    model_usage: dict = field(default_factory=dict)      # {"input_tokens", "output_tokens", ...}
    samples_preview: list[dict] = field(default_factory=list)  # 前 N 条样本预览
    artifact_paths: list[str] = field(default_factory=list)    # .eval / .json 绝对路径
    engine: str = ""                              # "inspect_evals@0.14.3"
    engine_metadata: dict = field(default_factory=dict)
    status: str = "success"                       # success / partial_success / failed
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "metrics": self.metrics,
            "total_samples": self.total_samples,
            "completed_samples": self.completed_samples,
            "failed_samples": self.failed_samples,
            "model_usage": self.model_usage,
            "samples_preview": self.samples_preview,
            "artifact_paths": self.artifact_paths,
            "engine": self.engine,
            "engine_metadata": self.engine_metadata,
            "status": self.status,
            "error": self.error,
        }
