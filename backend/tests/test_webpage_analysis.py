"""网页内容分析任务测试"""

import pytest
from unittest.mock import Mock, patch

from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.models.webpage_analysis_task import WebpageAnalysisTask


class TestWebpageAnalysisAPI:
    """网页内容分析 API 测试"""

    @pytest.fixture(autouse=True)
    def setup_user(self, client):
        client.post("/api/v1/auth/register", json={
            "username": "analyzer",
            "email": "analyzer@example.com",
            "password": "password123",
        })
        resp = client.post("/api/v1/auth/login", json={
            "username": "analyzer",
            "password": "password123",
        })
        self.token = resp.get_json()["data"]["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @patch("app.utils.ssrf._resolve_host", return_value="93.184.216.34")
    @patch("app.handlers.webpage_analysis._handler._celery_task.delay")
    def test_submit_webpage_analysis(self, mock_delay, mock_dns, client):
        resp = client.post("/api/v1/tasks/webpage-analysis/", json={
            "url": "https://example.com",
        }, headers=self.headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["code"] == 0
        assert data["data"]["status"] == "pending"
        assert data["data"]["task_type"] == TaskType.WEBPAGE_ANALYSIS
        assert data["data"]["task_type_name"] == "网页内容分析"
        assert data["data"]["url"] == "https://example.com"
        assert "id" in data["data"]
        mock_delay.assert_called_once()

    @patch("app.handlers.webpage_analysis._handler._celery_task.delay")
    def test_submit_invalid_url(self, mock_delay, client):
        resp = client.post("/api/v1/tasks/webpage-analysis/", json={
            "url": "not-a-url",
        }, headers=self.headers)
        assert resp.status_code == 400
        mock_delay.assert_not_called()

    @patch("app.handlers.webpage_analysis._handler._celery_task.delay")
    def test_submit_empty_body(self, mock_delay, client):
        resp = client.post("/api/v1/tasks/webpage-analysis/", json={}, headers=self.headers)
        assert resp.status_code == 400
        mock_delay.assert_not_called()

    def test_submit_no_auth(self, client):
        resp = client.post("/api/v1/tasks/webpage-analysis/", json={
            "url": "https://example.com",
        })
        assert resp.status_code == 401

    @patch("app.utils.ssrf._resolve_host", return_value="93.184.216.34")
    @patch("app.handlers.webpage_analysis._handler._celery_task.delay")
    def test_get_task(self, mock_delay, mock_dns, client):
        submit_resp = client.post("/api/v1/tasks/webpage-analysis/", json={
            "url": "https://example.com",
        }, headers=self.headers)
        task_id = submit_resp.get_json()["data"]["id"]

        resp = client.get(f"/api/v1/tasks/webpage-analysis/{task_id}", headers=self.headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["status"] == "pending"
        assert data["data"]["task_type"] == TaskType.WEBPAGE_ANALYSIS

    def test_get_task_not_found(self, client):
        resp = client.get("/api/v1/tasks/webpage-analysis/99999", headers=self.headers)
        assert resp.status_code == 404

    @patch("app.utils.ssrf._resolve_host", return_value="93.184.216.34")
    @patch("app.handlers.webpage_analysis._handler._celery_task.delay")
    def test_list_tasks(self, mock_delay, mock_dns, client):
        for i in range(2):
            client.post("/api/v1/tasks/webpage-analysis/", json={
                "url": f"https://example{i}.com",
            }, headers=self.headers)

        resp = client.get("/api/v1/tasks/webpage-analysis/?page=1&per_page=10", headers=self.headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["data"]["items"]) == 2
        assert data["data"]["total"] == 2
        assert {item["task_type"] for item in data["data"]["items"]} == {
            TaskType.WEBPAGE_ANALYSIS,
        }


HTML_NORMAL = """
<html>
<head>
  <title>测试页面标题</title>
  <meta name="description" content="这是一个测试页面的摘要描述。">
  <meta name="keywords" content="测试,Python,Flask">
</head>
<body>
  <h1>Hello World</h1>
  <p>这是正文第一段内容。</p>
</body>
</html>
"""

HTML_NO_META = """
<html>
<head><title>无 Meta 页面</title></head>
<body><p>只有正文内容，没有 meta 标签。</p></body>
</html>
"""

HTML_EMPTY_TITLE = """
<html>
<head><title></title></head>
<body><p>标题为空。</p></body>
</html>
"""

HTML_OG_TITLE = """
<html>
<head>
  <meta property="og:title" content="OG 标题">
</head>
<body><p>无 title 标签，但有 og:title。</p></body>
</html>
"""


class TestExecuteWebpageAnalysis:
    """Celery 任务 execute_webpage_analysis 逻辑测试"""

    @pytest.fixture(autouse=True)
    def setup(self, app):
        with app.app_context():
            from app import db
            from app.models.role import Role
            from app.models.tenant_membership import TenantMembership
            from tests.conftest import DEFAULT_TENANT_ID

            role = Role.query.filter_by(name="user").first()
            user = User(username="taskuser", email="task@test.com",
                        password_hash="hash")
            db.session.add(user)
            db.session.flush()
            db.session.add(TenantMembership(
                tenant_id=DEFAULT_TENANT_ID,
                user_id=user.id,
                role_id=role.id,
            ))
            db.session.flush()

            task = Task(
                tenant_id=DEFAULT_TENANT_ID,
                user_id=user.id,
                task_type=TaskType.WEBPAGE_ANALYSIS,
                status=TaskStatus.PENDING.value,
            )
            db.session.add(task)
            db.session.flush()
            db.session.add(WebpageAnalysisTask(
                tenant_id=DEFAULT_TENANT_ID,
                task_id=task.id,
                url="https://example.com",
            ))
            db.session.commit()
            self.task_id = task.id

    def _patch_requests(self, return_value=None, side_effect=None):
        """返回适用于 safe_requests_get 的 patcher 列表（含 DNS mock）"""
        patchers = [
            # SSRF 防护会做 DNS 解析，需要 mock
            patch("app.utils.ssrf._resolve_host", return_value="93.184.216.34"),
        ]
        if side_effect is not None:
            patchers.append(
                patch("app.utils.ssrf.requests.get", side_effect=side_effect)
            )
        else:
            patchers.append(
                patch("app.utils.ssrf.requests.get", return_value=return_value)
            )
        return patchers

    def test_execute_success(self, app):
        mock_resp = Mock()
        mock_resp.text = HTML_NORMAL
        mock_resp.raise_for_status = Mock()
        mock_resp.apparent_encoding = "utf-8"
        mock_resp.is_redirect = False

        with app.app_context():
            from app import db
            from app.services.webpage_analysis_service import execute_webpage_analysis

            with patch("app.utils.ssrf._resolve_host", return_value="93.184.216.34"), \
                 patch("app.utils.ssrf.requests.get", return_value=mock_resp):
                execute_webpage_analysis(self.task_id)

            task = db.session.get(Task, self.task_id)
            detail = task.webpage_analysis
            assert task.status == TaskStatus.SUCCESS.value
            assert detail.title == "测试页面标题"
            assert "测试页面" in detail.summary
            assert "测试" in detail.keywords
            assert task.completed_at is not None
            assert task.started_at is not None

    def test_execute_og_title_fallback(self, app):
        mock_resp = Mock()
        mock_resp.text = HTML_OG_TITLE
        mock_resp.raise_for_status = Mock()
        mock_resp.apparent_encoding = "utf-8"
        mock_resp.is_redirect = False

        with app.app_context():
            from app import db
            from app.services.webpage_analysis_service import execute_webpage_analysis

            with patch("app.utils.ssrf._resolve_host", return_value="93.184.216.34"), \
                 patch("app.utils.ssrf.requests.get", return_value=mock_resp):
                execute_webpage_analysis(self.task_id)

            detail = db.session.get(Task, self.task_id).webpage_analysis
            assert detail.title == "OG 标题"

    def test_execute_no_meta(self, app):
        mock_resp = Mock()
        mock_resp.text = HTML_NO_META
        mock_resp.raise_for_status = Mock()
        mock_resp.apparent_encoding = "utf-8"
        mock_resp.is_redirect = False

        with app.app_context():
            from app import db
            from app.services.webpage_analysis_service import execute_webpage_analysis

            with patch("app.utils.ssrf._resolve_host", return_value="93.184.216.34"), \
                 patch("app.utils.ssrf.requests.get", return_value=mock_resp):
                execute_webpage_analysis(self.task_id)

            detail = db.session.get(Task, self.task_id).webpage_analysis
            assert detail.title == "无 Meta 页面"
            assert "只有正文内容" in detail.summary

    def test_execute_empty_title(self, app):
        mock_resp = Mock()
        mock_resp.text = HTML_EMPTY_TITLE
        mock_resp.raise_for_status = Mock()
        mock_resp.apparent_encoding = "utf-8"
        mock_resp.is_redirect = False

        with app.app_context():
            from app import db
            from app.services.webpage_analysis_service import execute_webpage_analysis

            with patch("app.utils.ssrf._resolve_host", return_value="93.184.216.34"), \
                 patch("app.utils.ssrf.requests.get", return_value=mock_resp):
                execute_webpage_analysis(self.task_id)

            detail = db.session.get(Task, self.task_id).webpage_analysis
            assert detail.title == "(无标题)"

    def test_execute_timeout(self, app):
        import requests as requests_lib

        with app.app_context():
            from app import db
            from app.services.webpage_analysis_service import execute_webpage_analysis

            with patch("app.utils.ssrf._resolve_host", return_value="93.184.216.34"), \
                 patch("app.utils.ssrf.requests.get", side_effect=requests_lib.Timeout):
                execute_webpage_analysis(self.task_id)

            task = db.session.get(Task, self.task_id)
            assert task.status == TaskStatus.FAILED.value
            assert "超时" in task.error_message
            assert task.completed_at is not None

    def test_execute_connection_error(self, app):
        import requests as requests_lib

        with app.app_context():
            from app import db
            from app.services.webpage_analysis_service import execute_webpage_analysis

            with patch("app.utils.ssrf._resolve_host", return_value="93.184.216.34"), \
                 patch("app.utils.ssrf.requests.get", side_effect=requests_lib.ConnectionError):
                execute_webpage_analysis(self.task_id)

            task = db.session.get(Task, self.task_id)
            assert task.status == TaskStatus.FAILED.value
            assert "连接" in task.error_message

    def test_execute_http_404(self, app):
        import requests as requests_lib

        mock_resp = Mock()
        mock_resp.raise_for_status = Mock(
            side_effect=requests_lib.HTTPError(response=Mock(status_code=404))
        )
        mock_resp.is_redirect = False

        with app.app_context():
            from app import db
            from app.services.webpage_analysis_service import execute_webpage_analysis

            with patch("app.utils.ssrf._resolve_host", return_value="93.184.216.34"), \
                 patch("app.utils.ssrf.requests.get", return_value=mock_resp):
                execute_webpage_analysis(self.task_id)

            task = db.session.get(Task, self.task_id)
            assert task.status == TaskStatus.FAILED.value
            assert "HTTP" in task.error_message
            assert "404" in task.error_message

    def test_execute_parse_error(self, app):
        mock_resp = Mock()
        mock_resp.text = HTML_NORMAL
        mock_resp.raise_for_status = Mock()
        mock_resp.apparent_encoding = "utf-8"
        mock_resp.is_redirect = False

        with app.app_context():
            from app import db
            from app.services.webpage_analysis_service import execute_webpage_analysis

            with patch("app.utils.ssrf._resolve_host", return_value="93.184.216.34"), \
                 patch("app.utils.ssrf.requests.get", return_value=mock_resp), \
                 patch("app.services.webpage_analysis_service._extract_title",
                       side_effect=Exception("解析崩溃")):
                execute_webpage_analysis(self.task_id)

            task = db.session.get(Task, self.task_id)
            assert task.status == TaskStatus.FAILED.value
            assert "解析" in task.error_message
