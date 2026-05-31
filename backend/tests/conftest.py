"""测试共用 fixtures"""

import pytest
import sys
from pathlib import Path

# 确保 backend 目录在 Python 路径上
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app, db
from config import TestConfig


def _seed_rbac():
    """测试 DB 用 db.create_all() 建表，不跑 migration，所以这里 seed RBAC 系统数据。

    与生产的 c3d4e5f6a7b8_add_rbac.py migration 保持一致。
    """
    from app.models.role import Role, Permission
    from app.permissions import (
        PERMISSIONS_REGISTRY, SYSTEM_ROLES, SYSTEM_ROLE_DESCRIPTIONS,
    )

    # 权限
    for code, desc in PERMISSIONS_REGISTRY.items():
        db.session.add(Permission(code=code, description=desc))

    # 角色 + 关联权限
    perm_by_code = {code: Permission(code=code, description=desc)
                    for code, desc in PERMISSIONS_REGISTRY.items()}
    # 重新查询（前一步 add 的对象）
    db.session.flush()
    perm_map = {p.code: p for p in Permission.query.all()}

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
        _seed_rbac()
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    """测试 HTTP 客户端"""
    return app.test_client()
