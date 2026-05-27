"""分析任务请求 Schema"""

from marshmallow import Schema, fields, validate, ValidationError


def _validate_url(url: str) -> None:
    """校验 URL 格式"""
    url = url.strip()
    if not url:
        raise ValidationError("URL 不能为空")
    if not url.startswith(("http://", "https://")):
        raise ValidationError("URL 必须以 http:// 或 https:// 开头")
    if len(url) > 2048:
        raise ValidationError("URL 长度不能超过 2048 个字符")


class AnalyzeSubmitSchema(Schema):
    """提交分析任务请求"""

    url = fields.String(
        required=True,
        validate=_validate_url,
        metadata={"description": "目标网页 URL"},
    )


class AnalyzeQuerySchema(Schema):
    """查询任务列表请求（query string）"""

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