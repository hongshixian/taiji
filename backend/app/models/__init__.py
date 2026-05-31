"""数据模型 — 统一导入所有模型，确保 SQLAlchemy 能发现它们"""

from app.models.tenant import Tenant  # 必须最先 import（其他模型 FK 引用它）
from app.models._tenant_mixin import TenantMixin  # 注册全局 event hook
from app.models.user import User
from app.models.tenant_membership import TenantMembership
from app.models.analyze_task import AnalyzeTask, TaskStatus
from app.models.role import Role, Permission, role_permissions
from app.models.system_setting import SystemSetting

__all__ = [
    "Tenant", "TenantMixin",
    "User", "TenantMembership", "AnalyzeTask", "TaskStatus",
    "Role", "Permission", "role_permissions",
    "SystemSetting",
]
