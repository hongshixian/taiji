"""统一响应工具

所有 handler 都应该用这里的辅助函数返回数据，
避免散落各处的 `jsonify({"code": 0, "message": "...", "data": ...})`。

响应格式约定：
    {"code": int, "message": str, "data": ...}
- code = 0 表示成功
- code != 0 表示业务错误，对应 ErrorCode 中定义的码段
"""

import math
from flask import jsonify


def ok(data=None, message: str = "ok", status: int = 200):
    """成功响应"""
    return jsonify({"code": 0, "message": message, "data": data}), status


def created(data=None, message: str = "created"):
    """资源创建成功（HTTP 201）"""
    return ok(data, message, status=201)


def paginated(items, total: int, page: int, per_page: int):
    """分页响应（统一 items/total/page/per_page/pages 字段）"""
    return ok({
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": math.ceil(total / per_page) if per_page else 0,
    })
