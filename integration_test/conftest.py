"""pytest 集成测试配置"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from data.models import User, Student

@pytest.fixture(scope="module")
def client():
    """创建测试客户端"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()

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