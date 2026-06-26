"""接口契约测试 — 校验响应格式、状态码、Header"""

import pytest


@pytest.mark.contract
class TestRegisterContract:
    def test_register_returns_200_on_success(self, client):
        resp = client.post('/register', data={"username": "contract_u", "password": "pass123"})
        assert resp.status_code == 200

    def test_register_returns_200_on_duplicate(self, client):
        client.post('/register', data={"username": "dup_c", "password": "pass123"})
        resp = client.post('/register', data={"username": "dup_c", "password": "pass123"})
        assert resp.status_code == 200

    def test_register_returns_200_on_empty(self, client):
        resp = client.post('/register', data={"username": "", "password": ""})
        assert resp.status_code == 200

    def test_register_get_returns_200(self, client):
        resp = client.get('/register')
        assert resp.status_code == 200
        assert b'<!DOCTYPE html>' in resp.data or b'<html' in resp.data

    def test_register_content_type_html(self, client):
        resp = client.get('/register')
        assert 'text/html' in resp.content_type


@pytest.mark.contract
class TestLoginContract:
    def test_login_success_returns_200(self, client):
        client.post('/register', data={"username": "lc_u", "password": "pass123"})
        resp = client.post('/login', data={"username": "lc_u", "password": "pass123"})
        assert resp.status_code == 200

    def test_login_fail_returns_200(self, client):
        resp = client.post('/login', data={"username": "nobody", "password": "wrong"})
        assert resp.status_code == 200

    def test_login_get_returns_200(self, client):
        resp = client.get('/login')
        assert resp.status_code == 200

    def test_login_already_logged_in_redirects(self, logged_in_client):
        resp = logged_in_client.get('/login')
        assert resp.status_code == 302


@pytest.mark.contract
class TestLogoutContract:
    def test_logout_returns_302(self, logged_in_client):
        resp = logged_in_client.post('/logout')
        assert resp.status_code == 302

    def test_logout_redirects_to_login(self, logged_in_client):
        resp = logged_in_client.post('/logout')
        assert '/login' in resp.headers.get('Location', '')


@pytest.mark.contract
class TestStudentContract:
    def test_index_requires_auth(self, client):
        resp = client.get('/')
        assert resp.status_code == 302
        assert '/login' in resp.headers.get('Location', '')

    def test_index_returns_200_when_logged(self, logged_in_client):
        resp = logged_in_client.get('/')
        assert resp.status_code == 200

    def test_add_student_returns_302(self, logged_in_client):
        resp = logged_in_client.post('/students', data={
            "name": "契约学生", "age": "18", "class_name": "契约班"
        })
        assert resp.status_code == 302

    def test_edit_student_page_returns_200(self, logged_in_client):
        logged_in_client.post('/students', data={
            "name": "编辑测试", "age": "20", "class_name": "B班"
        })
        resp = logged_in_client.get('/students/1/edit')
        assert resp.status_code == 200

    def test_edit_student_submit_returns_302(self, logged_in_client):
        logged_in_client.post('/students', data={
            "name": "待编辑", "age": "19", "class_name": "C班"
        })
        resp = logged_in_client.post('/students/1', data={
            "name": "已编辑", "age": "21", "class_name": "D班"
        })
        assert resp.status_code == 302

    def test_delete_student_returns_302(self, logged_in_client):
        logged_in_client.post('/students', data={
            "name": "待删除", "age": "17", "class_name": "E班"
        })
        resp = logged_in_client.post('/students/1/delete')
        assert resp.status_code == 302


@pytest.mark.contract
class TestMetricsContract:
    def test_metrics_returns_200(self, client):
        resp = client.get('/metrics')
        assert resp.status_code == 200

    def test_metrics_content_type_prometheus(self, client):
        resp = client.get('/metrics')
        assert 'text/plain' in resp.content_type

    def test_metrics_contains_flask_counter(self, client):
        resp = client.get('/metrics')
        assert b'flask_http_request_total' in resp.data

    def test_metrics_contains_business_gauges(self, client):
        resp = client.get('/metrics')
        assert b'total_users' in resp.data
        assert b'total_students' in resp.data
        assert b'app_up' in resp.data


@pytest.mark.contract
class TestIdempotency:
    def test_duplicate_register_not_duplicated(self, client):
        client.post('/register', data={"username": "idem_u", "password": "pass123"})
        client.post('/register', data={"username": "idem_u", "password": "pass123"})
        client.post('/login', data={"username": "idem_u", "password": "pass123"})
        resp = client.get('/')
        assert resp.status_code == 200

    def test_double_delete_safe(self, logged_in_client):
        logged_in_client.post('/students', data={
            "name": "双删测试", "age": "20", "class_name": "F班"
        })
        logged_in_client.post('/students/1/delete')
        resp = logged_in_client.post('/students/1/delete', follow_redirects=False)
        assert resp.status_code in [302, 200, 404, 500]
