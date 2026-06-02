"""审计日志测试"""


class TestAuditLogs:
    def test_admin_action_writes_audit_log(self, client, app):
        with app.app_context():
            from app.services.auth_service import create_user
            from tests.conftest import DEFAULT_TENANT_ID

            create_user("audit-admin", "audit-admin@test.com", "adminpass", "admin",
                        tenant_id=DEFAULT_TENANT_ID)

        resp = client.post("/api/v1/auth/login",
                           json={"username": "audit-admin", "password": "adminpass"})
        token = resp.get_json()["data"]["access_token"]

        resp = client.post(
            "/api/v1/admin/roles",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Request-ID": "req-audit-role",
                "X-Forwarded-For": "203.0.113.9",
                "User-Agent": "pytest-agent",
            },
            json={
                "name": "auditor",
                "description": "审计测试角色",
                "permissions": ["task:read"],
            },
        )
        assert resp.status_code == 201
        role = resp.get_json()["data"]

        resp = client.get(
            "/api/v1/audit-logs",
            headers={"Authorization": f"Bearer {token}"},
            query_string={"action": "role.create", "resource_id": str(role["id"])},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["total"] == 1
        item = data["items"][0]
        assert item["tenant_id"] == 1
        assert item["actor_username"] == "audit-admin"
        assert item["action"] == "role.create"
        assert item["resource_type"] == "role"
        assert item["resource_name"] == "auditor"
        assert item["after_data"]["permissions"] == ["task:read"]
        assert item["request_id"] == "req-audit-role"
        assert item["ip_address"] == "203.0.113.9"

    def test_audit_logs_are_scoped_to_current_tenant(self, client, app):
        with app.app_context():
            from app import db
            from app.models.tenant import Tenant
            from app.services.auth_service import create_user

            db.session.add(Tenant(id=10, slug="tenant-a", name="租户A",
                                  is_active=True, is_system=False))
            db.session.add(Tenant(id=20, slug="tenant-b", name="租户B",
                                  is_active=True, is_system=False))
            db.session.commit()
            create_user("admina", "admina@test.com", "passa123", "admin", tenant_id=10)
            create_user("adminb", "adminb@test.com", "passb123", "admin", tenant_id=20)

        resp = client.post("/api/v1/auth/login",
                           json={"username": "admina", "password": "passa123"})
        token_a = resp.get_json()["data"]["access_token"]
        resp = client.post("/api/v1/auth/login",
                           json={"username": "adminb", "password": "passb123"})
        token_b = resp.get_json()["data"]["access_token"]

        resp = client.post(
            "/api/v1/admin/roles",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"name": "tenant-a-role", "permissions": ["task:read"]},
        )
        assert resp.status_code == 201
        resp = client.post(
            "/api/v1/admin/roles",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"name": "tenant-b-role", "permissions": ["task:create"]},
        )
        assert resp.status_code == 201

        resp = client.get("/api/v1/audit-logs",
                          headers={"Authorization": f"Bearer {token_a}"},
                          query_string={"action": "role.create"})
        assert resp.status_code == 200
        items = resp.get_json()["data"]["items"]
        assert {item["tenant_id"] for item in items} == {10}
        assert "tenant-a-role" in [item["resource_name"] for item in items]
        assert "tenant-b-role" not in [item["resource_name"] for item in items]

    def test_superuser_can_query_all_and_filter_tenant(self, client, app):
        with app.app_context():
            from app import db
            from app.models.tenant import Tenant
            from app.services.auth_service import create_user
            from tests.conftest import DEFAULT_TENANT_ID

            db.session.add(Tenant(id=10, slug="tenant-a", name="租户A",
                                  is_active=True, is_system=False))
            db.session.add(Tenant(id=20, slug="tenant-b", name="租户B",
                                  is_active=True, is_system=False))
            db.session.commit()
            superuser = create_user(
                "platform-audit",
                "platform-audit@test.com",
                "superpass",
                "admin",
                tenant_id=DEFAULT_TENANT_ID,
            )
            superuser.is_superuser = True
            create_user("admina", "audit-a@test.com", "passa123", "admin", tenant_id=10)
            create_user("adminb", "audit-b@test.com", "passb123", "admin", tenant_id=20)
            db.session.commit()

        resp = client.post("/api/v1/auth/login",
                           json={"username": "admina", "password": "passa123"})
        token_a = resp.get_json()["data"]["access_token"]
        resp = client.post("/api/v1/auth/login",
                           json={"username": "adminb", "password": "passb123"})
        token_b = resp.get_json()["data"]["access_token"]
        resp = client.post("/api/v1/auth/login",
                           json={"username": "platform-audit", "password": "superpass"})
        super_token = resp.get_json()["data"]["access_token"]

        client.post(
            "/api/v1/admin/roles",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"name": "audit-a-role", "permissions": ["task:read"]},
        )
        client.post(
            "/api/v1/admin/roles",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"name": "audit-b-role", "permissions": ["task:create"]},
        )

        resp = client.get("/api/v1/audit-logs",
                          headers={"Authorization": f"Bearer {super_token}"},
                          query_string={"action": "role.create"})
        assert resp.status_code == 200
        names = [item["resource_name"] for item in resp.get_json()["data"]["items"]]
        assert "audit-a-role" in names
        assert "audit-b-role" in names

        resp = client.get("/api/v1/audit-logs",
                          headers={"Authorization": f"Bearer {super_token}"},
                          query_string={"action": "role.create", "tenant_id": 20})
        assert resp.status_code == 200
        items = resp.get_json()["data"]["items"]
        assert {item["tenant_id"] for item in items} == {20}
        assert "audit-b-role" in [item["resource_name"] for item in items]
