"""Schema 校验辅助"""

from typing import Any

from flask import jsonify
from marshmallow import Schema, ValidationError


def validate_schema(schema: Schema, data: dict) -> tuple[dict | None, Any | None]:
    """校验请求数据，成功返回 (parsed_data, None)，失败返回 (None, error_response)

    Returns:
        (parsed_data, None) 校验通过
        (None, (response, status_code)) 校验失败
    """
    try:
        return schema.load(data), None
    except ValidationError as err:
        messages = err.messages
        if isinstance(messages, dict):
            first_field = next(iter(messages))
            first_msg = messages[first_field]
            detail = first_msg[0] if isinstance(first_msg, list) else str(first_msg)
        else:
            detail = str(messages)
        return None, (jsonify({"code": 400, "message": f"请求参数错误: {detail}"}), 400)