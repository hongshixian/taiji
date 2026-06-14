"""认证系统测试"""

import pytest


class TestRegister:
    """用户注册测试"""

    def test_register_success(self, client):
        """注册成功"""
        resp = client.post("/api/v1/auth/register", json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "123456",
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["code"] == 0
        assert data["data"]["username"] == "testuser"

    def test_register_duplicate_username(self, client):
        """重复用户名报错"""
        # 先注册一个
        client.post("/api/v1/auth/register", json={
            "username": "dupuser",
            "email": "dup1@example.com",
            "password": "123456",
        })
        # 再注册同名
        resp = client.post("/api/v1/auth/register", json={
            "username": "dupuser",
            "email": "dup2@example.com",
            "password": "123456",
        })
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["code"] == 10001  # USER_EXISTS
        assert "已存在" in data["message"]

    def test_register_short_password(self, client):
        """短密码报错"""
        resp = client.post("/api/v1/auth/register", json={
            "username": "spuser",
            "email": "sp@example.com",
            "password": "123",
        })
        assert resp.status_code == 400

    def test_register_short_username(self, client):
        """短用户名报错"""
        resp = client.post("/api/v1/auth/register", json={
            "username": "ab",
            "email": "ab@example.com",
            "password": "123456",
        })
        assert resp.status_code == 400

    def test_register_empty_body(self, client):
        """空请求体"""
        resp = client.post("/api/v1/auth/register", json={})
        assert resp.status_code == 400


class TestLogin:
    """用户登录测试"""

    @pytest.fixture(autouse=True)
    def setup_user(self, client):
        """每个测试前注册一个用户"""
        client.post("/api/v1/auth/register", json={
            "username": "loginuser",
            "email": "login@example.com",
            "password": "password123",
        })

    def test_login_success(self, client):
        """登录成功，返回 token"""
        resp = client.post("/api/v1/auth/login", json={
            "username": "loginuser",
            "password": "password123",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["code"] == 0
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]

    def test_login_wrong_password(self, client):
        """密码错误"""
        resp = client.post("/api/v1/auth/login", json={
            "username": "loginuser",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    def test_login_empty_body(self, client):
        """空请求体"""
        resp = client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 400

    def test_login_rejects_tenant_slug(self, client):
        """登录不再接受租户参数，租户切换应走 /auth/switch-tenant"""
        resp = client.post("/api/v1/auth/login", json={
            "username": "loginuser",
            "password": "password123",
            "tenant_slug": "guest",
        })
        assert resp.status_code == 400
        assert resp.get_json()["code"] == 90001


class TestAuthRequired:
    """鉴权测试"""

    @pytest.fixture(autouse=True)
    def setup_token(self, client):
        """注册 + 登录，获取 access token"""
        client.post("/api/v1/auth/register", json={
            "username": "meuser",
            "email": "me@example.com",
            "password": "password123",
        })
        resp = client.post("/api/v1/auth/login", json={
            "username": "meuser",
            "password": "password123",
        })
        self.token = resp.get_json()["data"]["access_token"]
        self.refresh_token = resp.get_json()["data"]["refresh_token"]

    def test_me_with_token(self, client):
        """带 token 访问 /me"""
        resp = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {self.token}",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["username"] == "meuser"

    def test_me_without_token(self, client):
        """不带 token 访问 /me → 401"""
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401
    
    def test_me_with_invalid_token(self, client):
        """无效 token → 401"""
        resp = client.get("/api/v1/auth/me", headers={
            "Authorization": "Bearer invalidtoken",
        })
        assert resp.status_code == 401

    def test_refresh_token(self, client):
        """刷新 access token"""
        resp = client.post("/api/v1/auth/refresh", headers={
            "Authorization": f"Bearer {self.refresh_token}",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert "access_token" in data["data"]


class TestLogout:
    """登出测试"""

    @pytest.fixture(autouse=True)
    def setup_token(self, client):
        client.post("/api/v1/auth/register", json={
            "username": "logoutuser",
            "email": "logout@example.com",
            "password": "password123",
        })
        resp = client.post("/api/v1/auth/login", json={
            "username": "logoutuser",
            "password": "password123",
        })
        self.token = resp.get_json()["data"]["access_token"]

    def test_logout_revokes_token(self, client):
        """登出后 token 应失效"""
        # 登出前可以访问 /me
        resp = client.get("/api/v1/auth/me",
                          headers={"Authorization": f"Bearer {self.token}"})
        assert resp.status_code == 200

        # 登出
        resp = client.post("/api/v1/auth/logout",
                           headers={"Authorization": f"Bearer {self.token}"})
        assert resp.status_code == 200

        # 登出后访问 /me 应 401 / TOKEN_REVOKED
        resp = client.get("/api/v1/auth/me",
                          headers={"Authorization": f"Bearer {self.token}"})
        assert resp.status_code == 401
        assert resp.get_json()["code"] == 30006  # TOKEN_REVOKED

    def test_logout_no_token(self, client):
        """未登录调登出 → 401"""
        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 401


class TestChangePassword:
    """修改密码测试"""

    @pytest.fixture(autouse=True)
    def setup_token(self, client):
        client.post("/api/v1/auth/register", json={
            "username": "pwduser",
            "email": "pwd@example.com",
            "password": "oldpass123",
        })
        resp = client.post("/api/v1/auth/login", json={
            "username": "pwduser",
            "password": "oldpass123",
        })
        self.token = resp.get_json()["data"]["access_token"]

    def test_change_password_revokes_all_tokens(self, client):
        """改密后旧 token 失效，新密码登录得新 token"""
        # 改密
        resp = client.put("/api/v1/auth/password",
                          headers={"Authorization": f"Bearer {self.token}"},
                          json={"old_password": "oldpass123",
                                "new_password": "newpass456"})
        assert resp.status_code == 200

        # 旧 token 立即失效
        resp = client.get("/api/v1/auth/me",
                          headers={"Authorization": f"Bearer {self.token}"})
        assert resp.status_code == 401
        assert resp.get_json()["code"] == 30006

        # 旧密码登录失败
        resp = client.post("/api/v1/auth/login",
                           json={"username": "pwduser", "password": "oldpass123"})
        assert resp.status_code == 401

        # 新密码登录成功
        resp = client.post("/api/v1/auth/login",
                           json={"username": "pwduser", "password": "newpass456"})
        assert resp.status_code == 200

    def test_change_password_wrong_old(self, client):
        """旧密码错误 → 401"""
        resp = client.put("/api/v1/auth/password",
                          headers={"Authorization": f"Bearer {self.token}"},
                          json={"old_password": "wrong",
                                "new_password": "newpass456"})
        assert resp.status_code == 401
        assert resp.get_json()["code"] == 10003  # INVALID_CREDENTIAL

    def test_change_password_too_short(self, client):
        """新密码太短 → 400 / VALIDATION_ERROR"""
        resp = client.put("/api/v1/auth/password",
                          headers={"Authorization": f"Bearer {self.token}"},
                          json={"old_password": "oldpass123",
                                "new_password": "12"})
        assert resp.status_code == 400
        assert resp.get_json()["code"] == 90001


class TestRBAC:
    """RBAC 权限测试"""

    @pytest.fixture(autouse=True)
    def setup_users(self, client, app):
        """注册一个普通用户（user 角色）+ 直接 DB 建一个 admin"""
        # 普通用户注册
        client.post("/api/v1/auth/register", json={
            "username": "normal",
            "email": "normal@test.com",
            "password": "password123",
        })
        resp = client.post("/api/v1/auth/login",
                           json={"username": "normal", "password": "password123"})
        self.user_token = resp.get_json()["data"]["access_token"]

        # admin（直接走 service，避免走 register-then-promote 路径）
        with app.app_context():
            from app.services.auth_service import create_user
            from tests.conftest import DEFAULT_TENANT_ID
            create_user("rbacadmin", "rbacadmin@test.com", "adminpass", "admin",
                        tenant_id=DEFAULT_TENANT_ID)
        resp = client.post("/api/v1/auth/login",
                           json={"username": "rbacadmin", "password": "adminpass"})
        self.admin_token = resp.get_json()["data"]["access_token"]

    def test_normal_user_blocked_from_admin_endpoint(self, client):
        """普通 user 访问 /admin/users → 403 / PERMISSION_DENIED"""
        resp = client.get("/api/v1/admin/users",
                          headers={"Authorization": f"Bearer {self.user_token}"})
        assert resp.status_code == 403
        assert resp.get_json()["code"] == 30004

    def test_admin_can_access_admin_endpoint(self, client):
        """admin 可以访问 /admin/users → 200"""
        resp = client.get("/api/v1/admin/users",
                          headers={"Authorization": f"Bearer {self.admin_token}"})
        assert resp.status_code == 200

    def test_jwt_contains_permissions(self, client):
        """登录返回的 user 数据应包含 permissions 列表"""
        resp = client.post("/api/v1/auth/login",
                           json={"username": "rbacadmin", "password": "adminpass"})
        user_data = resp.get_json()["data"]["user"]
        assert "permissions" in user_data
        assert "user:read" in user_data["permissions"]
        assert "user:write" in user_data["permissions"]

    def test_user_role_has_limited_permissions(self, client):
        """user 角色有 task:read / task:create / model:read / model:write / model:delete"""
        resp = client.get("/api/v1/auth/me",
                          headers={"Authorization": f"Bearer {self.user_token}"})
        user_data = resp.get_json()["data"]
        assert set(user_data["permissions"]) == {
            "task:read", "task:create",
            "model:read", "model:write", "model:delete",
        }
