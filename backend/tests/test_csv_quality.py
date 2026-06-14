"""CSV 数据质量检查任务测试"""

import pytest
from io import BytesIO
from unittest.mock import patch

from app.models.csv_quality_task import CsvQualityTask
from app.models.task import Task, TaskStatus, TaskType


class TestCsvQualityAPI:
    """CSV 数据质量检查 API 测试"""

    @pytest.fixture(autouse=True)
    def setup_user(self, client):
        client.post("/api/v1/auth/register", json={
            "username": "csvuser",
            "email": "csvuser@example.com",
            "password": "password123",
        })
        resp = client.post("/api/v1/auth/login", json={
            "username": "csvuser",
            "password": "password123",
        })
        self.token = resp.get_json()["data"]["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @patch("app.handlers.csv_quality._handler._celery_task.delay")
    def test_submit_csv_quality(self, mock_delay, client):
        resp = client.post(
            "/api/v1/tasks/csv-quality/",
            data={
                "task_name": "用户数据检查",
                "file": (
                    BytesIO("name,email,age\nAlice,alice@example.com,30\nBob,,28".encode()),
                    "users.csv",
                ),
            },
            headers=self.headers,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["status"] == "pending"
        assert data["task_type"] == TaskType.CSV_QUALITY
        assert data["task_type_name"] == "CSV 数据质量检查"
        assert data["task_name"] == "用户数据检查"
        assert data["filename"] == "users.csv"
        assert "name,email" in data["content_sample"]
        mock_delay.assert_called_once()

    @patch("app.handlers.csv_quality._handler._celery_task.delay")
    def test_submit_missing_task_name(self, mock_delay, client):
        resp = client.post(
            "/api/v1/tasks/csv-quality/",
            data={
                "task_name": " ",
                "file": (BytesIO(b"a,b\n1,2"), "data.csv"),
            },
            headers=self.headers,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        mock_delay.assert_not_called()

    @patch("app.handlers.csv_quality._handler._celery_task.delay")
    def test_submit_missing_file(self, mock_delay, client):
        resp = client.post(
            "/api/v1/tasks/csv-quality/",
            data={"task_name": "缺少文件"},
            headers=self.headers,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        mock_delay.assert_not_called()

    def test_submit_no_auth(self, client):
        resp = client.post(
            "/api/v1/tasks/csv-quality/",
            data={
                "task_name": "未登录",
                "file": (BytesIO(b"a,b\n1,2"), "data.csv"),
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 401

    @patch("app.handlers.csv_quality._handler._celery_task.delay")
    def test_get_and_list_csv_quality(self, mock_delay, client):
        submit_resp = client.post(
            "/api/v1/tasks/csv-quality/",
            data={
                "task_name": "邮箱检查",
                "file": (BytesIO(b"name,email\nAlice,a@test.com"), "emails.csv"),
            },
            headers=self.headers,
            content_type="multipart/form-data",
        )
        task_id = submit_resp.get_json()["data"]["id"]

        resp = client.get(f"/api/v1/tasks/csv-quality/{task_id}", headers=self.headers)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["task_type"] == TaskType.CSV_QUALITY

        resp = client.get("/api/v1/tasks/csv-quality/?page=1&per_page=10", headers=self.headers)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["total"] == 1
        assert data["items"][0]["id"] == task_id


class TestCsvQualityLogic:
    """CSV 解析与检查逻辑测试"""

    def test_analyze_csv_text(self):
        from app.services.csv_quality_service import analyze_csv_text

        result = analyze_csv_text(
            "name,email,age,active\n"
            "Alice,alice@example.com,30,true\n"
            "Bob,,28,false\n"
            "Bob,,28,false\n"
        )
        assert result["row_count"] == 4
        assert result["data_row_count"] == 3
        assert result["column_count"] == 4
        assert result["columns"] == ["name", "email", "age", "active"]
        assert result["empty_counts"]["email"] == 2
        assert result["duplicate_rows"] == 1
        assert result["type_inference"]["age"] == "integer"
        assert result["type_inference"]["active"] == "boolean"
        assert len(result["preview"]) == 3
        assert any("重复" in warning for warning in result["warnings"])

    def test_execute_csv_quality_check(self, app):
        with app.app_context():
            from app import db
            from app.models.role import Role
            from app.models.tenant_membership import TenantMembership
            from app.models.user import User
            from app.services.csv_quality_service import execute_csv_quality_check
            from tests.conftest import DEFAULT_TENANT_ID

            role = Role.query.filter_by(name="user").first()
            user = User(username="csvtask", email="csvtask@test.com",
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
                task_type=TaskType.CSV_QUALITY,
                status=TaskStatus.PENDING.value,
            )
            db.session.add(task)
            db.session.flush()
            db.session.add(CsvQualityTask(
                tenant_id=DEFAULT_TENANT_ID,
                task_id=task.id,
                task_name="样例检查",
                filename="sample.csv",
                input_text="name,age\nAlice,30\nBob,28",
                content_sample="name,age\nAlice,30\nBob,28",
            ))
            db.session.commit()

            execute_csv_quality_check(task.id)

            refreshed = db.session.get(Task, task.id)
            assert refreshed.status == TaskStatus.SUCCESS.value
            assert refreshed.csv_quality.result["data_row_count"] == 2
            assert refreshed.csv_quality.result["type_inference"]["age"] == "integer"
