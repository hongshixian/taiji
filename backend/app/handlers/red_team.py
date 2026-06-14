"""自动红队测评任务处理器"""

from flask import request

from app.handlers.base import BaseTaskHandler
from app.handlers.registry import registry
from app.schemas.red_team_schema import RedTeamSubmitSchema
from app.services.red_team_service import (
    create_red_team_task,
    execute_red_team,
    red_team_task_to_dict,
)
from app.utils.errors import BusinessError, ErrorCode
from app.utils.validation import validate_schema


class RedTeamHandler(BaseTaskHandler):
    task_type = "red_team"
    task_type_name = "自动红队测评"
    url_prefix = "red-team"
    rate_limit_submit = "20 per minute"

    def submit(self, user_id: int):
        data = request.get_json()
        if not data:
            raise BusinessError(ErrorCode.EMPTY_BODY)
        parsed, error = validate_schema(RedTeamSubmitSchema(), data)
        if error:
            raise BusinessError(ErrorCode.VALIDATION_ERROR)
        return create_red_team_task(
            user_id=user_id,
            task_name=parsed["task_name"].strip(),
            target_model_name=parsed["target_model_name"].strip(),
            target_model_endpoint=parsed.get("target_model_endpoint"),
            target_model_api_key=parsed.get("target_model_api_key"),
            attack_method=parsed["attack_method"],
            attack_config=parsed.get("attack_config"),
        )

    def execute(self, task_id: int) -> None:
        execute_red_team(task_id)

    def to_dict(self, task) -> dict:
        return red_team_task_to_dict(task)

    def _clear_detail(self, task) -> None:
        if task.red_team:
            task.red_team.result = None


_handler = RedTeamHandler()
registry.register(_handler)
