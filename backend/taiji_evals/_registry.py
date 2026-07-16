"""taiji_evals 任务注册表

import 各评测集模块的 @task 函数，触发 inspect_ai 的 @task 装饰器注册。
新增评测集时在此加一行 import。
"""

from taiji_evals.safetybench.safetybench import safetybench  # noqa: F401

__all__ = ["safetybench"]
