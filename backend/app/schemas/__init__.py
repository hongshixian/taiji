"""请求/响应 Schema — 统一校验与序列化"""

from app.schemas.auth_schema import LoginSchema, RegisterSchema
from app.schemas.task_schema import TaskQuerySchema
from app.schemas.webpage_analysis_schema import WebpageAnalysisSubmitSchema

__all__ = [
    "LoginSchema",
    "RegisterSchema",
    "TaskQuerySchema",
    "WebpageAnalysisSubmitSchema",
]
