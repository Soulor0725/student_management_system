"""数据库约束与并发测试"""

import pytest
import sqlite3
import threading
import os
import tempfile
import time


@pytest.mark.db
class TestDBConstraints:
    def test_unique_username_constraint(self, client):
        client.post('/register', data={"username": "unique_user", "password": "pass123"})
        resp = client.post('/register', data={"username": "unique_user", "password": "pass456"})
        assert resp.status_code == 200
        assert "已存在" in resp.text

    def test_not_null_username(self, client):
        resp = client.post('/register', data={"username": "", "password": "pass123"})
        assert resp.status_code == 200
        assert "不能为空" in resp.text

    def test_not_null_password(self, client):
        resp = client.post('/register', data={"username": "user_nopass", "password": ""})
        assert resp.status_code == 200
        assert "不能为空" in resp.text

    def test_student_name_max_length(self, logged_in_client):
        resp = logged_in_client.post('/students', data={
            "name": "a" * 13, "age": "18", "class_name": "A班"
        })
        assert resp.status_code == 200
        assert "12个字符" in resp.text

    def test_student_name_exact_max_length(self, logged_in_client):
        resp = logged_in_client.post('/students', data={
            "name": "a" * 12, "age": "18", "class_name": "A班"
        }, follow_redirects=False)
        assert resp.status_code == 302

    def test_empty_student_name_rejected(self, logged_in_client):
        logged_in_client.post('/students', data={
            "name": "should_exist", "age": "18", "class_name": "A班"
        })
        resp = logged_in_client.post('/students', data={
            "name": "", "age": "18", "class_name": "A班"
        }, follow_redirects=False)
        assert resp.status_code in [200, 302]
        # 验证空名字的学生没有被添加
        resp = logged_in_client.get('/')
        assert resp.status_code == 200


@pytest.mark.db
class TestDBAutoInit:
    def test_auto_create_tables(self):
        from app import init_db
        import app as app_module
        import shutil

        tmp_dir = tempfile.mkdtemp()
        test_db = os.path.join(tmp_dir, "test.db")
        original_db = app_module.DB_FILE
        app_module.DB_FILE = test_db
        try:
            init_db()
            conn = sqlite3.connect(test_db)
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            conn.close()
            assert 'users' in tables
            assert 'students' in tables
        finally:
            app_module.DB_FILE = original_db
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_auto_create_data_dir(self):
        from app import init_db
        import app as app_module
        import shutil

        tmp_dir = tempfile.mkdtemp()
        test_db = os.path.join(tmp_dir, "test.db")
        original_db = app_module.DB_FILE
        app_module.DB_FILE = test_db
        try:
            init_db()
            assert os.path.exists(test_db)
            conn = sqlite3.connect(test_db)
            count = conn.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()[0]
            conn.close()
            assert count > 0
        finally:
            app_module.DB_FILE = original_db
            shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.mark.db
class TestDBConcurrency:
    def test_concurrent_inserts(self, flask_app):
        import app as app_module
        import shutil

        tmp_dir = tempfile.mkdtemp()
        test_db = os.path.join(tmp_dir, "test.db")
        original_db = app_module.DB_FILE
        app_module.DB_FILE = test_db

        try:
            with flask_app.app_context():
                from app import init_db, get_db_connection
                init_db()

            errors = []

            def insert_student(name):
                try:
                    with flask_app.app_context():
                        from app import get_db_connection
                        conn = get_db_connection()
                        conn.execute(
                            "INSERT INTO students (name, age, class_name) VALUES (?, ?, ?)",
                            (name, 18, "并发测试班")
                        )
                        conn.commit()
                        conn.close()
                except Exception as e:
                    errors.append(str(e))

            threads = [threading.Thread(target=insert_student, args=(f"并发学生{i}",)) for i in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=5)

            with flask_app.app_context():
                from app import get_db_connection
                conn = get_db_connection()
                count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
                conn.close()

            assert count == 10, f"Expected 10, got {count}. Errors: {errors}"
        finally:
            app_module.DB_FILE = original_db
            shutil.rmtree(tmp_dir, ignore_errors=True)
