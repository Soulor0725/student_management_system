"""pytest 安全测试配置"""
import pytest
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

@pytest.fixture(scope="module")
def client():
    """创建测试客户端"""
    app.config['TESTING'] = True
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_db = f.name
    
    with app.test_client() as client:
        yield client
    
    os.unlink(temp_db)

@pytest.fixture(scope="module")
def test_user():
    """测试用户数据"""
    return {
        "username": "test_security_user",
        "password": "test_password123"
    }