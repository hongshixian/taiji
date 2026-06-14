"""任务执行日志测试"""

from unittest.mock import patch

from app.models.task import TaskType


class TestTaskLogs:
    @patch("app.handlers.webpage_analysis._handler._celery_task.delay")
    def test_task_create_writes_log_and_can_read(self, _mock_delay, client):
        client.post("/api/v1/auth/register", json={
            "username": "tasklog",
            "email": "tasklog@example.com",
            "password": "password123",
        })
        resp = client.post("/api/v1/auth/login", json={
            "username": "tasklog",
            "password": "password123",
        })
        token = resp.get_json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.post("/api/v1/tasks/webpage-analysis/", json={
            "url": "https://example.com",
        }, headers=headers)
        assert resp.status_code == 201
        task = resp.get_json()["data"]
        assert task["log_path"] == (
            f"tasks/tenant_2/{TaskType.WEBPAGE_ANALYSIS}/task_{task['id']}.jsonl"
        )

        resp = client.get(f"/api/v1/tasks/{task['id']}/logs", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["task_id"] == task["id"]
        assert data["task_type"] == TaskType.WEBPAGE_ANALYSIS
        assert data["log_path"] == task["log_path"]
        events = [item["event"] for item in data["items"]]
        assert "task_created" in events

    @patch("app.handlers.webpage_analysis._handler._celery_task.delay")
    def test_task_logs_are_tenant_scoped(self, _mock_delay, client, app):
        with app.app_context():
            from app import db
            from app.models.tenant import Tenant
            from app.services.auth_service import create_user

            db.session.add(Tenant(id=10, slug="tenant-a", name="租户A",
                                  is_active=True, is_system=False))
            db.session.add(Tenant(id=20, slug="tenant-b", name="租户B",
                                  is_active=True, is_system=False))
            db.session.commit()
            create_user("tasklog-a", "tasklog-a@test.com", "passa123", "admin", tenant_id=10)
            create_user("tasklog-b", "tasklog-b@test.com", "passb123", "admin", tenant_id=20)

        resp = client.post("/api/v1/auth/login",
                           json={"username": "tasklog-a", "password": "passa123"})
        token_a = resp.get_json()["data"]["access_token"]
        resp = client.post("/api/v1/auth/login",
                           json={"username": "tasklog-b", "password": "passb123"})
        token_b = resp.get_json()["data"]["access_token"]

        resp = client.post("/api/v1/tasks/webpage-analysis/", json={
            "url": "https://example.com",
        }, headers={"Authorization": f"Bearer {token_a}"})
        task_id = resp.get_json()["data"]["id"]

        resp = client.get(
            f"/api/v1/tasks/{task_id}/logs",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp.status_code == 404
