"""分析任务测试"""

import pytest
from unittest.mock import patch


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
        # 创建任务
        submit_resp = client.post("/api/analyze/", json={
            "url": "https://example.com",
        }, headers=self.headers)
        task_id = submit_resp.get_json()["data"]["id"]

        # 查询
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