"""测试执行器配置"""

TEST_STAGES = {
    "smoke": {
        "name": "冒烟测试",
        "path": "smoke_test/test_smoke.py",
        "description": "核心路径快速验证"
    },
    "unit": {
        "name": "单元测试",
        "path": "unit_test/test_app.py",
        "description": "验证单个函数和模块的正确性"
    },
    "db": {
        "name": "数据库测试",
        "path": "db_test/test_db.py",
        "description": "数据库约束、自动建表、并发写入"
    },
    "contract": {
        "name": "接口契约测试",
        "path": "contract_test/test_contract.py",
        "description": "状态码契约、Header、幂等性"
    },
    "crud": {
        "name": "数据完整性测试",
        "path": "crud_test/test_crud.py",
        "description": "CRUD全链路、数据持久化、边界值"
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
    "reliability": {
        "name": "可靠性测试",
        "path": "reliability_test/test_reliability.py",
        "description": "稳定性、错误恢复、配置验证"
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

EXECUTION_ORDER = [
    "smoke", "unit", "db", "contract", "crud",
    "api", "integration", "security", "reliability",
    "automation", "performance", "chaos"
]

REPORTS_DIR = "test_executor/reports"
ALLURE_RESULTS_DIR = "test_executor/reports/allure-results"
ALLURE_REPORT_DIR = "test_executor/reports/allure-report"
