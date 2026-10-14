"""Locust 性能测试脚本

使用 Locust 进行 API 性能测试，支持分布式测试和 CI 集成。
"""

import os
import random
import re
from locust import HttpUser, task, between, events
from locust.stats import stats_printer, stats_history
from locust.log import setup_logging

# 配置日志
setup_logging("INFO", None)

_CSRF_RE = re.compile(r'name="csrf_token"\s+value="([^"]+)"')


class StudentManagementUser(HttpUser):
    """学生管理系统性能测试用户"""
    
    wait_time = between(1, 3)
    host = "http://localhost:5000"
    
    def _refresh_csrf(self):
        """从页面提取 CSRF token（登录会轮换会话 token）。"""
        try:
            resp = self.client.get("/login")
            match = _CSRF_RE.search(resp.text or "")
            if match:
                self.client.headers["X-CSRF-TOKEN"] = match.group(1)
        except Exception:
            pass

    def on_start(self):
        """用户开始时执行 - 注册并登录"""
        self.username = f"test_user_{random.randint(1000, 9999)}"
        self.password = "test123"
        
        try:
            self._refresh_csrf()
            self.client.post("/register", {
                "username": self.username,
                "password": self.password
            })
        except Exception:
            pass
        
        self._refresh_csrf()
        response = self.client.post("/login", {
            "username": self.username,
            "password": self.password
        })
        # 登录清空了会话，重新取 token 供后续 POST 使用
        self._refresh_csrf()
        
        if response.status_code == 200:
            self.logged_in = True
        else:
            self.logged_in = False
    
    def on_stop(self):
        """用户结束时执行"""
        if self.logged_in:
            self._refresh_csrf()
            self.client.post("/logout")
    
    @task(3)
    def view_students(self):
        """查看学生列表 - 权重3"""
        if self.logged_in:
            self.client.get("/")
    
    @task(2)
    def add_student(self):
        """添加学生 - 权重2"""
        if self.logged_in:
            self.client.post("/students", {
                "name": f"学生_{random.randint(1, 1000)}",
                "age": str(random.randint(15, 25)),
                "class_name": f"班级_{random.randint(1, 10)}班"
            })
    
    @task(1)
    def view_metrics(self):
        """查看监控指标 - 权重1"""
        self.client.get("/metrics")
    
    @task(1)
    def chaos_status(self):
        """查看混沌测试状态 - 权重1"""
        self.client.get("/chaos/status")


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Locust 初始化事件"""
    print(f"[INFO] Locust 性能测试启动")
    print(f"[INFO] 目标主机: {StudentManagementUser.host}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """测试开始事件"""
    print("[INFO] 性能测试开始...")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """测试结束事件"""
    print("[INFO] 性能测试结束")
    
    stats = environment.stats.total
    print(f"\n=== 测试统计 ===")
    print(f"请求总数: {stats.num_requests}")
    print(f"失败总数: {stats.num_failures}")
    print(f"平均响应时间: {stats.avg_response_time:.2f}ms")
    print(f"最小响应时间: {stats.min_response_time:.2f}ms")
    print(f"最大响应时间: {stats.max_response_time:.2f}ms")
    print(f"请求速率: {stats.total_rps:.2f}/s")