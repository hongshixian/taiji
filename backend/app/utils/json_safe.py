"""JSON 安全化：把 Python 里合法、但 JSON 标准 / PostgreSQL JSON 列不接受的
特殊浮点值（NaN / Infinity / -Infinity）递归替换为 None。

背景：inspect_ai 在样本全失败等场景下算出的 metric 可能是 float('nan')。
SQLite 存 JSON 不校验，能落库；PostgreSQL 的 ::JSON 严格校验会抛
`InvalidTextRepresentation: Token "NaN" is invalid`，导致事务失败、任务卡死。
所有写入 JSON 列（Task.progress / BenchmarkTask.result 等）的数据都应先过这里。
"""

from __future__ import annotations

import math
from typing import Any


def json_safe(value: Any) -> Any:
    """递归清洗：NaN / ±Inf → None；容器深拷贝式替换，其余原样返回。"""

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value
