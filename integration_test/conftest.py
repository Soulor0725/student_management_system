"""pytest 集成测试配置"""
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
    
    # 创建临时数据库
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_db = f.name
    
    original_db = app.config.get('DATABASE', None)
    
    with app.test_client() as client:
        yield client
    
    # 清理临时文件
    os.unlink(temp_db)

@pytest.fixture(scope="module")
def test_user():
    """测试用户数据"""
    return {
        "username": "test_integration_user",
        "password": "test_password123"
    }

@pytest.fixture(scope="module")
def test_student():
    """测试学生数据"""
    return {
        "name": "张三",
        "age": "18",
        "class_name": "高三(1)班"
    }