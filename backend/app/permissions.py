"""系统权限枚举 — 代码侧硬编码

权限码是代码里的常量，对应到 handler 装饰器的 @require_permission("xxx")。
不允许 admin 在运行时增删权限码（因为代码里没有对应的判断）。
角色（Role）可以运行时增删，并通过 role_permissions 关联表绑定权限。
"""


class Permission:
    """系统权限码"""

    # 用户管理
    USER_READ = "user:read"            # 查看用户列表
    USER_WRITE = "user:write"          # 创建/编辑用户
    USER_DELETE = "user:delete"        # 删除用户
    ROLE_ASSIGN = "role:assign"        # 分配角色给用户

    # 角色管理
    ROLE_READ = "role:read"            # 查看角色列表
    ROLE_WRITE = "role:write"          # 创建/编辑角色（含修改权限分配）
    ROLE_DELETE = "role:delete"        # 删除非系统角色

    # 任务
    TASK_READ = "task:read"            # 查看任务（自己的）
    TASK_CREATE = "task:create"        # 创建任务
    TASK_DELETE_ANY = "task:delete:any"  # 删除任意用户的任务（admin 用）

    # 模型配置
    MODEL_READ = "model:read"          # 查看模型配置
    MODEL_WRITE = "model:write"        # 新建 / 编辑模型配置
    MODEL_DELETE = "model:delete"      # 删除模型配置

    # 系统
    SYSTEM_AUDIT = "system:audit"      # 查看审计日志（预留）


# 注册表：权限码 → 描述（启动时 seed 到 permissions 表）
PERMISSIONS_REGISTRY: dict[str, str] = {
    Permission.USER_READ: "查看用户列表",
    Permission.USER_WRITE: "创建 / 编辑用户",
    Permission.USER_DELETE: "删除用户",
    Permission.ROLE_ASSIGN: "为用户分配角色",
    Permission.ROLE_READ: "查看角色列表",
    Permission.ROLE_WRITE: "创建 / 编辑角色（含权限分配）",
    Permission.ROLE_DELETE: "删除非系统角色",
    Permission.TASK_READ: "查看自己的任务",
    Permission.TASK_CREATE: "创建任务",
    Permission.TASK_DELETE_ANY: "删除任意用户的任务",
    Permission.MODEL_READ: "查看模型配置",
    Permission.MODEL_WRITE: "新建 / 编辑模型配置",
    Permission.MODEL_DELETE: "删除模型配置",
    Permission.SYSTEM_AUDIT: "查看审计日志",
}


# 系统角色 → 权限码集合（启动时 seed）
SYSTEM_ROLES: dict[str, set[str]] = {
    "admin": {
        Permission.USER_READ, Permission.USER_WRITE, Permission.USER_DELETE,
        Permission.ROLE_ASSIGN, Permission.ROLE_READ, Permission.ROLE_WRITE,
        Permission.ROLE_DELETE,
        Permission.TASK_READ, Permission.TASK_CREATE, Permission.TASK_DELETE_ANY,
        Permission.MODEL_READ, Permission.MODEL_WRITE, Permission.MODEL_DELETE,
        Permission.SYSTEM_AUDIT,
    },
    "user": {
        Permission.TASK_READ, Permission.TASK_CREATE,
        Permission.MODEL_READ, Permission.MODEL_WRITE, Permission.MODEL_DELETE,
    },
    "guest": {
        Permission.TASK_READ,
    },
}


# 系统角色描述
SYSTEM_ROLE_DESCRIPTIONS: dict[str, str] = {
    "admin": "管理员（全部权限）",
    "user": "普通用户（创建并查看自己的任务）",
    "guest": "访客（只读）",
}
