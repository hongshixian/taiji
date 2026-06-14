"""数据模型 — 统一导入所有模型，确保 SQLAlchemy 能发现它们"""

from app.models.tenant import Tenant  # 必须最先 import（其他模型 FK 引用它）
from app.models._tenant_mixin import TenantMixin  # 注册全局 event hook
from app.models.user import User
from app.models.tenant_membership import TenantMembership
from app.models.task import Task, TaskStatus, TaskType
from app.models.webpage_analysis_task import WebpageAnalysisTask
from app.models.csv_quality_task import CsvQualityTask
from app.models.benchmark_task import BenchmarkTask
from app.models.role import Role, Permission, role_permissions
from app.models.system_setting import SystemSetting
from app.models.audit_log import AuditLog

__all__ = [
    "Tenant", "TenantMixin",
    "User", "TenantMembership",
    "Task", "TaskStatus", "TaskType",
    "WebpageAnalysisTask", "CsvQualityTask", "BenchmarkTask",
    "Role", "Permission", "role_permissions",
    "SystemSetting", "AuditLog",
]
