"""自动红队测评任务输入校验 Schema"""

from marshmallow import Schema, ValidationError, fields, validate, validates


ATTACK_METHODS = [
    "gcg",
    "gcg_ensemble",
    "gptfuzz",
    "pair",
    "tap",
    "autodan",
    "autoprompt",
]


class RedTeamSubmitSchema(Schema):
    task_name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=100),
    )
    target_model_name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=200),
    )
    target_model_endpoint = fields.String(
        load_default=None,
        validate=validate.Length(max=500),
    )
    target_model_api_key = fields.String(
        load_default=None,
        validate=validate.Length(max=500),
    )
    attack_method = fields.String(
        required=True,
        validate=validate.OneOf(ATTACK_METHODS),
    )
    attack_config = fields.Dict(load_default=None)

    @validates("task_name")
    def validate_task_name(self, value):
        if not value.strip():
            raise ValidationError("任务名称不能为空白")
