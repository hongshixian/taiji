"""自定义接入的 benchmark（inspect_evals 未收录的）

平台用 inspect_ai 的 @task 一等公民机制自行接入上游未收录的评测集。
每个 @task 函数返回标准 Task(dataset, solver, scorer)，由 InspectEvalsEngine
按 engine_ref 前缀 "custom/" 解析后传给 inspect_ai.eval。

新增自定义 benchmark：在此实现 @task 函数 -> 在 suites.yaml 用
engine_ref: custom/<函数名> 登记 -> enabled: true。
"""

from __future__ import annotations

from typing import Any

from inspect_ai import Task, task
from inspect_ai.dataset import Sample, hf_dataset
from inspect_ai.scorer import choice
from inspect_ai.solver import multiple_choice


def _record_to_sample(record: dict[str, Any]) -> Sample:
    """SafetyBench 原始样本：{question, options: [...], answer: int, category} -> inspect Sample。

    inspect 的 multiple_choice 期望 choices=target=字母位置（A/B/C...）。
    answer 是 0-based 索引，转成对应字母。
    """
    options = record.get("options") or []
    answer = record.get("answer")
    target = chr(ord("A") + answer) if isinstance(answer, int) and 0 <= answer < len(options) else ""
    return Sample(
        input=record.get("question", ""),
        choices=options,
        target=target,
        metadata={"category": record.get("category", "")},
    )


def _load_safetybench(category: str = "all", language: str = "en", split: str = "dev"):
    """加载 SafetyBench 并摊平成一条一题。

    原始结构：按类别分组，{category: [{question,options,answer}, ...]}。
    摊平后每条带 category metadata。dev 集（含答案）用于评测；test 集无答案。
    """
    ds = hf_dataset(
        path="thu-coai/SafetyBench",
        name=split,
        split=language,
        trust_remote_code=False,
        sample_fields=None,   # 先拿原始 dict，再自行摊平
    )
    rows: list[dict[str, Any]] = []
    # ds 每行是一个 {category: [questions]} 的分组结构
    for group in ds:
        for cat, questions in group.items():
            if category != "all" and cat != category:
                continue
            for q in (questions or []):
                rows.append({**q, "category": cat})
    return rows


@task
def safetybench(category: str = "all", language: str = "en", split: str = "dev"):
    """SafetyBench：清华多选题安全评测（7 类：冒犯/偏见/身心健康/违法/伦理/隐私等）。

    多选题 -> multiple_choice solver + choice scorer 自动判分，无需评委。
    数据集 MIT 许可。默认 dev 集（有答案，35 题）；test 集无答案不可评测。
    """
    from inspect_ai.dataset import MemoryDataset

    rows = _load_safetybench(category, language, split)
    return Task(
        dataset=MemoryDataset([_record_to_sample(r) for r in rows]),
        solver=multiple_choice(),
        scorer=choice(),
    )
