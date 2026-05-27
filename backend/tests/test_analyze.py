"""分析任务测试"""

import pytest
from unittest.mock import patch, Mock

from app.models.user import User
from app.models.analyze_task import AnalyzeTask, TaskStatus


class TestAnalyzeAPI:
    """分析任务 API 测试"""

    @pytest.fixture(autouse=True)
    def setup_user(self, client):
        """注册 + 登录，获取 token"""
        client.post("/api/auth/register", json={
            "username": "analyzer",
            "email": "analyzer@example.com",
            "password": "password123",
        })
        resp = client.post("/api/auth/login", json={
            "username": "analyzer",
            "password": "password123",
        })
        self.token = resp.get_json()["data"]["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @patch("app.api.analyze.analyze_webpage.delay")
    def test_submit_analysis(self, mock_delay, client):
        """提交分析任务成功（mock Celery 调用）"""
        resp = client.post("/api/analyze/", json={
            "url": "https://example.com",
        }, headers=self.headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["code"] == 0
        assert data["data"]["status"] == "pending"
        assert "id" in data["data"]
        mock_delay.assert_called_once()

    @patch("app.api.analyze.analyze_webpage.delay")
    def test_submit_invalid_url(self, mock_delay, client):
        """无效 URL → 400"""
        resp = client.post("/api/analyze/", json={
            "url": "not-a-url",
        }, headers=self.headers)
        assert resp.status_code == 400
        mock_delay.assert_not_called()

    @patch("app.api.analyze.analyze_webpage.delay")
    def test_submit_empty_body(self, mock_delay, client):
        """空请求体 → 400"""
        resp = client.post("/api/analyze/", json={}, headers=self.headers)
        assert resp.status_code == 400
        mock_delay.assert_not_called()

    def test_submit_no_auth(self, client):
        """未登录提交 → 401"""
        resp = client.post("/api/analyze/", json={
            "url": "https://example.com",
        })
        assert resp.status_code == 401

    @patch("app.api.analyze.analyze_webpage.delay")
    def test_get_task(self, mock_delay, client):
        """查询单个任务"""
        submit_resp = client.post("/api/analyze/", json={
            "url": "https://example.com",
        }, headers=self.headers)
        task_id = submit_resp.get_json()["data"]["id"]

        resp = client.get(f"/api/analyze/{task_id}", headers=self.headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["status"] == "pending"

    def test_get_task_not_found(self, client):
        """查询不存在的任务"""
        resp = client.get("/api/analyze/99999", headers=self.headers)
        assert resp.status_code == 404

    @patch("app.api.analyze.analyze_webpage.delay")
    def test_list_tasks(self, mock_delay, client):
        """分页查询列表"""
        for i in range(2):
            client.post("/api/analyze/", json={
                "url": f"https://example{i}.com",
            }, headers=self.headers)

        resp = client.get("/api/analyze/?page=1&per_page=10", headers=self.headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["data"]["items"]) == 2
        assert data["data"]["total"] == 2


# ═══════════════════════════════════════════════════════════════
# Celery 任务逻辑单元测试（mock requests）
# ═══════════════════════════════════════════════════════════════

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


class TestExecuteAnalysis:
    """Celery 任务 execute_analysis 逻辑测试"""

    @pytest.fixture(autouse=True)
    def setup(self, app):
        """每个测试前创建用户和任务"""
        with app.app_context():
            from app import db
            user = User(username="taskuser", email="task@test.com",
                        password_hash="hash")
            db.session.add(user)
            db.session.commit()
            self.user_id = user.id

            task = AnalyzeTask(user_id=user.id, url="https://example.com",
                               status=TaskStatus.PENDING)
            db.session.add(task)
            db.session.commit()
            self.task_id = task.id

    def test_execute_success(self, app):
        """正常网页 → 成功提取标题/摘要/关键词"""
        mock_resp = Mock()
        mock_resp.text = HTML_NORMAL
        mock_resp.raise_for_status = Mock()
        mock_resp.apparent_encoding = "utf-8"

        with app.app_context():
            from app.services.analyze_service import execute_analysis
            from app import db

            with patch("app.services.analyze_service.requests.get",
                       return_value=mock_resp):
                execute_analysis(self.task_id)

            task = db.session.get(AnalyzeTask, self.task_id)
            assert task.status == TaskStatus.SUCCESS
            assert task.title == "测试页面标题"
            assert "测试页面" in task.summary
            assert "测试" in task.keywords
            assert task.completed_at is not None
            assert task.started_at is not None

    def test_execute_og_title_fallback(self, app):
        """无 title 标签 → 回退 og:title"""
        mock_resp = Mock()
        mock_resp.text = HTML_OG_TITLE
        mock_resp.raise_for_status = Mock()
        mock_resp.apparent_encoding = "utf-8"

        with app.app_context():
            from app.services.analyze_service import execute_analysis
            from app import db

            with patch("app.services.analyze_service.requests.get",
                       return_value=mock_resp):
                execute_analysis(self.task_id)

            task = db.session.get(AnalyzeTask, self.task_id)
            assert task.status == TaskStatus.SUCCESS
            assert task.title == "OG 标题"

    def test_execute_no_meta(self, app):
        """无 meta 标签 → 回退正文提取"""
        mock_resp = Mock()
        mock_resp.text = HTML_NO_META
        mock_resp.raise_for_status = Mock()
        mock_resp.apparent_encoding = "utf-8"

        with app.app_context():
            from app.services.analyze_service import execute_analysis
            from app import db

            with patch("app.services.analyze_service.requests.get",
                       return_value=mock_resp):
                execute_analysis(self.task_id)

            task = db.session.get(AnalyzeTask, self.task_id)
            assert task.status == TaskStatus.SUCCESS
            assert task.title == "无 Meta 页面"
            assert "只有正文内容" in task.summary

    def test_execute_empty_title(self, app):
        """空标题 → 返回 '(无标题)'"""
        mock_resp = Mock()
        mock_resp.text = HTML_EMPTY_TITLE
        mock_resp.raise_for_status = Mock()
        mock_resp.apparent_encoding = "utf-8"

        with app.app_context():
            from app.services.analyze_service import execute_analysis
            from app import db

            with patch("app.services.analyze_service.requests.get",
                       return_value=mock_resp):
                execute_analysis(self.task_id)

            task = db.session.get(AnalyzeTask, self.task_id)
            assert task.status == TaskStatus.SUCCESS
            assert task.title == "(无标题)"

    def test_execute_timeout(self, app):
        """请求超时 → status=failed"""
        import requests as requests_lib

        with app.app_context():
            from app.services.analyze_service import execute_analysis
            from app import db

            with patch("app.services.analyze_service.requests.get",
                       side_effect=requests_lib.Timeout):
                execute_analysis(self.task_id)

            task = db.session.get(AnalyzeTask, self.task_id)
            assert task.status == TaskStatus.FAILED
            assert "超时" in task.error_message
            assert task.completed_at is not None

    def test_execute_connection_error(self, app):
        """连接错误 → status=failed"""
        import requests as requests_lib

        with app.app_context():
            from app.services.analyze_service import execute_analysis
            from app import db

            with patch("app.services.analyze_service.requests.get",
                       side_effect=requests_lib.ConnectionError):
                execute_analysis(self.task_id)

            task = db.session.get(AnalyzeTask, self.task_id)
            assert task.status == TaskStatus.FAILED
            assert "连接" in task.error_message

    def test_execute_http_404(self, app):
        """HTTP 404 → status=failed"""
        import requests as requests_lib

        mock_resp = Mock()
        mock_resp.raise_for_status = Mock(
            side_effect=requests_lib.HTTPError(response=Mock(status_code=404))
        )

        with app.app_context():
            from app.services.analyze_service import execute_analysis
            from app import db

            with patch("app.services.analyze_service.requests.get",
                       return_value=mock_resp):
                execute_analysis(self.task_id)

            task = db.session.get(AnalyzeTask, self.task_id)
            assert task.status == TaskStatus.FAILED
            assert "HTTP" in task.error_message
            assert "404" in task.error_message

    def test_execute_parse_error(self, app):
        """HTML 解析异常 → status=failed"""
        with app.app_context():
            from app.services.analyze_service import execute_analysis
            from app import db

            with patch("app.services.analyze_service.requests.get") as mock_get:
                mock_resp = Mock()
                mock_resp.text = HTML_NORMAL
                mock_resp.raise_for_status = Mock()
                mock_resp.apparent_encoding = "utf-8"
                mock_get.return_value = mock_resp

                with patch("app.services.analyze_service._extract_title",
                           side_effect=Exception("解析崩溃")):
                    execute_analysis(self.task_id)

            task = db.session.get(AnalyzeTask, self.task_id)
            assert task.status == TaskStatus.FAILED
            assert "解析" in task.error_message