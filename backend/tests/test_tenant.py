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
        from app.models.task import Task, TaskStatus, TaskType
        from app.services.auth_service import create_user
        from app.models.webpage_analysis_task import WebpageAnalysisTask

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
            task_a = Task(tenant_id=10, user_id=user_a.id,
                          task_type=TaskType.WEBPAGE_ANALYSIS,
                          status=TaskStatus.SUCCESS.value)
            task_b = Task(tenant_id=20, user_id=user_b.id,
                          task_type=TaskType.WEBPAGE_ANALYSIS,
                          status=TaskStatus.SUCCESS.value)
            db.session.add_all([task_a, task_b])
            db.session.flush()
            db.session.add(WebpageAnalysisTask(tenant_id=10, task_id=task_a.id,
                                               url="https://a.com",
                                               title="A 的任务"))
            db.session.add(WebpageAnalysisTask(tenant_id=20, task_id=task_b.id,
                                               url="https://b.com",
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
        """租户 A 用户只能看到 A 租户下的任务（租户内所有用户的任务均可见）"""
        resp = client.get("/api/v1/tasks/webpage-analysis/",
                          headers={"Authorization": f"Bearer {self.token_a}"})
        assert resp.status_code == 200
        items = resp.get_json()["data"]["items"]
        urls = [i["url"] for i in items]
        assert "https://a.com" in urls
        assert "https://b.com" not in urls  # 跨租户不可见

        resp = client.get("/api/v1/tasks/webpage-analysis/",
                          headers={"Authorization": f"Bearer {self.token_b}"})
        items = resp.get_json()["data"]["items"]
        urls = [i["url"] for i in items]
        assert "https://b.com" in urls
        assert "https://a.com" not in urls  # 跨租户不可见

    def test_cannot_access_other_tenant_task_by_id(self, client):
        """A 用 task_id 强行访问 B 的任务 → 404"""
        # 先拿到 B 的任务 id
        resp = client.get("/api/v1/tasks/webpage-analysis/",
                          headers={"Authorization": f"Bearer {self.token_b}"})
        b_task_id = resp.get_json()["data"]["items"][0]["id"]

        # A 试图访问
        resp = client.get(f"/api/v1/tasks/webpage-analysis/{b_task_id}",
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

    def test_user_can_switch_between_membership_tenants(self, client, app):
        """同一个全局用户可在多个租户身份之间切换"""
        with app.app_context():
            from app import db
            from app.models.task import Task, TaskStatus, TaskType
            from app.models.webpage_analysis_task import WebpageAnalysisTask
            from app.services.auth_service import create_user, add_user_membership

            user = create_user("multi", "multi@test.com", "multipass", "user", tenant_id=10)
            add_user_membership(user.id, 20, "user")
            task_a = Task(tenant_id=10, user_id=user.id,
                          task_type=TaskType.WEBPAGE_ANALYSIS,
                          status=TaskStatus.SUCCESS.value)
            task_b = Task(tenant_id=20, user_id=user.id,
                          task_type=TaskType.WEBPAGE_ANALYSIS,
                          status=TaskStatus.SUCCESS.value)
            db.session.add_all([task_a, task_b])
            db.session.flush()
            db.session.add(WebpageAnalysisTask(tenant_id=10, task_id=task_a.id,
                                               url="https://multi-a.com",
                                               title="multi A"))
            db.session.add(WebpageAnalysisTask(tenant_id=20, task_id=task_b.id,
                                               url="https://multi-b.com",
                                               title="multi B"))
            db.session.commit()

        resp = client.post("/api/v1/auth/login",
                           json={"username": "multi", "password": "multipass"})
        assert resp.status_code == 200
        token = resp.get_json()["data"]["access_token"]

        resp = client.get("/api/v1/tasks/webpage-analysis/",
                          headers={"Authorization": f"Bearer {token}"})
        urls = [i["url"] for i in resp.get_json()["data"]["items"]]
        assert "https://multi-a.com" in urls
        assert "https://a.com" in urls       # 同租户其他用户的任务也可见
        assert "https://b.com" not in urls   # 跨租户不可见

        resp = client.post("/api/v1/auth/switch-tenant",
                           headers={"Authorization": f"Bearer {token}"},
                           json={"tenant_id": 20})
        assert resp.status_code == 200
        token = resp.get_json()["data"]["access_token"]

        resp = client.get("/api/v1/tasks/webpage-analysis/",
                          headers={"Authorization": f"Bearer {token}"})
        urls = [i["url"] for i in resp.get_json()["data"]["items"]]
        assert "https://multi-b.com" in urls
        assert "https://b.com" in urls       # 同租户其他用户的任务也可见
        assert "https://a.com" not in urls   # 跨租户不可见

        resp = client.get("/api/v1/auth/me",
                          headers={"Authorization": f"Bearer {token}"})
        memberships = resp.get_json()["data"]["memberships"]
        assert {m["tenant_id"] for m in memberships} == {10, 20}

    def test_custom_roles_are_scoped_to_tenant(self, client, app):
        """租户自定义角色只在当前租户可见，同名角色可在不同租户独立定义"""
        resp = client.post(
            "/api/v1/admin/roles",
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={
                "name": "operator",
                "description": "A 租户运营",
                "permissions": ["task:read"],
            },
        )
        assert resp.status_code == 201
        role_a = resp.get_json()["data"]
        assert role_a["tenant_id"] == 10
        assert role_a["permissions"] == ["task:read"]

        resp = client.get("/api/v1/admin/roles",
                          headers={"Authorization": f"Bearer {self.token_b}"})
        assert resp.status_code == 200
        assert "operator" not in [r["name"] for r in resp.get_json()["data"]]

        resp = client.post(
            "/api/v1/admin/roles",
            headers={"Authorization": f"Bearer {self.token_b}"},
            json={
                "name": "operator",
                "description": "B 租户运营",
                "permissions": ["task:create"],
            },
        )
        assert resp.status_code == 201
        role_b = resp.get_json()["data"]
        assert role_b["tenant_id"] == 20
        assert role_b["id"] != role_a["id"]
        assert role_b["permissions"] == ["task:create"]

        resp = client.get("/api/v1/admin/roles",
                          headers={"Authorization": f"Bearer {self.token_a}"})
        role_map = {r["name"]: r for r in resp.get_json()["data"]}
        assert role_map["operator"]["tenant_id"] == 10
        assert role_map["operator"]["permissions"] == ["task:read"]

        resp = client.post(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {self.token_b}"},
            json={
                "username": "operator-b",
                "email": "operator-b@test.com",
                "password": "operatorpass",
                "role": "operator",
            },
        )
        assert resp.status_code == 201

        with app.app_context():
            from app.models.user import User
            from app.models.tenant_membership import TenantMembership
            from app.utils.decorators import bypass_tenant_filter

            with bypass_tenant_filter():
                user = User.query.filter_by(username="operator-b").first()
                membership = TenantMembership.query.filter_by(
                    user_id=user.id,
                    tenant_id=20,
                ).first()
            assert membership.role_id == role_b["id"]

        resp = client.post("/api/v1/auth/login",
                           json={"username": "operator-b", "password": "operatorpass"})
        token = resp.get_json()["data"]["access_token"]
        resp = client.get("/api/v1/auth/me",
                          headers={"Authorization": f"Bearer {token}"})
        assert set(resp.get_json()["data"]["permissions"]) == {"task:create"}

    def test_register_goes_to_guest_tenant(self, client, app):
        """新注册用户自动获得 guest 租户成员身份"""
        resp = client.post("/api/v1/auth/register", json={
            "username": "newbie",
            "email": "newbie@test.com",
            "password": "newbiepass",
        })
        assert resp.status_code == 201

        # 直接查 DB 验证 membership.tenant_id
        with app.app_context():
            from app.models.user import User
            from app.models.tenant_membership import TenantMembership
            from app.utils.decorators import bypass_tenant_filter
            from tests.conftest import GUEST_TENANT_ID
            from flask import g
            g.bypass_tenant_filter = True
            try:
                user = User.query.filter_by(username="newbie").first()
                membership = TenantMembership.query.filter_by(user_id=user.id).first()
            finally:
                g.bypass_tenant_filter = False
            assert user is not None
            assert membership.tenant_id == GUEST_TENANT_ID

    def test_username_unique_globally(self, client):
        """用户名全局唯一，不允许跨 tenant 重名"""
        resp = client.post("/api/v1/auth/register", json={
            "username": "admina",  # 与 tenant_a 的 admina 同名
            "email": "newadmina@guest.com",
            "password": "guestpass",
        })
        assert resp.status_code == 400
        assert resp.get_json()["code"] == 10001

    def test_system_setting_default_registration_tenant_superuser_only(self, client, app):
        """系统设置仅超级管理员可改，且影响新注册用户默认租户"""
        # 普通租户管理员不可访问平台系统设置
        resp = client.get("/api/v1/superadmin/settings",
                          headers={"Authorization": f"Bearer {self.token_a}"})
        assert resp.status_code == 403

        with app.app_context():
            from app import db
            from app.services.auth_service import create_user
            from tests.conftest import DEFAULT_TENANT_ID

            superuser = create_user(
                "platform-admin",
                "platform-admin@test.com",
                "superpass",
                "admin",
                tenant_id=DEFAULT_TENANT_ID,
            )
            superuser.is_superuser = True
            db.session.commit()

        resp = client.post("/api/v1/auth/login",
                           json={"username": "platform-admin", "password": "superpass"})
        super_token = resp.get_json()["data"]["access_token"]

        resp = client.put("/api/v1/superadmin/settings",
                          headers={"Authorization": f"Bearer {super_token}"},
                          json={"public.default_registration_tenant_slug": "tenant-a"})
        assert resp.status_code == 200
        settings = {s["key"]: s["value"] for s in resp.get_json()["data"]}
        assert settings["public.default_registration_tenant_slug"] == "tenant-a"

        resp = client.post("/api/v1/auth/register", json={
            "username": "configured-newbie",
            "email": "configured-newbie@test.com",
            "password": "newbiepass",
        })
        assert resp.status_code == 201

        with app.app_context():
            from app.models.user import User
            from app.models.tenant_membership import TenantMembership
            from app.utils.decorators import bypass_tenant_filter

            with bypass_tenant_filter():
                user = User.query.filter_by(username="configured-newbie").first()
                membership = TenantMembership.query.filter_by(user_id=user.id).first()
            assert membership.tenant_id == 10

    def test_superuser_can_manage_superuser_list(self, client, app):
        """超级管理员可以添加/移除其他用户的超级管理员身份"""
        with app.app_context():
            from app import db
            from app.services.auth_service import create_user
            from tests.conftest import DEFAULT_TENANT_ID

            superuser = create_user(
                "platform-admin-list",
                "platform-admin-list@test.com",
                "superpass",
                "admin",
                tenant_id=DEFAULT_TENANT_ID,
            )
            superuser.is_superuser = True
            candidate = create_user(
                "super-candidate",
                "super-candidate@test.com",
                "candidatepass",
                "user",
                tenant_id=DEFAULT_TENANT_ID,
            )
            db.session.commit()
            candidate_id = candidate.id

        resp = client.post("/api/v1/auth/login",
                           json={"username": "platform-admin-list", "password": "superpass"})
        token = resp.get_json()["data"]["access_token"]

        resp = client.post("/api/v1/superadmin/superusers",
                           headers={"Authorization": f"Bearer {token}"},
                           json={"identifier": "super-candidate"})
        assert resp.status_code == 200
        assert resp.get_json()["data"]["is_superuser"] is True

        resp = client.get("/api/v1/superadmin/superusers",
                          headers={"Authorization": f"Bearer {token}"})
        assert "super-candidate" in [u["username"] for u in resp.get_json()["data"]]

        resp = client.delete(f"/api/v1/superadmin/superusers/{candidate_id}",
                             headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

        with app.app_context():
            from app import db
            from app.models.user import User
            refreshed = db.session.get(User, candidate_id)
            assert refreshed.is_superuser is False

    def test_superuser_can_manage_tenant_members(self, client, app):
        """超级管理员可以向任意租户添加和移除成员"""
        with app.app_context():
            from app import db
            from app.services.auth_service import create_user
            from tests.conftest import DEFAULT_TENANT_ID

            superuser = create_user(
                "platform-admin-members",
                "platform-admin-members@test.com",
                "superpass",
                "admin",
                tenant_id=DEFAULT_TENANT_ID,
            )
            superuser.is_superuser = True
            member = create_user(
                "tenant-added",
                "tenant-added@test.com",
                "memberpass",
                "user",
                tenant_id=DEFAULT_TENANT_ID,
            )
            db.session.commit()
            member_id = member.id

        resp = client.post("/api/v1/auth/login",
                           json={"username": "platform-admin-members", "password": "superpass"})
        token = resp.get_json()["data"]["access_token"]

        resp = client.post("/api/v1/superadmin/tenants/10/members",
                           headers={"Authorization": f"Bearer {token}"},
                           json={
                               "identifier": "tenant-added",
                               "role": "user",
                           })
        assert resp.status_code == 200
        assert resp.get_json()["data"]["id"] == member_id

        resp = client.get("/api/v1/superadmin/tenants/10/members",
                          headers={"Authorization": f"Bearer {token}"})
        assert "tenant-added" in [u["username"] for u in resp.get_json()["data"]]

        resp = client.delete(f"/api/v1/superadmin/tenants/10/members/{member_id}",
                             headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

        resp = client.get("/api/v1/superadmin/tenants/10/members",
                          headers={"Authorization": f"Bearer {token}"})
        assert "tenant-added" not in [u["username"] for u in resp.get_json()["data"]]

        resp = client.post("/api/v1/superadmin/tenants/10/members",
                           headers={"Authorization": f"Bearer {token}"},
                           json={
                               "identifier": "not-registered-user",
                               "role": "user",
                           })
        assert resp.status_code == 404
        assert resp.get_json()["code"] == 10005
