"""taiji_evals —— 平台自有的 inspect_ai 评测集包

用于接入 inspect_evals 尚未收录的 benchmark。每个评测集是一个 @task 函数，
被 inspect_ai 注册后可通过 "taiji_evals/<task_name>" 引用（与 inspect_evals/<name> 同理）。

注册方式：平台引擎在调用 inspect_ai 前 import 本包（见 _registry），触发各 @task
装饰器注册；无需 pip install / entry_points。
"""

from taiji_evals._registry import *  # noqa: F401,F403
