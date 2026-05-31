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