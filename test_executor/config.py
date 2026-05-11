"""测试执行器配置"""

TEST_STAGES = {
    "unit": {
        "name": "单元测试",
        "path": "unit_test/test_app.py",
        "description": "验证单个函数和模块的正确性"
    },
    "api": {
        "name": "API接口测试",
        "path": "api_test/test_api.py",
        "description": "验证API接口的功能和性能"
    },
    "integration": {
        "name": "集成测试",
        "path": "integration_test/test_integration.py",
        "description": "验证模块间的协作"
    },
    "security": {
        "name": "安全测试",
        "path": "security_test/test_security.py",
        "description": "检测安全漏洞"
    },
    "automation": {
        "name": "自动化测试",
        "path": "automation_test/test_playwright.py",
        "description": "UI自动化测试"
    },
    "performance": {
        "name": "性能测试",
        "path": "performance_test_jmeter",
        "description": "JMeter性能压测"
    },
    "chaos": {
        "name": "混沌测试",
        "path": "chaos_test/run_chaos_test.py",
        "description": "故障注入测试"
    }
}

EXECUTION_ORDER = ["unit", "api", "integration", "security", "automation", "performance", "chaos"]

REPORTS_DIR = "test_executor/reports"
ALLURE_RESULTS_DIR = "test_executor/reports/allure-results"
ALLURE_REPORT_DIR = "test_executor/reports/allure-report"