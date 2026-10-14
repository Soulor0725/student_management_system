"""单元测试 — 密码哈希、注册、登录、学生 CRUD"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import LOGIN_RATE_LIMIT, hash_password, verify_password


@pytest.mark.unit
class TestHashPassword:
    def test_hash_password_is_salted(self):
        h1 = hash_password("test123")
        h2 = hash_password("test123")
        assert isinstance(h1, str) and h1
        assert h1 != h2

    def test_verify_password_roundtrip(self):
        stored = hash_password("mysecret")
        assert verify_password(stored, "mysecret")
        assert not verify_password(stored, "wrongpass")

    def test_verify_legacy_sha256_hash(self):
        import hashlib

        legacy = hashlib.sha256(b"legacy123").hexdigest()
        assert verify_password(legacy, "legacy123")
        assert not verify_password(legacy, "nope")

    def test_verify_password_empty_inputs(self):
        assert not verify_password("", "x")
        assert not verify_password(hash_password("x"), "")

    def test_hash_password_different_passwords(self):
        h1 = hash_password("pass1")
        h2 = hash_password("pass2")
        assert h1 != h2


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
@pytest.mark.skipif(not LOGIN_RATE_LIMIT, reason="LOGIN_RATE_LIMIT=0")
class TestLoginRateLimit:
    def test_locked_after_repeated_failures(self, client):
        client.post("/register", data={"username": "brute1", "password": "pass123"})

        for _ in range(5):
            response = client.post("/login", data={"username": "brute1", "password": "wrong"})
            assert response.status_code == 200
            assert "用户名或密码错误" in response.text

        response = client.post("/login", data={"username": "brute1", "password": "wrong"})
        assert response.status_code == 429
        assert "尝试过于频繁" in response.text
        assert response.headers.get("Retry-After")

        # 锁定窗口内即便密码正确也拒绝
        response = client.post("/login", data={"username": "brute1", "password": "pass123"})
        assert response.status_code == 429

    def test_successful_login_clears_failures(self, client):
        client.post("/register", data={"username": "brute2", "password": "pass123"})
        for _ in range(4):
            client.post("/login", data={"username": "brute2", "password": "wrong"})
        assert client.post("/login", data={"username": "brute2", "password": "pass123"}).status_code == 200

        # 成功登录清空该用户计数，再错 4 次也不会被锁
        for _ in range(4):
            response = client.post("/login", data={"username": "brute2", "password": "wrong"})
            assert response.status_code == 200

    def test_empty_credentials_are_not_counted(self, client):
        for _ in range(10):
            response = client.post("/login", data={"username": "brute3", "password": ""})
            assert response.status_code == 200
            assert "不能为空" in response.text


@pytest.mark.unit
class TestSearchAndPagination:
    def test_like_wildcards_are_literal(self, logged_in_client):
        logged_in_client.post("/students", data={"name": "100%", "age": "18", "class_name": "A班"})
        logged_in_client.post("/students", data={"name": "张三", "age": "19", "class_name": "B班"})

        response = logged_in_client.get("/", query_string={"q": "%"})
        assert "100%" in response.text
        assert "张三" not in response.text

        response = logged_in_client.get("/", query_string={"q": "_"})
        assert "没有找到匹配" in response.text

    def test_empty_state_without_students(self, logged_in_client):
        response = logged_in_client.get("/")
        assert response.status_code == 200
        assert "还没有学生记录" in response.text

    def test_page_window_collapses_long_ranges(self):
        from app import _page_window

        assert _page_window(1, 1) == [1]
        assert _page_window(2, 5) == [1, 2, 3, 4, 5]
        assert _page_window(7, 20) == [1, "…", 5, 6, 7, 8, 9, "…", 20]
        assert _page_window(20, 20) == [1, "…", 18, 19, 20]
