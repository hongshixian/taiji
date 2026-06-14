"""CSV 数据质量检查任务处理器"""

import os

from flask import request
from marshmallow import ValidationError

from app.handlers.base import BaseTaskHandler
from app.handlers.registry import registry
from app.schemas.csv_quality_schema import (
    MAX_CSV_TEXT_LENGTH,
    _validate_csv_text,
    validate_csv_filename,
    validate_task_name,
)
from app.services.csv_quality_service import (
    create_csv_quality_task,
    execute_csv_quality_check,
    csv_quality_task_to_dict,
)
from app.utils.errors import BusinessError, ErrorCode


class CsvQualityHandler(BaseTaskHandler):
    task_type = "csv_quality_check"
    task_type_name = "CSV 数据质量检查"
    url_prefix = "csv-quality"
    rate_limit_submit = "20 per minute"

    def submit(self, user_id: int):
        if not request.form and not request.files:
            raise BusinessError(ErrorCode.EMPTY_BODY)
        try:
            task_name = validate_task_name(request.form.get("task_name", ""))
            upload = request.files.get("file")
            if not upload:
                raise ValidationError("CSV 文件不能为空")
            filename = validate_csv_filename(os.path.basename(upload.filename or ""))
            csv_text = self._read_csv(upload)
            _validate_csv_text(csv_text)
        except ValidationError:
            raise BusinessError(ErrorCode.VALIDATION_ERROR)
        return create_csv_quality_task(user_id, task_name, csv_text, filename)

    def execute(self, task_id: int) -> None:
        execute_csv_quality_check(task_id)

    def to_dict(self, task) -> dict:
        return csv_quality_task_to_dict(task)

    def _clear_detail(self, task) -> None:
        if task.csv_quality:
            task.csv_quality.result = None

    @staticmethod
    def _read_csv(upload) -> str:
        raw = upload.stream.read(MAX_CSV_TEXT_LENGTH + 1)
        if len(raw) > MAX_CSV_TEXT_LENGTH:
            raise ValidationError("CSV 文件不能超过 200000 字节")
        for enc in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                continue
        raise ValidationError("CSV 文件编码仅支持 UTF-8 或 GB18030")


_handler = CsvQualityHandler()
registry.register(_handler)
