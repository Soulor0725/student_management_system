"""共享 pytest fixtures — 所有测试模块共用"""

import os
import sys
import tempfile
import shutil
import time
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as app_module
from app import app, init_db


@pytest.fixture(scope="session")
def flask_app():
    """整个测试会话共享的 Flask app 实例"""
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    return app


@pytest.fixture(scope="function")
def client(flask_app):
    """每个测试函数独立的临时数据库 + 测试客户端"""
    tmp_dir = tempfile.mkdtemp()
    test_db = os.path.join(tmp_dir, "test.db")

    original_db = app_module.DB_FILE
    app_module.DB_FILE = test_db

    try:
        with flask_app.test_client() as c:
            with flask_app.app_context():
                init_db()
            yield c
    finally:
        app_module.DB_FILE = original_db
        time.sleep(0.05)
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass


@pytest.fixture(scope="module")
def module_client(flask_app):
    """模块级共享客户端 — 性能敏感的测试用这个"""
    tmp_dir = tempfile.mkdtemp()
    test_db = os.path.join(tmp_dir, "test.db")

    original_db = app_module.DB_FILE
    app_module.DB_FILE = test_db

    try:
        with flask_app.test_client() as c:
            with flask_app.app_context():
                init_db()
            yield c
    finally:
        app_module.DB_FILE = original_db
        time.sleep(0.05)
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass


@pytest.fixture
def logged_in_client(client):
    """已登录状态的测试客户端"""
    client.post('/register', data={"username": "testuser", "password": "testpass123"})
    client.post('/login', data={"username": "testuser", "password": "testpass123"})
    return client


@pytest.fixture
def test_user():
    """标准测试用户数据"""
    return {
        "username": "test_user",
        "password": "test_password123"
    }


@pytest.fixture
def test_student():
    """标准测试学生数据"""
    return {
        "name": "张三",
        "age": "18",
        "class_name": "高三(1)班"
    }


@pytest.fixture
def bulk_students():
    """批量测试学生数据"""
    return [
        {"name": f"学生{i}", "age": str(15 + i % 10), "class_name": f"班级{i % 5 + 1}班"}
        for i in range(20)
    ]
