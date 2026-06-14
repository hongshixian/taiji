"""自动红队测评任务业务逻辑（空壳实现）"""

from app import db
from app.models.red_team_task import RedTeamTask
from app.models.task import Task, TaskType
from app.services.task_service import (
    create_task_record,
    task_base_to_dict,
    mark_running,
    mark_success,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def create_red_team_task(
    user_id: int,
    task_name: str,
    target_model_name: str,
    target_model_endpoint: str | None,
    target_model_api_key: str | None,
    attack_method: str,
    attack_config: dict | None,
) -> Task:
    """创建自动红队测评任务"""

    task = create_task_record(user_id, TaskType.RED_TEAM)
    detail = RedTeamTask(
        tenant_id=task.tenant_id,
        task_id=task.id,
        task_name=task_name,
        target_model_name=target_model_name,
        target_model_endpoint=target_model_endpoint,
        target_model_api_key=target_model_api_key,
        attack_method=attack_method,
        attack_config=attack_config,
    )
    db.session.add(detail)
    db.session.commit()
    return task


def execute_red_team(task_id: int) -> None:
    """执行自动红队测评（空壳：直接标记成功）"""

    task = db.session.get(Task, task_id)
    if not task or task.task_type != TaskType.RED_TEAM:
        logger.error(f"红队测评任务 {task_id} 不存在")
        return

    mark_running(task)
    # TODO: 实现实际红队攻击逻辑
    pass
    mark_success(task)


def red_team_task_to_dict(task: Task) -> dict:
    """将自动红队测评任务序列化为字典"""

    base = task_base_to_dict(task)
    detail = task.red_team
    if not detail:
        return base
    return {
        **base,
        "task_name": detail.task_name,
        "target_model_name": detail.target_model_name,
        "target_model_endpoint": detail.target_model_endpoint,
        "target_model_api_key": "***" if detail.target_model_api_key else None,
        "attack_method": detail.attack_method,
        "attack_config": detail.attack_config,
        "result": detail.result,
    }
