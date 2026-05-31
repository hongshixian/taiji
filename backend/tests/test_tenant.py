"""多租户隔离测试 — 验证不同 tenant 的数据不会互相泄漏"""

import pytest


class TestTenantIsolation:
    """跨租户数据隔离"""

    @pytest.fixture(autouse=True)
    def setup_tenants(self, app, client):
        """建两个 tenant + 每个 tenant 一个 admin 用户"""
        from app import db
        from app.models.tenant import Tenant
        from app.models.user import User
        from app.models.analyze_task import AnalyzeTask, TaskStatus
        from app.services.auth_service import create_user

        with app.app_context():
            # 新建 tenant_a / tenant_b（除了 default/guest 之外）
            db.session.add(Tenant(id=10, slug="tenant-a", name="租户A",
                                  is_active=True, is_system=False))
            db.session.add(Tenant(id=20, slug="tenant-b", name="租户B",
                                  is_active=True, is_system=False))
            db.session.commit()

            # 各自一个 admin（拥有 task:read/create）
            user_a = create_user("admina", "a@a.com", "passa123", "admin", tenant_id=10)
            user_b = create_user("adminb", "b@b.com", "passb123", "admin", tenant_id=20)

            # 各自一条任务（用真实 user.id，避免 ID 假设）
            db.session.add(AnalyzeTask(tenant_id=10, user_id=user_a.id,
                                        url="https://a.com",
                                        status=TaskStatus.SUCCESS,
                                        title="A 的任务"))
            db.session.add(AnalyzeTask(tenant_id=20, user_id=user_b.id,
                                        url="https://b.com",
                                        status=TaskStatus.SUCCESS,
                                        title="B 的任务"))
            db.session.commit()

        # 登录 A
        resp = client.post("/api/v1/auth/login",
                           json={"username": "admina", "password": "passa123"})
        self.token_a = resp.get_json()["data"]["access_token"]
        # 登录 B
        resp = client.post("/api/v1/auth/login",
                           json={"username": "adminb", "password": "passb123"})
        self.token_b = resp.get_json()["data"]["access_token"]

    def test_user_only_sees_own_tenant_tasks(self, client):
        """租户 A 用户只能看到 A 的任务"""
        resp = client.get("/api/v1/analyze/",
                          headers={"Authorization": f"Bearer {self.token_a}"})
        assert resp.status_code == 200
        items = resp.get_json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["url"] == "https://a.com"

        resp = client.get("/api/v1/analyze/",
                          headers={"Authorization": f"Bearer {self.token_b}"})
        items = resp.get_json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["url"] == "https://b.com"

    def test_cannot_access_other_tenant_task_by_id(self, client):
        """A 用 task_id 强行访问 B 的任务 → 404"""
        # 先拿到 B 的任务 id
        resp = client.get("/api/v1/analyze/",
                          headers={"Authorization": f"Bearer {self.token_b}"})
        b_task_id = resp.get_json()["data"]["items"][0]["id"]

        # A 试图访问
        resp = client.get(f"/api/v1/analyze/{b_task_id}",
                          headers={"Authorization": f"Bearer {self.token_a}"})
        assert resp.status_code == 404
        assert resp.get_json()["code"] == 20001  # TASK_NOT_FOUND

    def test_admin_user_list_scoped_to_tenant(self, client):
        """tenant A 的 admin 只能看到 A 的用户列表"""
        resp = client.get("/api/v1/admin/users",
                          headers={"Authorization": f"Bearer {self.token_a}"})
        assert resp.status_code == 200
        usernames = [u["username"] for u in resp.get_json()["data"]["items"]]
        assert "admina" in usernames
        assert "adminb" not in usernames

    def test_register_goes_to_guest_tenant(self, client, app):
        """新注册用户自动进 guest 租户"""
        resp = client.post("/api/v1/auth/register", json={
            "username": "newbie",
            "email": "newbie@test.com",
            "password": "newbiepass",
        })
        assert resp.status_code == 201

        # 直接查 DB 验证 tenant_id
        with app.app_context():
            from app.models.user import User
            from app.utils.decorators import bypass_tenant_filter
            from tests.conftest import GUEST_TENANT_ID
            from flask import g
            # fixture 上下文里，g 可能未初始化，手动控制
            g.bypass_tenant_filter = True
            try:
                user = User.query.filter_by(username="newbie").first()
            finally:
                g.bypass_tenant_filter = False
            assert user is not None
            assert user.tenant_id == GUEST_TENANT_ID

    def test_username_unique_within_tenant_only(self, client):
        """同名用户在不同 tenant 下可共存"""
        # tenant A 已经有 admina；tenant B 也注册一个同名（B 是个 guest 租户场景）
        # 现 register 默认进 guest，所以注册 admina 应该成功（不与 tenant_a 的 admina 冲突）
        resp = client.post("/api/v1/auth/register", json={
            "username": "admina",  # 与 tenant_a 的 admina 同名
            "email": "newadmina@guest.com",
            "password": "guestpass",
        })
        # 应该成功（guest tenant 内 admina 不存在）
        assert resp.status_code == 201, resp.get_json()
