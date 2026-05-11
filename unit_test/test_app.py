import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app as app_module
from app import app, init_db, hash_password, is_logged_in


@pytest.fixture
def client():
    import shutil
    import time
    
    tmp_dir = tempfile.mkdtemp()
    test_db = Path(tmp_dir) / "test.db"

    original_db_file = app_module.DB_FILE
    app_module.DB_FILE = test_db

    try:
        with app.test_client() as client:
            with app.app_context():
                init_db()
            yield client
    finally:
        app_module.DB_FILE = original_db_file
        # 等待片刻确保连接关闭
        time.sleep(0.1)
        # 尝试删除临时目录，忽略错误
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass


@pytest.fixture
def logged_in_client(client):
    with client.session_transaction() as sess:
        sess["user"] = {"id": 1, "username": "testuser"}
    return client


class TestHashPassword:
    def test_hash_password_returns_hex_string(self):
        result = hash_password("test123")
        assert isinstance(result, str)
        assert len(result) == 64

    def test_hash_password_consistent(self):
        pwd = "mysecret"
        h1 = hash_password(pwd)
        h2 = hash_password(pwd)
        assert h1 == h2

    def test_hash_password_different_passwords(self):
        h1 = hash_password("pass1")
        h2 = hash_password("pass2")
        assert h1 != h2


class TestRegister:
    def test_register_page_loads(self, client):
        response = client.get("/register")
        assert response.status_code == 200

    def test_register_empty_fields(self, client):
        response = client.post("/register", data={"username": "", "password": ""})
        assert "用户名和密码不能为空" in response.text

    def test_register_success(self, client):
        response = client.post("/register", data={"username": "newuser", "password": "pass123"})
        assert "注册成功" in response.text

    def test_register_duplicate_user(self, client):
        client.post("/register", data={"username": "dupuser", "password": "pass123"})
        response = client.post("/register", data={"username": "dupuser", "password": "pass123"})
        assert "用户名已存在" in response.text


class TestLogin:
    def test_login_page_loads(self, client):
        response = client.get("/login")
        assert response.status_code == 200

    def test_login_wrong_password(self, client):
        client.post("/register", data={"username": "user1", "password": "correct"})
        response = client.post("/login", data={"username": "user1", "password": "wrong"})
        assert "用户名或密码错误" in response.text

    def test_login_success(self, client):
        client.post("/register", data={"username": "user2", "password": "correct"})
        response = client.post("/login", data={"username": "user2", "password": "correct"}, follow_redirects=True)
        assert response.status_code == 200
        assert "登录成功" in response.text


class TestStudentCrud:
    def test_index_redirects_unlogged(self, client):
        response = client.get("/")
        assert response.status_code == 302

    def test_add_student_requires_login(self, client):
        response = client.post("/students", data={"name": "Test", "age": 20, "class_name": "Class1"})
        assert response.status_code == 302

    def test_add_student_success(self, logged_in_client):
        response = logged_in_client.post("/students", data={"name": "TestStudent", "age": 20, "class_name": "Class1"})
        assert response.status_code == 302

    def test_delete_student_requires_login(self, client):
        response = client.post("/students/1/delete")
        assert response.status_code == 302
