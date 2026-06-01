"""通用任务请求 Schema"""

from marshmallow import Schema, fields, validate


class TaskQuerySchema(Schema):
    """任务分页查询请求（query string）"""

    page = fields.Integer(
        load_default=1,
        validate=validate.Range(min=1, error="页码必须 ≥ 1"),
        metadata={"description": "页码"},
    )
    per_page = fields.Integer(
        load_default=20,
        validate=validate.Range(min=1, max=100, error="每页条数必须在 1-100 之间"),
        metadata={"description": "每页条数"},
    )
