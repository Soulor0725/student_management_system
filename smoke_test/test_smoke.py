"""冒烟测试 — 核心路径快速验证，CI 每次必跑"""

import pytest


@pytest.mark.smoke
class TestSmokeRegister:
    def test_register_page_loads(self, client):
        resp = client.get('/register')
        assert resp.status_code == 200

    def test_register_success(self, client):
        resp = client.post('/register', data={"username": "smoke_user", "password": "smoke123"})
        assert resp.status_code == 200
        assert "注册成功" in resp.text


@pytest.mark.smoke
class TestSmokeLogin:
    def test_login_success(self, client):
        client.post('/register', data={"username": "smoke_login", "password": "smoke123"})
        resp = client.post('/login', data={"username": "smoke_login", "password": "smoke123"})
        assert resp.status_code == 200
        assert "登录成功" in resp.text

    def test_login_wrong_password(self, client):
        client.post('/register', data={"username": "smoke_wrong", "password": "smoke123"})
        resp = client.post('/login', data={"username": "smoke_wrong", "password": "wrong"})
        assert resp.status_code == 200
        assert "用户名或密码错误" in resp.text


@pytest.mark.smoke
class TestSmokeStudentCRUD:
    def test_add_student(self, logged_in_client):
        resp = logged_in_client.post('/students', data={
            "name": "烟测学生", "age": "18", "class_name": "烟测班"
        }, follow_redirects=False)
        assert resp.status_code == 302

    def test_view_student_list(self, logged_in_client):
        logged_in_client.post('/students', data={
            "name": "烟测列表", "age": "20", "class_name": "A班"
        })
        resp = logged_in_client.get('/')
        assert resp.status_code == 200
        assert "烟测列表" in resp.text

    def test_unauthenticated_redirect(self, client):
        resp = client.get('/')
        assert resp.status_code == 302


@pytest.mark.smoke
class TestSmokeMetrics:
    def test_metrics_accessible(self, client):
        resp = client.get('/metrics')
        assert resp.status_code == 200
        assert b'flask_http_request_total' in resp.data
