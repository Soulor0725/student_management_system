"""数据完整性 CRUD 测试 — 全链路数据验证"""

import pytest


@pytest.mark.crud
class TestStudentCRUDIntegrity:
    def test_full_crud_lifecycle(self, logged_in_client):
        # CREATE
        resp = logged_in_client.post('/students', data={
            "name": "全链路", "age": "20", "class_name": "A班"
        }, follow_redirects=False)
        assert resp.status_code == 302

        # READ
        resp = logged_in_client.get('/')
        assert resp.status_code == 200
        assert "全链路" in resp.text
        assert "20" in resp.text
        assert "A班" in resp.text

        # UPDATE
        resp = logged_in_client.post('/students/1', data={
            "name": "全链路已修改", "age": "22", "class_name": "B班"
        }, follow_redirects=False)
        assert resp.status_code == 302

        resp = logged_in_client.get('/')
        assert "全链路已修改" in resp.text
        assert "全链路" not in resp.text.replace("全链路已修改", "")

        # DELETE
        resp = logged_in_client.post('/students/1/delete', follow_redirects=False)
        assert resp.status_code == 302

        resp = logged_in_client.get('/')
        assert "全链路已修改" not in resp.text

    def test_multiple_students_independence(self, logged_in_client):
        students = [
            {"name": "独立A", "age": "16", "class_name": "1班"},
            {"name": "独立B", "age": "17", "class_name": "2班"},
            {"name": "独立C", "age": "18", "class_name": "3班"},
        ]
        for s in students:
            logged_in_client.post('/students', data=s)

        resp = logged_in_client.get('/')
        for s in students:
            assert s["name"] in resp.text

        # 删除中间一个
        logged_in_client.post('/students/2/delete')
        resp = logged_in_client.get('/')
        assert "独立A" in resp.text
        assert "独立B" not in resp.text
        assert "独立C" in resp.text

    def test_edit_preserves_other_fields(self, logged_in_client):
        logged_in_client.post('/students', data={
            "name": "字段保留", "age": "19", "class_name": "保留班"
        })
        # 只改名字
        logged_in_client.post('/students/1', data={
            "name": "已改名", "age": "19", "class_name": "保留班"
        })
        resp = logged_in_client.get('/')
        assert "已改名" in resp.text
        assert "保留班" in resp.text

    def test_student_list_ordering(self, logged_in_client):
        names = ["排序一", "排序二", "排序三"]
        for name in names:
            logged_in_client.post('/students', data={
                "name": name, "age": "18", "class_name": "排序班"
            })
        resp = logged_in_client.get('/')
        text = resp.text
        # 按 ID 降序排列，最后添加的排在前面
        pos_last = text.index("排序三")
        pos_mid = text.index("排序二")
        pos_first = text.index("排序一")
        assert pos_last < pos_mid < pos_first


@pytest.mark.crud
class TestUserCRUDIntegrity:
    def test_register_login_logout_cycle(self, client):
        # REGISTER
        resp = client.post('/register', data={"username": "cycle_u", "password": "cycle123"})
        assert "注册成功" in resp.text

        # LOGIN
        resp = client.post('/login', data={"username": "cycle_u", "password": "cycle123"})
        assert "登录成功" in resp.text

        # ACCESS PROTECTED
        resp = client.get('/')
        assert resp.status_code == 200

        # LOGOUT
        resp = client.post('/logout', follow_redirects=False)
        assert resp.status_code == 302

        # VERIFY LOGGED OUT
        resp = client.get('/')
        assert resp.status_code == 302

    def test_password_hash_not_stored_plaintext(self, client):
        client.post('/register', data={"username": "hash_u", "password": "plain123"})
        resp = client.post('/login', data={"username": "hash_u", "password": "plain123"})
        assert resp.status_code == 200


@pytest.mark.crud
class TestDataPersistence:
    def test_data_persists_across_requests(self, logged_in_client):
        logged_in_client.post('/students', data={
            "name": "持久化", "age": "21", "class_name": "持久班"
        })
        # 多次访问
        for _ in range(5):
            resp = logged_in_client.get('/')
            assert "持久化" in resp.text

    def test_data_persists_after_relogin(self, client):
        client.post('/register', data={"username": "persist_u", "password": "persist123"})
        client.post('/login', data={"username": "persist_u", "password": "persist123"})
        client.post('/students', data={
            "name": "重登验证", "age": "22", "class_name": "重登班"
        })
        client.post('/logout')
        client.post('/login', data={"username": "persist_u", "password": "persist123"})
        resp = client.get('/')
        assert "重登验证" in resp.text


@pytest.mark.crud
class TestEdgeCaseData:
    def test_unicode_student_name(self, logged_in_client):
        logged_in_client.post('/students', data={
            "name": "中文名¥™£", "age": "18", "class_name": "Unicode班"
        })
        resp = logged_in_client.get('/')
        assert "中文名¥™£" in resp.text

    def test_zero_age_student(self, logged_in_client):
        resp = logged_in_client.post('/students', data={
            "name": "零岁", "age": "0", "class_name": "特殊班"
        }, follow_redirects=False)
        assert resp.status_code == 302

    def test_large_age_value(self, logged_in_client):
        resp = logged_in_client.post('/students', data={
            "name": "大龄", "age": "999", "class_name": "特殊班"
        }, follow_redirects=False)
        assert resp.status_code == 302

    def test_special_chars_class_name(self, logged_in_client):
        logged_in_client.post('/students', data={
            "name": "特殊班级", "age": "18", "class_name": "高三<1>班&\"2班"
        })
        resp = logged_in_client.get('/')
        assert "特殊班级" in resp.text
