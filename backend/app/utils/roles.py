"""角色常量"""

class Role:
    ADMIN = "admin"
    USER = "user"

    _ALL = {ADMIN, USER}

    @classmethod
    def is_valid(cls, value):
        return value in cls._ALL
