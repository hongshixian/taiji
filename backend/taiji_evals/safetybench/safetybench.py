"""SafetyBench —— thu-coai 的 LLM 安全多选题评测集（ACL 2024）

数据集：HF `thu-coai/SafetyBench`，裸 JSON（非 HF datasets 标准格式）。
  * dev_{en,zh}.json：按 7 个安全类别分组的 dict，每类 5 条，带 answer（选项索引）—— 用于本地判分。
  * test_{en,zh}.json：11435 条 list，无 answer（官方隐藏，需提交评测器）—— 不能本地判分。

POC 用 dev split：题型为多选题（question + options + answer 索引），
solver 用 multiple_choice()，scorer 用内置 choice()。

参考 inspect_evals/truthfulqa 的多选题标准模板。
"""

from __future__ import annotations

import json

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.scorer import choice
from inspect_ai.solver import multiple_choice


_REPO = "thu-coai/SafetyBench"
# 选项索引 -> 字母（choice scorer 用字母对齐 multiple_choice 渲染的 A/B/C/D）
_LETTERS = ["A", "B", "C", "D", "E", "F"]


@task
def safetybench(language: str = "en", split: str = "dev") -> Task:
    """SafetyBench 安全多选题。

    Args:
        language: "en" 或 "zh"（数据集为中英双语）。
        split: "dev"（35 条带答案，可判分）或 "test"（11435 条无答案，仅跑不判分）。
    """
    lang = "zh" if str(language).lower().startswith("zh") else "en"
    use_split = "test" if str(split).lower() == "test" else "dev"

    samples = _load_samples(lang, use_split)
    return Task(
        dataset=MemoryDataset(samples, name=f"safetybench_{lang}_{use_split}"),
        solver=[multiple_choice()],
        scorer=choice(),
    )


def _load_samples(lang: str, split: str) -> list[Sample]:
    from huggingface_hub import hf_hub_download

    path = hf_hub_download(_REPO, f"{split}_{lang}.json", repo_type="dataset")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    samples: list[Sample] = []
    if split == "dev":
        # dev：{category: [ {question, options, answer(int)} ]}
        for category, items in data.items():
            for i, rec in enumerate(items):
                samples.append(_record_to_sample(rec, category, f"{category}-{i}"))
    else:
        # test：[ {question, options, category, id} ]，无 answer
        for rec in data:
            samples.append(_record_to_sample(rec, rec.get("category", ""), rec.get("id")))
    return samples


def _record_to_sample(rec: dict, category: str, sid) -> Sample:
    options = rec.get("options") or []
    answer_idx = rec.get("answer")
    target = _LETTERS[answer_idx] if isinstance(answer_idx, int) and 0 <= answer_idx < len(options) else ""
    return Sample(
        input=rec["question"],
        choices=list(options),
        target=target,
        id=str(sid) if sid is not None else None,
        metadata={"category": category},
    )
