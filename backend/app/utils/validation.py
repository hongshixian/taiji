"""Schema 校验辅助"""

from typing import Any

from flask import jsonify
from marshmallow import Schema, ValidationError

from app.utils.errors import ErrorCode


def validate_schema(schema: Schema, data: dict) -> tuple[dict | None, Any | None]:
    """校验请求数据

    Returns:
        (parsed_data, None) 校验通过
        (None, (response, status_code)) 校验失败，code = VALIDATION_ERROR
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
        err_code = ErrorCode.VALIDATION_ERROR
        response = jsonify({
            "code": err_code.code,
            "message": f"{err_code.message}: {detail}",
        })
        return None, (response, err_code.http)
