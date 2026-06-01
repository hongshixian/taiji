"""CSV 数据质量检查请求限制"""

from marshmallow import ValidationError

MAX_CSV_TEXT_LENGTH = 200_000
MAX_TASK_NAME_LENGTH = 100
MAX_FILENAME_LENGTH = 255


def _validate_csv_text(csv_text: str) -> None:
    text = csv_text.strip()
    if not text:
        raise ValidationError("CSV 内容不能为空")
    if len(csv_text) > MAX_CSV_TEXT_LENGTH:
        raise ValidationError("CSV 内容不能超过 200000 个字符")


def validate_task_name(task_name: str) -> str:
    """校验并清理任务名"""

    value = task_name.strip()
    if not value:
        raise ValidationError("任务名不能为空")
    if len(value) > MAX_TASK_NAME_LENGTH:
        raise ValidationError("任务名不能超过 100 个字符")
    return value


def validate_csv_filename(filename: str) -> str:
    """校验并清理 CSV 文件名"""

    value = filename.strip()
    if not value:
        raise ValidationError("CSV 文件不能为空")
    if len(value) > MAX_FILENAME_LENGTH:
        raise ValidationError("文件名不能超过 255 个字符")
    if not value.lower().endswith(".csv"):
        raise ValidationError("请上传 .csv 文件")
    return value
