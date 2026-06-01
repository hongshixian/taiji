"""网页内容分析请求 Schema"""

from marshmallow import Schema, fields, ValidationError


def _validate_url(url: str) -> None:
    """校验 URL 格式"""

    url = url.strip()
    if not url:
        raise ValidationError("URL 不能为空")
    if not url.startswith(("http://", "https://")):
        raise ValidationError("URL 必须以 http:// 或 https:// 开头")
    if len(url) > 2048:
        raise ValidationError("URL 长度不能超过 2048 个字符")


class WebpageAnalysisSubmitSchema(Schema):
    """提交网页内容分析任务请求"""

    url = fields.String(
        required=True,
        validate=_validate_url,
        metadata={"description": "目标网页 URL"},
    )
