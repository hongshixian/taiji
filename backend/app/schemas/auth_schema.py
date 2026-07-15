"""认证请求 Schema"""

from marshmallow import Schema, fields, validate


class RegisterSchema(Schema):
    """用户注册请求"""

    username = fields.String(
        required=True,
        validate=validate.Length(min=3, max=30, error="用户名长度必须在 3-30 个字符之间"),
        metadata={"description": "用户名，3-30 字符"},
    )
    email = fields.Email(
        required=True,
        metadata={"description": "邮箱地址"},
    )
    password = fields.String(
        required=True,
        validate=validate.Length(min=6, error="密码长度至少 6 位"),
        metadata={"description": "密码，至少 6 位"},
    )


class LoginSchema(Schema):
    """用户登录请求"""

    username = fields.String(
        required=True,
        validate=validate.Length(min=1, error="用户名不能为空"),
        metadata={"description": "用户名"},
    )
    password = fields.String(
        required=True,
        validate=validate.Length(min=1, error="密码不能为空"),
        metadata={"description": "密码"},
    )


class ChangePasswordSchema(Schema):
    """用户自助修改密码请求"""

    old_password = fields.String(
        required=True,
        validate=validate.Length(min=1, error="旧密码不能为空"),
        metadata={"description": "当前密码"},
    )
    new_password = fields.String(
        required=True,
        validate=validate.Length(min=6, error="新密码至少 6 位"),
        metadata={"description": "新密码，至少 6 位"},
    )
