"""网页内容分析业务逻辑"""

import re

import requests
from bs4 import BeautifulSoup

from app import db
from app.models.task import Task, TaskType
from app.models.webpage_analysis_task import WebpageAnalysisTask
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
from app.utils.errors import BusinessError, ErrorCode
from app.utils.logger import get_logger

logger = get_logger(__name__)

REQUEST_TIMEOUT = 30


def create_webpage_analysis_task(user_id: int, url: str) -> Task:
    """创建网页内容分析任务"""

    task = create_task_record(user_id, TaskType.WEBPAGE_ANALYSIS)
    detail = WebpageAnalysisTask(
        tenant_id=task.tenant_id,
        task_id=task.id,
        url=url,
    )
    db.session.add(detail)
    db.session.commit()
    return task


def execute_webpage_analysis(task_id: int) -> None:
    """执行网页内容分析（在 Celery worker 中调用）"""

    task = db.session.get(Task, task_id)
    if not task or task.task_type != TaskType.WEBPAGE_ANALYSIS:
        logger.error(f"网页分析任务 {task_id} 不存在")
        return
    detail = WebpageAnalysisTask.query.filter_by(task_id=task.id).first()
    if not detail:
        logger.error(f"网页分析任务 {task_id} 缺少详情记录")
        mark_failed(task, "任务详情不存在")
        return

    mark_running(task)
    logger.info(f"开始网页分析: {detail.url}")

    try:
        response = requests.get(
            detail.url,
            timeout=REQUEST_TIMEOUT,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; TaijiBot/1.0; "
                    "+https://github.com/hongshixian/taiji)"
                ),
            },
            allow_redirects=True,
        )
        response.raise_for_status()
        response.encoding = response.apparent_encoding or "utf-8"

        soup = BeautifulSoup(response.text, "html.parser")
        detail.title = _extract_title(soup)
        detail.summary = _extract_summary(soup)
        detail.keywords = _extract_keywords(soup)
        mark_success(task)

        logger.info(f"网页分析完成: {detail.url} -> {detail.title}")
    except requests.Timeout:
        mark_failed(task, "网页请求超时")
    except requests.ConnectionError:
        mark_failed(task, "无法连接到目标网址")
    except requests.HTTPError as e:
        mark_failed(task, f"HTTP 错误: {e.response.status_code}")
    except requests.RequestException as e:
        mark_failed(task, f"网络请求异常: {str(e)}")
    except Exception as e:
        logger.exception(f"网页分析任务 {task_id} 异常")
        mark_failed(task, f"解析异常: {str(e)}")


def get_webpage_analysis_task(task_id: int) -> Task:
    return get_task_or_404(task_id, TaskType.WEBPAGE_ANALYSIS)


def list_webpage_analysis_tasks(page: int = 1, per_page: int = 20):
    return list_tasks(page=page, per_page=per_page, task_type=TaskType.WEBPAGE_ANALYSIS)


def retry_webpage_analysis_task(task_id: int) -> Task:
    task = get_webpage_analysis_task(task_id)
    detail = task.webpage_analysis
    if not detail:
        raise BusinessError(ErrorCode.TASK_NOT_FOUND)

    detail.title = None
    detail.summary = None
    detail.keywords = None
    reset_task(task)

    from app.tasks.webpage_analysis_task import analyze_webpage
    analyze_webpage.delay(task.id, task.tenant_id)

    logger.info(f"网页分析任务 {task.id} 已重新提交")
    return task


def delete_webpage_analysis_task(task_id: int) -> None:
    task = get_webpage_analysis_task(task_id)
    delete_task_record(task)


def webpage_analysis_task_to_dict(task: Task) -> dict:
    detail = task.webpage_analysis
    d = task_base_to_dict(task)
    d.update({
        "url": detail.url if detail else None,
        "title": detail.title if detail else None,
        "summary": detail.summary if detail else None,
        "keywords": detail.keywords if detail else None,
    })
    return d


def _extract_title(soup: BeautifulSoup) -> str:
    """提取网页标题"""

    if soup.title and soup.title.string:
        return soup.title.string.strip()
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return og["content"].strip()
    return "(无标题)"


def _extract_summary(soup: BeautifulSoup, max_len: int = 300) -> str:
    """提取网页摘要"""

    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        text = meta["content"].strip()
        if text:
            return text[:max_len]

    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    body = soup.find("body")
    if body:
        text = body.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        return text[:max_len]

    return "(无摘要)"


def _extract_keywords(soup: BeautifulSoup) -> list[str]:
    """提取关键词"""

    meta = soup.find("meta", attrs={"name": "keywords"})
    if meta and meta.get("content"):
        return [k.strip() for k in meta["content"].split(",") if k.strip()]
    return []
