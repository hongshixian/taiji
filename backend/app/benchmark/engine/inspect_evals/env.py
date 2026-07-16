"""HuggingFace 相关环境变量构造（评测执行与可访问性检测共用）

抽出 InspectEvalsEngine._prepare_env 的逻辑，供 engine.run 与 benchmark_check_service
共用，保证「检测走的 HF 缓存/镜像/token 配置」与「真正评测」完全一致。
"""

from __future__ import annotations

import os
from pathlib import Path


def build_hf_env(hf_cache_dir: Path, hf_token: str | None, extra: dict | None = None) -> dict:
    """构造要覆盖的 HF 环境变量（缓存路径、镜像、gated token）。

    镜像（hf-mirror.com）对 resolve 路径间歇 504/超时，datasets 库每次加载
    都会 HEAD 校验元数据文件，任一超时即触发 5 次指数退避重试、拖垮整体。
    故：调大 HEAD/下载超时；并允许外部用 HF_HUB_OFFLINE=1 强制走纯本地缓存
    （已下载的数据集不再校验，彻底规避镜像抖动）。
    """

    env = {
        "HF_HOME": str(hf_cache_dir),
        "HF_DATASETS_CACHE": str(hf_cache_dir / "datasets"),
        "HUGGINGFACE_HUB_CACHE": str(hf_cache_dir / "hub"),
        # 镜像 HEAD 校验超时调大（默认太短，镜像一抖就重试雪崩）
        "HF_HUB_ETAG_TIMEOUT": "30",
        "HF_HUB_DOWNLOAD_TIMEOUT": "60",
    }
    # HF 镜像（国内加速）
    env["HF_ENDPOINT"] = os.environ.get("HF_ENDPOINT", "https://hf-mirror.com")
    # 允许外部强制离线（已缓存数据集不再联网校验）
    if os.environ.get("HF_HUB_OFFLINE"):
        env["HF_HUB_OFFLINE"] = os.environ["HF_HUB_OFFLINE"]
    # gated 数据集 token
    if hf_token:
        env["HF_TOKEN"] = hf_token
        env["HUGGING_FACE_HUB_TOKEN"] = hf_token
    if extra:
        env.update(extra)
    return env
