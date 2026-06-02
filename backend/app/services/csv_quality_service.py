"""CSV 数据质量检查业务逻辑"""

import csv
import io
from collections import Counter
from datetime import datetime

from app import db
from app.models.csv_quality_task import CsvQualityTask
from app.models.task import Task, TaskType
from app.services.task_service import (
    create_task_record,
    delete_task_record,
    get_task_or_404,
    list_tasks,
    mark_failed,
    mark_running,
    mark_success,
    reset_task,
    task_base_to_dict,
)
from app.services.task_log_service import create_task_logger
from app.utils.errors import BusinessError, ErrorCode
from app.utils.logger import get_logger

logger = get_logger(__name__)

SAMPLE_LIMIT = 5000
PREVIEW_LIMIT = 5
MAX_ANALYZED_ROWS = 2000


def create_csv_quality_task(
    user_id: int,
    task_name: str,
    csv_text: str,
    filename: str,
) -> Task:
    """创建 CSV 数据质量检查任务"""

    task = create_task_record(user_id, TaskType.CSV_QUALITY)
    detail = CsvQualityTask(
        tenant_id=task.tenant_id,
        task_id=task.id,
        task_name=task_name,
        filename=filename,
        input_text=csv_text,
        content_sample=csv_text[:SAMPLE_LIMIT],
    )
    db.session.add(detail)
    db.session.commit()
    return task


def execute_csv_quality_check(task_id: int) -> None:
    """执行 CSV 数据质量检查（在 Celery worker 中调用）"""

    task = db.session.get(Task, task_id)
    if not task or task.task_type != TaskType.CSV_QUALITY:
        logger.error(f"CSV 检查任务 {task_id} 不存在")
        return
    detail = CsvQualityTask.query.filter_by(task_id=task.id).first()
    task_logger = create_task_logger(task)
    if not detail:
        logger.error(f"CSV 检查任务 {task_id} 缺少详情记录")
        task_logger.error(step="load", event="task_detail_missing", msg="任务详情不存在")
        mark_failed(task, "任务详情不存在")
        return

    mark_running(task)
    task_logger.info(
        step="execute",
        event="worker_started",
        msg="Worker 开始执行 CSV 数据质量检查",
        data={"task_name": detail.task_name, "filename": detail.filename},
    )
    logger.info(f"开始 CSV 数据质量检查: task_id={task_id}")

    try:
        task_logger.info(step="parse", event="csv_parse_started", msg="开始解析 CSV")
        detail.result = analyze_csv_text(detail.input_text)
        task_logger.info(
            step="analyze",
            event="csv_quality_analyzed",
            msg="CSV 数据质量检查完成",
            data={
                "row_count": detail.result.get("row_count"),
                "data_row_count": detail.result.get("data_row_count"),
                "column_count": detail.result.get("column_count"),
                "duplicate_rows": detail.result.get("duplicate_rows"),
                "warning_count": len(detail.result.get("warnings") or []),
            },
        )
        mark_success(task)
        task_logger.info(step="complete", event="task_completed", msg="CSV 检查任务完成")
    except Exception as e:
        logger.exception(f"CSV 检查任务 {task_id} 异常")
        task_logger.error(
            step="analyze",
            event="csv_parse_error",
            msg="CSV 解析异常",
            data={"error": str(e)},
        )
        mark_failed(task, f"CSV 解析异常: {str(e)}")


def get_csv_quality_task(task_id: int) -> Task:
    return get_task_or_404(task_id, TaskType.CSV_QUALITY)


def list_csv_quality_tasks(page: int = 1, per_page: int = 20):
    return list_tasks(page=page, per_page=per_page, task_type=TaskType.CSV_QUALITY)


def retry_csv_quality_task(task_id: int) -> Task:
    task = get_csv_quality_task(task_id)
    detail = task.csv_quality
    if not detail:
        raise BusinessError(ErrorCode.TASK_NOT_FOUND)

    detail.result = None
    reset_task(task)
    create_task_logger(task).info(step="retry", event="task_retry_submitted", msg="任务已重新提交")

    from app.tasks.csv_quality_task import check_csv_quality
    check_csv_quality.delay(task.id, task.tenant_id)

    logger.info(f"CSV 检查任务 {task.id} 已重新提交")
    return task


def delete_csv_quality_task(task_id: int) -> None:
    task = get_csv_quality_task(task_id)
    delete_task_record(task)


def csv_quality_task_to_dict(task: Task) -> dict:
    detail = task.csv_quality
    d = task_base_to_dict(task)
    d.update({
        "task_name": detail.task_name if detail else None,
        "filename": detail.filename if detail else None,
        "content_sample": detail.content_sample if detail else None,
        "result": detail.result if detail and detail.result else None,
    })
    return d


def analyze_csv_text(csv_text: str) -> dict:
    """分析 CSV 文本，返回质量概览"""

    rows = _read_csv_rows(csv_text)
    if not rows:
        return {
            "row_count": 0,
            "data_row_count": 0,
            "column_count": 0,
            "columns": [],
            "empty_counts": {},
            "duplicate_rows": 0,
            "type_inference": {},
            "preview": [],
            "warnings": ["CSV 内容为空"],
        }

    warnings = []
    header = [str(cell).strip() for cell in rows[0]]
    if not any(header):
        warnings.append("缺少表头")
        column_count = max(len(row) for row in rows)
        columns = [f"column_{i + 1}" for i in range(column_count)]
        data_rows = rows
    else:
        columns = [
            name if name else f"column_{idx + 1}"
            for idx, name in enumerate(header)
        ]
        column_count = len(columns)
        data_rows = rows[1:]

    inconsistent_rows = [
        idx + 1 for idx, row in enumerate(rows)
        if len(row) != column_count
    ]
    if inconsistent_rows:
        warnings.append(f"存在 {len(inconsistent_rows)} 行列数不一致")

    normalized_rows = [_normalize_row(row, column_count) for row in data_rows]
    analyzed_rows = normalized_rows[:MAX_ANALYZED_ROWS]
    if len(normalized_rows) > MAX_ANALYZED_ROWS:
        warnings.append(f"仅分析前 {MAX_ANALYZED_ROWS} 行数据")

    empty_counts = {column: 0 for column in columns}
    column_values = {column: [] for column in columns}
    for row in analyzed_rows:
        for idx, column in enumerate(columns):
            value = row[idx].strip() if idx < len(row) else ""
            if value == "":
                empty_counts[column] += 1
            else:
                column_values[column].append(value)

    duplicate_rows = _count_duplicate_rows(normalized_rows)
    if duplicate_rows:
        warnings.append(f"存在 {duplicate_rows} 行重复数据")

    data_row_count = len(normalized_rows)
    if data_row_count:
        for column, empty_count in empty_counts.items():
            if empty_count / min(data_row_count, MAX_ANALYZED_ROWS) >= 0.5:
                warnings.append(f"字段 {column} 空值占比较高")

    return {
        "row_count": len(rows),
        "data_row_count": data_row_count,
        "column_count": column_count,
        "columns": columns,
        "empty_counts": empty_counts,
        "duplicate_rows": duplicate_rows,
        "type_inference": {
            column: _infer_type(values)
            for column, values in column_values.items()
        },
        "preview": [
            {columns[idx]: row[idx] if idx < len(row) else "" for idx in range(column_count)}
            for row in normalized_rows[:PREVIEW_LIMIT]
        ],
        "warnings": warnings,
    }


def _read_csv_rows(csv_text: str) -> list[list[str]]:
    sample = csv_text[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample)
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(csv_text), dialect)
    return [row for row in reader if row and any(cell.strip() for cell in row)]


def _normalize_row(row: list[str], column_count: int) -> list[str]:
    normalized = list(row[:column_count])
    if len(normalized) < column_count:
        normalized.extend([""] * (column_count - len(normalized)))
    return normalized


def _count_duplicate_rows(rows: list[list[str]]) -> int:
    counter = Counter(tuple(cell.strip() for cell in row) for row in rows)
    return sum(count - 1 for count in counter.values() if count > 1)


def _infer_type(values: list[str]) -> str:
    if not values:
        return "empty"
    checks = [
        ("integer", _is_integer),
        ("number", _is_number),
        ("boolean", _is_boolean),
        ("date", _is_date),
    ]
    for label, checker in checks:
        matched = sum(1 for value in values if checker(value))
        if matched / len(values) >= 0.8:
            return label
    return "text"


def _is_integer(value: str) -> bool:
    try:
        int(value)
        return True
    except ValueError:
        return False


def _is_number(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def _is_boolean(value: str) -> bool:
    return value.strip().lower() in {"true", "false", "yes", "no", "y", "n", "0", "1"}


def _is_date(value: str) -> bool:
    formats = ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S")
    for fmt in formats:
        try:
            datetime.strptime(value.strip(), fmt)
            return True
        except ValueError:
            continue
    return False
