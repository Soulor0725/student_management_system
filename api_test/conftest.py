"""pytest 配置和钩子

用于捕获测试计时和生成报告。
"""

import os
import pytest
import json
from datetime import datetime
from pathlib import Path


TEST_RESULTS = []
TEST_START_TIME = None
TEST_END_TIME = None
ENDPOINT_STATS = {}

NAME_CN_MAP = {
    "test_register_success": "用户注册成功",
    "test_register_empty_username": "用户名为空注册",
    "test_register_empty_password": "密码为空注册",
    "test_register_duplicate": "重复注册",
    "test_login_success": "用户登录成功",
    "test_login_wrong_password": "密码错误登录",
    "test_login_nonexistent_user": "用户不存在登录",
    "test_login_empty_credentials": "空凭证登录",
    "test_add_student_success": "添加学生成功",
    "test_add_student_empty_name": "学生姓名为空",
    "test_add_student_invalid_age": "年龄为负数",
    "test_add_student_zero_age": "年龄为零",
    "test_add_student_empty_class": "班级为空",
    "test_view_students": "查看学生列表",
    "test_edit_student_success": "编辑学生成功",
    "test_delete_student_success": "删除学生成功",
    "test_access_without_login": "未登录访问",
    "test_metrics_endpoint": "获取监控指标",
    "test_chaos_status": "获取混沌状态",
    "test_chaos_start_stop": "启动停止混沌测试"
}


def pytest_configure(config):
    """pytest 配置钩子 - 测试开始"""
    global TEST_START_TIME
    TEST_START_TIME = datetime.now()


def pytest_sessionfinish(session, exitstatus):
    """pytest 会话结束钩子 - 生成报告"""
    global TEST_END_TIME
    TEST_END_TIME = datetime.now()

    # 生成报告
    generate_report()


def pytest_runtest_logreport(report):
    """捕获测试报告"""
    if report.when == "call":
        # 从测试报告中提取信息
        test_name = report.nodeid.split("::")[-1]
        test_class = "::".join(report.nodeid.split("::")[:-1]).replace("test_api.py::", "")

        # 提取端点信息（从测试名称推断）
        endpoint = infer_endpoint(test_name)

        # 获取中文名称
        test_name_cn = NAME_CN_MAP.get(test_name, test_name)

        # 记录测试结果
        TEST_RESULTS.append({
            "name": test_name_cn,
            "class": test_class,
            "endpoint": endpoint,
            "scene": "正常" if "success" in test_name and "empty" not in test_name and "wrong" not in test_name and "nonexistent" not in test_name and "invalid" not in test_name and "without" not in test_name and "zero" not in test_name else "异常",
            "status": "passed" if report.passed else ("failed" if report.failed else "skipped"),
            "start_time": datetime.fromtimestamp(report.startdate).isoformat() if hasattr(report, 'startdate') else TEST_START_TIME.isoformat(),
            "end_time": datetime.fromtimestamp(report.stopdate).isoformat() if hasattr(report, 'stopdate') else datetime.now().isoformat(),
            "duration": report.duration
        })

        # 更新端点统计
        if endpoint:
            ENDPOINT_STATS[endpoint] = ENDPOINT_STATS.get(endpoint, 0) + 1


def infer_endpoint(test_name):
    """从测试名称推断端点"""
    endpoint_map = {
        "register": "POST /register",
        "login": "POST /login",
        "add_student": "POST /students",
        "view_students": "GET /",
        "edit_student": "POST /students/<id>",
        "delete_student": "POST /students/<id>/delete",
        "access_without_login": "GET / (未登录)",
        "metrics": "GET /metrics",
        "chaos_status": "GET /chaos/status",
        "chaos_start_stop": "POST /chaos/start, POST /chaos/stop"
    }

    for key, endpoint in endpoint_map.items():
        if key in test_name:
            return endpoint
    return "Unknown"


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

    # 生成时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 生成 JSON 报告
    test_dir = Path(__file__).parent
    os.makedirs(test_dir / "reports", exist_ok=True)

    json_report_path = test_dir / "reports" / f"api_test_report_{timestamp}.json"
    with open(json_report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # 生成 Markdown 报告
    md_report = generate_markdown_report(report, timestamp)
    md_report_path = test_dir / "reports" / f"api_test_report_{timestamp}.md"
    with open(md_report_path, "w", encoding="utf-8") as f:
        f.write(md_report)

    print()
    print("=" * 60)
    print("Test report generated:")
    print(f"   JSON: {json_report_path}")
    print(f"   Markdown: {md_report_path}")
    print("=" * 60)


def generate_markdown_report(report, timestamp):
    """生成 Markdown 格式报告"""
    import os

    passed_rate = (report["passed"] / report["total_tests"]) * 100 if report["total_tests"] > 0 else 0
    total_requests = sum(report["endpoint_stats"].values())

    session_info = report["test_session"]
    start_dt = datetime.fromisoformat(session_info["start_time"]) if session_info["start_time"] else None
    end_dt = datetime.fromisoformat(session_info["end_time"]) if session_info["end_time"] else None

    md = f"""# API 接口测试报告

**生成时间**: {datetime.fromisoformat(report['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}
**测试环境**: http://localhost:5000

---

## 测试会话信息

| 项目 | 值 |
|------|-----|
| 测试开始时间 | {start_dt.strftime('%Y-%m-%d %H:%M:%S') if start_dt else 'N/A'} |
| 测试结束时间 | {end_dt.strftime('%Y-%m-%d %H:%M:%S') if end_dt else 'N/A'} |
| 测试总耗时 | {session_info['total_duration']:.3f}s |

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
