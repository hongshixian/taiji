"""HuggingFace 相关环境变量构造（评测执行与可访问性检测共用）

抽出 InspectEvalsEngine._prepare_env 的逻辑，供 engine.run 与 benchmark_check_service
共用，保证「检测走的 HF 缓存/镜像/token 配置」与「真正评测」完全一致。
"""

from __future__ import annotations

import os
from pathlib import Path


def build_hf_env(hf_cache_dir: Path, hf_token: str | None, extra: dict | None = None) -> dict:
    """构造要覆盖的 HF 环境变量（缓存路径、镜像、gated token）。"""

    env = {
        "HF_HOME": str(hf_cache_dir),
        "HF_DATASETS_CACHE": str(hf_cache_dir / "datasets"),
        "HUGGINGFACE_HUB_CACHE": str(hf_cache_dir / "hub"),
    }
    # HF 镜像（国内加速）
    env["HF_ENDPOINT"] = os.environ.get("HF_ENDPOINT", "https://hf-mirror.com")
    # gated 数据集 token
    if hf_token:
        env["HF_TOKEN"] = hf_token
        env["HUGGING_FACE_HUB_TOKEN"] = hf_token
    if extra:
        env.update(extra)
    return env
