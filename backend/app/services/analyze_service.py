"""网页分析服务"""

from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from app import db
from app.models.analyze_task import AnalyzeTask, TaskStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 抓取超时（秒）
REQUEST_TIMEOUT = 30


def create_task(user_id: int, url: str) -> AnalyzeTask:
    """创建分析任务

    Args:
        user_id: 用户 ID
        url: 目标网页 URL

    Returns:
        AnalyzeTask: 新创建的任务
    """
    task = AnalyzeTask(
        user_id=user_id,
        url=url,
        status=TaskStatus.PENDING,
    )
    db.session.add(task)
    db.session.commit()
    return task


def execute_analysis(task_id: int) -> None:
    """执行网页分析（在 Celery worker 中调用）

    Args:
        task_id: 任务 ID
    """
    # 查询任务
    task = db.session.get(AnalyzeTask, task_id)
    if not task:
        logger.error(f"任务 {task_id} 不存在")
        return

    # 更新状态为运行中
    task.status = TaskStatus.RUNNING
    task.started_at = datetime.now(timezone.utc)
    db.session.commit()

    logger.info(f"开始分析: {task.url}")

    try:
        # 抓取网页
        response = requests.get(
            task.url,
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

        # 解析 HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # 提取标题
        title = _extract_title(soup)

        # 提取摘要
        summary = _extract_summary(soup)

        # 提取关键词
        keywords = _extract_keywords(soup)

        # 更新任务结果
        task.status = TaskStatus.SUCCESS
        task.title = title
        task.summary = summary
        task.keywords = keywords
        task.completed_at = datetime.now(timezone.utc)
        db.session.commit()

        logger.info(f"分析完成: {task.url} → {title}")

    except requests.Timeout:
        _fail_task(task, "网页请求超时")
    except requests.ConnectionError:
        _fail_task(task, "无法连接到目标网址")
    except requests.HTTPError as e:
        _fail_task(task, f"HTTP 错误: {e.response.status_code}")
    except requests.RequestException as e:
        _fail_task(task, f"网络请求异常: {str(e)}")
    except Exception as e:
        logger.exception(f"分析任务 {task_id} 异常")
        _fail_task(task, f"解析异常: {str(e)}")


def get_task(task_id: int, user_id: int) -> AnalyzeTask | None:
    """查询单个任务（仅限拥有者）"""
    return AnalyzeTask.query.filter_by(id=task_id, user_id=user_id).first()


def get_user_tasks(user_id: int, page: int = 1, per_page: int = 20):
    """分页查询用户的任务列表"""
    return (
        AnalyzeTask.query
        .filter_by(user_id=user_id)
        .order_by(AnalyzeTask.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )


def task_to_dict(task: AnalyzeTask) -> dict:
    """将任务对象转为字典"""
    return {
        "id": task.id,
        "url": task.url,
        "status": task.status if isinstance(task.status, str) else task.status.value,
        "title": task.title,
        "summary": task.summary,
        "keywords": task.keywords,
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


# ─── 内部辅助函数 ────────────────────────────────────────────

def _extract_title(soup: BeautifulSoup) -> str:
    """提取网页标题"""
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    # 回退：og:title meta
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return og["content"].strip()
    return "(无标题)"


def _extract_summary(soup: BeautifulSoup, max_len: int = 300) -> str:
    """提取网页摘要"""
    # 优先使用 meta description
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        text = meta["content"].strip()
        if text:
            return text[:max_len]

    # 回退：正文前 300 字
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    body = soup.find("body")
    if body:
        text = body.get_text(separator=" ", strip=True)
        # 去掉多余空白
        import re
        text = re.sub(r"\s+", " ", text)
        return text[:max_len]

    return "(无摘要)"


def _extract_keywords(soup: BeautifulSoup) -> list[str]:
    """提取关键词"""
    meta = soup.find("meta", attrs={"name": "keywords"})
    if meta and meta.get("content"):
        return [k.strip() for k in meta["content"].split(",") if k.strip()]
    return []


def _fail_task(task: AnalyzeTask, message: str) -> None:
    """标记任务失败"""
    task.status = TaskStatus.FAILED
    task.error_message = message
    task.completed_at = datetime.now(timezone.utc)
    db.session.commit()
    logger.warning(f"任务 {task.id} 失败: {message}")

def retry_task(task_id: int, user_id: int) -> AnalyzeTask | None:
    """重试失败或超时的任务

    Args:
        task_id: 任务 ID
        user_id: 用户 ID

    Returns:
        AnalyzeTask | None: 重置后的任务，不存在或无权限返回 None
    """
    task = AnalyzeTask.query.filter_by(id=task_id, user_id=user_id).first()
    if not task:
        return None

    # 清除旧结果，重置为 PENDING
    task.status = TaskStatus.PENDING
    task.title = None
    task.summary = None
    task.keywords = None
    task.error_message = None
    task.started_at = None
    task.completed_at = None
    db.session.commit()

    # 重新提交到 Celery
    from app.tasks.analyze_task import analyze_webpage
    analyze_webpage.delay(task.id)

    logger.info(f"任务 {task.id} 已重新提交")
    return task
