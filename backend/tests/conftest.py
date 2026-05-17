"""测试共用 fixtures"""

import pytest
import sys
from pathlib import Path

# 确保 backend 目录在 Python 路径上
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from config import TestConfig


@pytest.fixture
def app():
    """创建测试用的 Flask 应用"""
    app = create_app(config_obj=TestConfig)
    return app


@pytest.fixture
def client(app):
    """测试 HTTP 客户端"""
    return app.test_client()