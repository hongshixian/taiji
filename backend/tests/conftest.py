"""测试共用 fixtures"""

import pytest
import sys
from pathlib import Path

# 确保 backend 目录在 Python 路径上
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app, db
from config import TestConfig


# 测试中使用的固定租户 ID（与 _seed_tenants 中保持一致）
DEFAULT_TENANT_ID = 1
GUEST_TENANT_ID = 2


def _seed_tenants():
    """seed 系统租户（default + guest），与 d4e5f6a7b8c9 migration 同步"""
    from app.models.tenant import Tenant
    db.session.add(Tenant(id=DEFAULT_TENANT_ID, slug="default", name="默认组织",
                          is_active=True, is_system=True))
    db.session.add(Tenant(id=GUEST_TENANT_ID, slug="guest", name="访客租户",
                          is_active=True, is_system=True))
    db.session.commit()


def _seed_rbac():
    """seed RBAC 系统数据，与 c3d4e5f6a7b8 migration 同步"""
    from app.models.role import Role, Permission
    from app.permissions import (
        PERMISSIONS_REGISTRY, SYSTEM_ROLES, SYSTEM_ROLE_DESCRIPTIONS,
    )

    # 权限
    for code, desc in PERMISSIONS_REGISTRY.items():
        db.session.add(Permission(code=code, description=desc))
    db.session.flush()
    perm_map = {p.code: p for p in Permission.query.all()}

    # 角色 + 关联权限
    for name, codes in SYSTEM_ROLES.items():
        role = Role(name=name,
                    description=SYSTEM_ROLE_DESCRIPTIONS.get(name, ""),
                    is_system=True)
        for code in codes:
            role.permissions.append(perm_map[code])
        db.session.add(role)

    db.session.commit()


@pytest.fixture
def app():
    """创建测试用的 Flask 应用（内存 SQLite）"""
    app = create_app(config_obj=TestConfig)
    with app.app_context():
        db.create_all()
        _seed_tenants()
        _seed_rbac()
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    """测试 HTTP 客户端"""
    return app.test_client()
