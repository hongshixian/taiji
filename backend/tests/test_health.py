"""健康检查接口测试"""


def test_health_check(client):
    """验证 /api/health 返回正常"""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"


def test_404_returns_error_response(client):
    """验证不存在的路由返回统一错误格式"""
    response = client.get("/api/nonexistent")
    assert response.status_code == 404
    data = response.get_json()
    assert data["code"] == 404
    assert "message" in data