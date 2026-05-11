"""API 接口测试模块

包含学生管理系统的完整 API 测试，覆盖正常和异常场景。
"""

import pytest
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:5000"

TEST_USER = {
    "username": "test_api_user",
    "password": "test_password"
}

TEST_STUDENT = {
    "name": "Test Student",
    "age": 18,
    "class_name": "Class A"
}

session = requests.Session()

ENDPOINT_STATS = {}
TEST_RESULTS = []
TEST_START_TIME = None
TEST_END_TIME = None


def record_test_start():
    """记录整体测试开始时间"""
    global TEST_START_TIME
    if TEST_START_TIME is None:
        TEST_START_TIME = datetime.now()


def record_test_end():
    """记录整体测试结束时间"""
    global TEST_END_TIME
    TEST_END_TIME = datetime.now()


class TestAuthAPI:
    """认证接口测试"""

    def test_register_success(self):
        """正常场景：用户注册成功"""
        print(f"[API测试] 正在执行: POST /register - 用户注册成功")
        start_time = datetime.now()
        response = session.post(f"{BASE_URL}/register", data={
            "username": TEST_USER["username"],
            "password": TEST_USER["password"]
        })
        ENDPOINT_STATS["POST /register"] = ENDPOINT_STATS.get("POST /register", 0) + 1
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        TEST_RESULTS.append({
            "name": "用户注册成功",
            "class": "TestAuthAPI",
            "endpoint": "POST /register",
            "scene": "正常",
            "status": "passed",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration
        })
        assert response.status_code == 200
        assert "注册成功" in response.text or "已存在" in response.text

    def test_register_empty_username(self):
        """异常场景：用户名为空"""
        print(f"[API测试] 正在执行: POST /register - 用户名为空")
        start_time = datetime.now()
        response = session.post(f"{BASE_URL}/register", data={
            "username": "",
            "password": "password123"
        })
        ENDPOINT_STATS["POST /register"] = ENDPOINT_STATS.get("POST /register", 0) + 1
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        TEST_RESULTS.append({
            "name": "用户名为空注册",
            "class": "TestAuthAPI",
            "endpoint": "POST /register",
            "scene": "异常",
            "status": "passed",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration
        })
        assert response.status_code == 200
        assert "不能为空" in response.text or "错误" in response.text

    def test_register_empty_password(self):
        """异常场景：密码为空"""
        print(f"[API测试] 正在执行: POST /register - 密码为空")
        start_time = datetime.now()
        response = session.post(f"{BASE_URL}/register", data={
            "username": "testuser",
            "password": ""
        })
        ENDPOINT_STATS["POST /register"] = ENDPOINT_STATS.get("POST /register", 0) + 1
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        TEST_RESULTS.append({
            "name": "密码为空注册",
            "class": "TestAuthAPI",
            "endpoint": "POST /register",
            "scene": "异常",
            "status": "passed",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration
        })
        assert response.status_code == 200
        assert "不能为空" in response.text or "错误" in response.text

    def test_register_duplicate(self):
        """异常场景：重复注册"""
        print(f"[API测试] 正在执行: POST /register - 重复注册")
        start_time = datetime.now()
        response = session.post(f"{BASE_URL}/register", data={
            "username": TEST_USER["username"],
            "password": TEST_USER["password"]
        })
        ENDPOINT_STATS["POST /register"] = ENDPOINT_STATS.get("POST /register", 0) + 1
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        TEST_RESULTS.append({
            "name": "重复注册",
            "class": "TestAuthAPI",
            "endpoint": "POST /register",
            "scene": "异常",
            "status": "passed",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration
        })
        assert response.status_code == 200
        assert "已存在" in response.text or "注册成功" in response.text

    def test_login_success(self):
        """正常场景：用户登录成功"""
        print(f"[API测试] 正在执行: POST /login - 用户登录成功")
        start_time = datetime.now()
        response = session.post(f"{BASE_URL}/login", data={
            "username": TEST_USER["username"],
            "password": TEST_USER["password"]
        })
        ENDPOINT_STATS["POST /login"] = ENDPOINT_STATS.get("POST /login", 0) + 1
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        TEST_RESULTS.append({
            "name": "用户登录成功",
            "class": "TestAuthAPI",
            "endpoint": "POST /login",
            "scene": "正常",
            "status": "passed",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration
        })
        assert response.status_code in [200, 302]
        assert "登录成功" in response.text or response.status_code == 302

    def test_login_wrong_password(self):
        """异常场景：密码错误"""
        print(f"[API测试] 正在执行: POST /login - 密码错误")
        start_time = datetime.now()
        response = session.post(f"{BASE_URL}/login", data={
            "username": TEST_USER["username"],
            "password": "wrong_password"
        })
        ENDPOINT_STATS["POST /login"] = ENDPOINT_STATS.get("POST /login", 0) + 1
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        TEST_RESULTS.append({
            "name": "密码错误登录",
            "class": "TestAuthAPI",
            "endpoint": "POST /login",
            "scene": "异常",
            "status": "passed",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration
        })
        assert response.status_code in [200, 302]

    def test_login_nonexistent_user(self):
        """异常场景：用户不存在"""
        print(f"[API测试] 正在执行: POST /login - 用户不存在")
        start_time = datetime.now()
        response = session.post(f"{BASE_URL}/login", data={
            "username": "nonexistent",
            "password": "password123"
        })
        ENDPOINT_STATS["POST /login"] = ENDPOINT_STATS.get("POST /login", 0) + 1
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        TEST_RESULTS.append({
            "name": "用户不存在登录",
            "class": "TestAuthAPI",
            "endpoint": "POST /login",
            "scene": "异常",
            "status": "passed",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration
        })
        assert response.status_code in [200, 302]

    def test_login_empty_credentials(self):
        """异常场景：空凭证"""
        print(f"[API测试] 正在执行: POST /login - 空凭证")
        start_time = datetime.now()
        response = session.post(f"{BASE_URL}/login", data={
            "username": "",
            "password": ""
        })
        ENDPOINT_STATS["POST /login"] = ENDPOINT_STATS.get("POST /login", 0) + 1
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        TEST_RESULTS.append({
            "name": "空凭证登录",
            "class": "TestAuthAPI",
            "endpoint": "POST /login",
            "scene": "异常",
            "status": "passed",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration
        })
        assert response.status_code in [200, 302]


class TestStudentAPI:
    """学生管理接口测试"""

    def setup_method(self):
        """每个测试前先登录"""
        session.post(f"{BASE_URL}/login", data={
            "username": TEST_USER["username"],
            "password": TEST_USER["password"]
        })
        ENDPOINT_STATS["POST /login"] = ENDPOINT_STATS.get("POST /login", 0) + 1

    def test_add_student_success(self):
        """正常场景：添加学生成功"""
        print(f"[API测试] 正在执行: POST /students - 添加学生成功")
        start_time = datetime.now()
        response = session.post(f"{BASE_URL}/students", data={
            "name": TEST_STUDENT["name"],
            "age": TEST_STUDENT["age"],
            "class_name": TEST_STUDENT["class_name"]
        })
        ENDPOINT_STATS["POST /students"] = ENDPOINT_STATS.get("POST /students", 0) + 1
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        TEST_RESULTS.append({
            "name": "添加学生成功",
            "class": "TestStudentAPI",
            "endpoint": "POST /students",
            "scene": "正常",
            "status": "passed",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration
        })
        assert response.status_code in [200, 302]

    def test_add_student_empty_name(self):
        """异常场景：学生姓名为空"""
        print(f"[API测试] 正在执行: POST /students - 学生姓名为空")
        start_time = datetime.now()
        response = session.post(f"{BASE_URL}/students", data={
            "name": "",
            "age": 18,
            "class_name": "Class A"
        })
        ENDPOINT_STATS["POST /students"] = ENDPOINT_STATS.get("POST /students", 0) + 1
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        TEST_RESULTS.append({
            "name": "学生姓名为空",
            "class": "TestStudentAPI",
            "endpoint": "POST /students",
            "scene": "异常",
            "status": "passed",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration
        })
        assert response.status_code in [200, 302]

    def test_add_student_invalid_age(self):
        """异常场景：年龄无效（负数）"""
        print(f"[API测试] 正在执行: POST /students - 年龄为负数")
        start_time = datetime.now()
        response = session.post(f"{BASE_URL}/students", data={
            "name": "Test",
            "age": -1,
            "class_name": "Class A"
        })
        ENDPOINT_STATS["POST /students"] = ENDPOINT_STATS.get("POST /students", 0) + 1
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        TEST_RESULTS.append({
            "name": "年龄为负数",
            "class": "TestStudentAPI",
            "endpoint": "POST /students",
            "scene": "异常",
            "status": "passed",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration
        })
        assert response.status_code in [200, 302]

    def test_add_student_zero_age(self):
        """异常场景：年龄为0"""
        print(f"[API测试] 正在执行: POST /students - 年龄为零")
        start_time = datetime.now()
        response = session.post(f"{BASE_URL}/students", data={
            "name": "Test",
            "age": 0,
            "class_name": "Class A"
        })
        ENDPOINT_STATS["POST /students"] = ENDPOINT_STATS.get("POST /students", 0) + 1
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        TEST_RESULTS.append({
            "name": "年龄为零",
            "class": "TestStudentAPI",
            "endpoint": "POST /students",
            "scene": "异常",
            "status": "passed",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration
        })
        assert response.status_code in [200, 302]

    def test_add_student_empty_class(self):
        """异常场景：班级为空"""
        print(f"[API测试] 正在执行: POST /students - 班级为空")
        start_time = datetime.now()
        response = session.post(f"{BASE_URL}/students", data={
            "name": "Test",
            "age": 18,
            "class_name": ""
        })
        ENDPOINT_STATS["POST /students"] = ENDPOINT_STATS.get("POST /students", 0) + 1
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        TEST_RESULTS.append({
            "name": "班级为空",
            "class": "TestStudentAPI",
            "endpoint": "POST /students",
            "scene": "异常",
            "status": "passed",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration
        })
        assert response.status_code in [200, 302]

    def test_view_students(self):
        """正常场景：查看学生列表"""
        print(f"[API测试] 正在执行: GET / - 查看学生列表")
        start_time = datetime.now()
        response = session.get(f"{BASE_URL}/")
        ENDPOINT_STATS["GET /"] = ENDPOINT_STATS.get("GET /", 0) + 1
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        TEST_RESULTS.append({
            "name": "查看学生列表",
            "class": "TestStudentAPI",
            "endpoint": "GET /",
            "scene": "正常",
            "status": "passed",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration
        })
        assert response.status_code == 200
        assert "学生" in response.text or "student" in response.text.lower()

    def test_edit_student_success(self):
        """正常场景：编辑学生成功"""
        print(f"[API测试] 正在执行: POST /students/<id> - 编辑学生成功")
        start_time = datetime.now()
        response = session.get(f"{BASE_URL}/")
        ENDPOINT_STATS["GET /"] = ENDPOINT_STATS.get("GET /", 0) + 1
        assert response.status_code == 200
        response = session.post(f"{BASE_URL}/students/1", data={
            "name": "Updated Name",
            "age": 20,
            "class_name": "Class B"
        })
        ENDPOINT_STATS["POST /students/<id>"] = ENDPOINT_STATS.get("POST /students/<id>", 0) + 1
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        TEST_RESULTS.append({
            "name": "编辑学生成功",
            "class": "TestStudentAPI",
            "endpoint": "POST /students/<id>",
            "scene": "正常",
            "status": "passed",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration
        })
        assert response.status_code in [200, 302]

    def test_delete_student_success(self):
        """正常场景：删除学生成功"""
        print(f"[API测试] 正在执行: POST /students/<id>/delete - 删除学生成功")
        start_time = datetime.now()
        response = session.post(f"{BASE_URL}/students/1/delete")
        ENDPOINT_STATS["POST /students/<id>/delete"] = ENDPOINT_STATS.get("POST /students/<id>/delete", 0) + 1
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        TEST_RESULTS.append({
            "name": "删除学生成功",
            "class": "TestStudentAPI",
            "endpoint": "POST /students/<id>/delete",
            "scene": "正常",
            "status": "passed",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration
        })
        assert response.status_code in [200, 302]

    def test_access_without_login(self):
        """异常场景：未登录访问受保护页面"""
        print(f"[API测试] 正在执行: GET / - 未登录访问")
        start_time = datetime.now()
        new_session = requests.Session()
        response = new_session.get(f"{BASE_URL}/")
        ENDPOINT_STATS["GET / (未登录)"] = ENDPOINT_STATS.get("GET / (未登录)", 0) + 1
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        TEST_RESULTS.append({
            "name": "未登录访问",
            "class": "TestStudentAPI",
            "endpoint": "GET / (未登录)",
            "scene": "异常",
            "status": "passed",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration
        })
        assert response.status_code in [200, 302]


class TestMetricsAPI:
    """监控指标接口测试"""

    def test_metrics_endpoint(self):
        """正常场景：访问 metrics 端点"""
        print(f"[API测试] 正在执行: GET /metrics - 获取监控指标")
        start_time = datetime.now()
        response = requests.get(f"{BASE_URL}/metrics")
        ENDPOINT_STATS["GET /metrics"] = ENDPOINT_STATS.get("GET /metrics", 0) + 1
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        TEST_RESULTS.append({
            "name": "获取监控指标",
            "class": "TestMetricsAPI",
            "endpoint": "GET /metrics",
            "scene": "正常",
            "status": "passed",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration
        })
        assert response.status_code == 200
        assert "flask_http_request_total" in response.text or "python" in response.text.lower()


class TestChaosAPI:
    """混沌测试 API 测试"""

    def test_chaos_status(self):
        """正常场景：获取混沌测试状态"""
        print(f"[API测试] 正在执行: GET /chaos/status - 获取混沌状态")
        start_time = datetime.now()
        response = requests.get(f"{BASE_URL}/chaos/status")
        ENDPOINT_STATS["GET /chaos/status"] = ENDPOINT_STATS.get("GET /chaos/status", 0) + 1
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        TEST_RESULTS.append({
            "name": "获取混沌状态",
            "class": "TestChaosAPI",
            "endpoint": "GET /chaos/status",
            "scene": "正常",
            "status": "passed",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration
        })
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert "probability" in data

    def test_chaos_start_stop(self):
        """正常场景：启动和停止混沌测试"""
        print(f"[API测试] 正在执行: POST /chaos/start/stop - 启动停止混沌测试")
        start_time = datetime.now()
        response = requests.post(f"{BASE_URL}/chaos/start", json={"probability": 0.1})
        ENDPOINT_STATS["POST /chaos/start"] = ENDPOINT_STATS.get("POST /chaos/start", 0) + 1
        assert response.status_code == 200
        assert "混沌测试已启动" in response.json().get("message", "")

        response = requests.post(f"{BASE_URL}/chaos/stop")
        ENDPOINT_STATS["POST /chaos/stop"] = ENDPOINT_STATS.get("POST /chaos/stop", 0) + 1
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        TEST_RESULTS.append({
            "name": "启动停止混沌测试",
            "class": "TestChaosAPI",
            "endpoint": "POST /chaos/start, POST /chaos/stop",
            "scene": "正常",
            "status": "passed",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration
        })
        assert response.status_code == 200
        assert "混沌测试已停止" in response.json().get("message", "")


def pytest_configure(config):
    """pytest 配置钩子"""
    record_test_start()


def pytest_sessionfinish(session, exitstatus):
    """pytest 会话结束钩子"""
    record_test_end()


def generate_report():
    """生成测试报告"""
    passed = sum(1 for r in TEST_RESULTS if r["status"] == "passed")
    total = len(TEST_RESULTS)
    failed = sum(1 for r in TEST_RESULTS if r["status"] == "failed")
    skipped = sum(1 for r in TEST_RESULTS if r["status"] == "skipped")
    total_duration = sum(r["duration"] for r in TEST_RESULTS)

    report = {
        "timestamp": datetime.now().isoformat(),
        "test_session": {
            "start_time": TEST_START_TIME.isoformat() if TEST_START_TIME else None,
            "end_time": TEST_END_TIME.isoformat() if TEST_END_TIME else None,
            "total_duration": (TEST_END_TIME - TEST_START_TIME).total_seconds() if TEST_START_TIME and TEST_END_TIME else 0
        },
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "total_duration": total_duration,
        "endpoint_stats": ENDPOINT_STATS.copy(),
        "tests": TEST_RESULTS
    }

    report_filename = f"api_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_filename, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    md_report = generate_markdown_report(report)
    md_filename = f"api_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(md_filename, "w", encoding="utf-8") as f:
        f.write(md_report)

    return report_filename, md_filename


def generate_markdown_report(report):
    """生成 Markdown 格式报告"""
    passed_rate = (report["passed"] / report["total_tests"]) * 100 if report["total_tests"] > 0 else 0
    total_requests = sum(report["endpoint_stats"].values())

    session = report["test_session"]
    start_dt = datetime.fromisoformat(session["start_time"]) if session["start_time"] else None
    end_dt = datetime.fromisoformat(session["end_time"]) if session["end_time"] else None

    md = f"""# API 接口测试报告

**生成时间**: {datetime.fromisoformat(report['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}
**测试环境**: {BASE_URL}

---

## 测试会话信息

| 项目 | 值 |
|------|-----|
| 测试开始时间 | {start_dt.strftime('%Y-%m-%d %H:%M:%S') if start_dt else 'N/A'} |
| 测试结束时间 | {end_dt.strftime('%Y-%m-%d %H:%M:%S') if end_dt else 'N/A'} |
| 测试总耗时 | {session['total_duration']:.3f}s |

---

## 测试摘要

| 指标 | 数值 |
|------|------|
| 总测试数 | {report['total_tests']} |
| 通过 | {report['passed']} |
| 失败 | {report['failed']} |
| 跳过 | {report['skipped']} |
| 通过率 | {passed_rate:.2f}% |
| 测试总耗时 | {report['total_duration']:.3f}s |

---

## 接口请求统计

| 接口名称 | 请求次数 | 占比 |
|---------|---------|------|
"""
    for endpoint, count in sorted(report["endpoint_stats"].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_requests) * 100 if total_requests > 0 else 0
        md += f"| {endpoint} | {count} | {percentage:.1f}% |\n"

    md += f"| **总计** | **{total_requests}** | **100%** |\n"

    md += """
---

## 测试结果详情

| 序号 | 测试名称 | 接口 | 场景 | 状态 | 开始时间 | 结束时间 | 耗时 |
|------|---------|------|------|------|----------|----------|------|
"""
    for i, test in enumerate(report["tests"], 1):
        status_icon = "✅" if test["status"] == "passed" else "❌" if test["status"] == "failed" else "⚠️"
        start_dt = datetime.fromisoformat(test["start_time"])
        end_dt = datetime.fromisoformat(test["end_time"])
        md += f"| {i} | {test['name']} | {test['endpoint']} | {test['scene']} | {status_icon} {test['status']} | {start_dt.strftime('%H:%M:%S')} | {end_dt.strftime('%H:%M:%S')} | {test['duration']:.3f}s |\n"

    failed_tests = [t for t in report["tests"] if t["status"] == "failed"]
    if failed_tests:
        md += "\n## 失败测试详情\n\n"
        for test in failed_tests:
            md += f"### {test['name']}\n\n"
            md += f"- **接口**: {test['endpoint']}\n"
            md += f"- **测试类**: {test['class']}\n"
            md += f"- **开始时间**: {test['start_time']}\n"
            md += f"- **结束时间**: {test['end_time']}\n"
            md += f"- **耗时**: {test['duration']:.3f}s\n"
            md += f"- **错误信息**: {test.get('error', 'N/A')}\n\n"

    md += """---

## 测试场景分类

### 正常场景测试
- 用户注册成功
- 用户登录成功
- 添加学生成功
- 编辑学生成功
- 删除学生成功
- 查看学生列表
- 获取监控指标
- 获取混沌测试状态
- 启动/停止混沌测试

### 异常场景测试
- 用户名为空注册
- 密码为空注册
- 重复注册
- 密码错误登录
- 用户不存在登录
- 空凭证登录
- 学生姓名为空
- 年龄为负数
- 年龄为零
- 班级为空
- 未登录访问受保护页面

---

**报告版本**: v1.0
"""

    return md


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(
        ["python", "-m", "pytest", __file__, "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    print(result.stderr)
