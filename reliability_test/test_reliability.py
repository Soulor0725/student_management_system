"""可靠性与配置测试"""

import pytest
import os
import time
import app as app_module


@pytest.mark.reliability
class TestStability:
    def test_repeated_requests_stability(self, logged_in_client):
        for i in range(50):
            resp = logged_in_client.get('/')
            assert resp.status_code == 200

    def test_rapid_login_logout_cycle(self, client):
        for i in range(10):
            client.post('/register', data={"username": f"rapid_{i}", "password": "rapid123"})
            client.post('/login', data={"username": f"rapid_{i}", "password": "rapid123"})
            client.post('/logout')

    def test_concurrent_read_requests(self, flask_app):
        import threading
        results = []

        def make_request():
            with flask_app.test_client() as c:
                c.post('/register', data={"username": "conc_read", "password": "conc123"})
                c.post('/login', data={"username": "conc_read", "password": "conc123"})
                resp = c.get('/')
                results.append(resp.status_code)

        threads = [threading.Thread(target=make_request) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        assert all(r == 200 for r in results), f"Status codes: {results}"


@pytest.mark.reliability
class TestErrorRecovery:
    def test_recovers_after_invalid_input(self, logged_in_client):
        # 发送无效数据
        logged_in_client.post('/students', data={"name": "", "age": "abc", "class_name": ""})
        # 系统应该恢复正常
        resp = logged_in_client.post('/students', data={
            "name": "恢复测试", "age": "18", "class_name": "恢复班"
        }, follow_redirects=False)
        assert resp.status_code == 302

    def test_404_does_not_crash(self, client):
        resp = client.get('/nonexistent_page_xyz')
        assert resp.status_code == 404

    def test_invalid_method_returns_error(self, client):
        resp = client.put('/')
        assert resp.status_code in [405, 302]

    def test_invalid_student_id(self, logged_in_client):
        resp = logged_in_client.get('/students/99999/edit')
        assert resp.status_code in [200, 404, 500]


@pytest.mark.config
class TestConfiguration:
    def test_app_secret_key_exists(self, flask_app):
        assert flask_app.secret_key is not None
        assert len(flask_app.secret_key) > 0

    def test_testing_config(self, flask_app):
        assert flask_app.config['TESTING'] is True

    def test_database_path_configured(self):
        assert app_module.DB_FILE is not None
        assert str(app_module.DB_FILE).endswith('.db')

    def test_data_directory_creation(self):
        assert app_module.DATA_DIR is not None

    def test_app_starts_correctly(self):
        assert app_module.app is not None
        assert app_module.app.name == 'app'
