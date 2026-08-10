"""系统权限枚举 — 代码侧硬编码

权限码是代码里的常量，对应到 handler 装饰器的 @require_permission("xxx")。
不允许 admin 在运行时增删权限码（因为代码里没有对应的判断）。
OIDC 模式使用 IAM 固定角色；本地 Role 仅作为业务权限映射和旧认证模式兼容层。
"""


class Permission:
    """系统权限码"""

    # 租户成员管理
    MEMBER_READ = "member:read"        # 查看当前租户成员
    MEMBER_WRITE = "member:write"      # 邀请成员、修改固定身份角色
    MEMBER_REMOVE = "member:remove"    # 停用当前租户成员身份

    # 任务
    TASK_READ = "task:read"            # 查看租户内全部任务
    TASK_CREATE = "task:create"        # 创建任务
    TASK_DELETE_ANY = "task:delete:any"  # 管理租户内任意成员的任务

    # 模型配置
    MODEL_READ = "model:read"          # 查看模型配置
    MODEL_WRITE = "model:write"        # 新建 / 编辑模型配置
    MODEL_DELETE = "model:delete"      # 删除模型配置

    # Benchmark 资产
    BENCHMARK_READ = "benchmark:read"    # 查看 Benchmark 资产与状态
    BENCHMARK_WRITE = "benchmark:write"  # 管理 Benchmark 启用状态与可达性检测

    # 系统
    SYSTEM_AUDIT = "system:audit"      # 查看审计日志（预留）


# 注册表：权限码 → 描述（启动时 seed 到 permissions 表）
PERMISSIONS_REGISTRY: dict[str, str] = {
    Permission.MEMBER_READ: "查看当前租户成员",
    Permission.MEMBER_WRITE: "邀请成员并修改固定身份角色",
    Permission.MEMBER_REMOVE: "停用当前租户成员身份",
    Permission.TASK_READ: "查看租户内全部任务",
    Permission.TASK_CREATE: "创建任务",
    Permission.TASK_DELETE_ANY: "管理租户内任意成员的任务",
    Permission.MODEL_READ: "查看模型配置",
    Permission.MODEL_WRITE: "新建 / 编辑模型配置",
    Permission.MODEL_DELETE: "删除模型配置",
    Permission.BENCHMARK_READ: "查看 Benchmark 资产与状态",
    Permission.BENCHMARK_WRITE: "管理 Benchmark 启用状态与可达性检测",
    Permission.SYSTEM_AUDIT: "查看审计日志",
}


# 系统角色 → 权限码集合（启动时 seed）
SYSTEM_ROLES: dict[str, set[str]] = {
    "admin": {
        Permission.MEMBER_READ, Permission.MEMBER_WRITE, Permission.MEMBER_REMOVE,
        Permission.TASK_READ, Permission.TASK_CREATE, Permission.TASK_DELETE_ANY,
        Permission.MODEL_READ, Permission.MODEL_WRITE, Permission.MODEL_DELETE,
        Permission.BENCHMARK_READ, Permission.BENCHMARK_WRITE,
        Permission.SYSTEM_AUDIT,
    },
    "user": {
        Permission.TASK_READ, Permission.TASK_CREATE, Permission.TASK_DELETE_ANY,
        Permission.MODEL_READ, Permission.MODEL_WRITE, Permission.MODEL_DELETE,
        Permission.BENCHMARK_READ,
    },
    "guest": {
        Permission.TASK_READ,
    },
}


# 系统角色描述
SYSTEM_ROLE_DESCRIPTIONS: dict[str, str] = {
    "admin": "租户管理员",
    "user": "租户成员",
    "guest": "访客（只读）",
}
