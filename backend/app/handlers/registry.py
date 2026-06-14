"""任务处理器注册表

handler 模块末尾调用 registry.register(XxxHandler()) 完成自注册。
框架通过 registry.discover() 统一导入所有已知 handler 模块。
"""

from typing import Dict


class TaskRegistry:
    def __init__(self):
        self._handlers: Dict[str, "BaseTaskHandler"] = {}

    def register(self, handler) -> None:
        """注册 handler：生成 Celery task 并记录 task_type_name。"""
        handler.make_celery_task()
        self._handlers[handler.task_type] = handler
        # 将可读名称写入 TASK_TYPE_NAMES，供 task_base_to_dict 使用
        from app.models.task import TASK_TYPE_NAMES
        TASK_TYPE_NAMES[handler.task_type] = handler.task_type_name

    def get(self, task_type: str):
        return self._handlers.get(task_type)

    def all(self):
        return self._handlers.values()

    def discover(self) -> None:
        """导入所有 handler 模块，触发模块末尾的 registry.register()。
        新增任务类型时，在这里加一行 import 即可。
        """
        import app.handlers.webpage_analysis  # noqa: F401
        import app.handlers.csv_quality       # noqa: F401
        import app.handlers.benchmark          # noqa: F401


registry = TaskRegistry()
