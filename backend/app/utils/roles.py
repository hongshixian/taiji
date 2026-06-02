"""角色常量（兼容老代码）

旧代码中以 admin/user 字符串作为角色标识；RBAC 引入后，权威角色定义在
roles 表里。is_valid() 改为对 roles 表的查询，支持运行时新增的自定义角色。
"""


class Role:
    """常用系统角色名常量（仅用于代码可读性，不用于校验）"""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"

    @classmethod
    def is_valid(cls, value):
        """检查角色名是否存在于当前租户作用域（含系统角色 + 租户自定义角色）"""
        if not value:
            return False
        from app.services.role_service import find_role_by_name
        return find_role_by_name(value) is not None
