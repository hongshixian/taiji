"""网页内容分析任务处理器"""

from flask import request

from app.handlers.base import BaseTaskHandler
from app.handlers.registry import registry
from app.schemas.webpage_analysis_schema import WebpageAnalysisSubmitSchema
from app.services.webpage_analysis_service import (
    create_webpage_analysis_task,
    execute_webpage_analysis,
    webpage_analysis_task_to_dict,
)
from app.utils.errors import BusinessError, ErrorCode
from app.utils.validation import validate_schema


class WebpageAnalysisHandler(BaseTaskHandler):
    task_type = "webpage_content_analysis"
    task_type_name = "网页内容分析"
    url_prefix = "webpage-analysis"
    rate_limit_submit = "30 per minute"

    def submit(self, user_id: int):
        data = request.get_json()
        if not data:
            raise BusinessError(ErrorCode.EMPTY_BODY)
        parsed, error = validate_schema(WebpageAnalysisSubmitSchema(), data)
        if error:
            # validate_schema 返回 (None, (response, status))，需转为异常
            raise BusinessError(ErrorCode.VALIDATION_ERROR)
        return create_webpage_analysis_task(user_id, parsed["url"].strip())

    def execute(self, task_id: int) -> None:
        execute_webpage_analysis(task_id)

    def to_dict(self, task) -> dict:
        return webpage_analysis_task_to_dict(task)

    def _clear_detail(self, task) -> None:
        detail = task.webpage_analysis
        if detail:
            detail.title = None
            detail.summary = None
            detail.keywords = None


_handler = WebpageAnalysisHandler()
registry.register(_handler)
