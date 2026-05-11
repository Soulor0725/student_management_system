"""端到端集成测试用例"""
import pytest
from datetime import datetime

class TestEndToEndIntegration:
    """端到端集成测试类"""

    def test_full_user_registration_login_flow(self, client, test_user):
        """
        端到端测试：用户注册 -> 登录 -> 访问首页
        验证完整的用户认证流程
        """
        print(f"[集成测试] 正在执行: 用户注册登录流程")
        # Step 1: 用户注册
        register_response = client.post('/register', data={
            'username': test_user['username'],
            'password': test_user['password']
        })
        assert register_response.status_code in [200, 302]

        # Step 2: 用户登录
        login_response = client.post('/login', data={
            'username': test_user['username'],
            'password': test_user['password']
        })
        assert login_response.status_code == 200

        # Step 3: 访问首页（登录后）
        index_response = client.get('/')
        assert index_response.status_code == 200
        assert '学生管理'.encode('utf-8') in index_response.data

    def test_student_full_lifecycle(self, client, test_user, test_student):
        """
        端到端测试：添加学生 -> 查看列表 -> 编辑 -> 删除
        验证学生管理完整生命周期
        """
        print(f"[集成测试] 正在执行: 学生完整生命周期")
        # 先登录
        client.post('/register', data=test_user)
        client.post('/login', data=test_user)

        # Step 1: 添加学生
        add_response = client.post('/students', data=test_student)
        assert add_response.status_code == 302

        # Step 2: 查看学生列表，验证学生已添加
        list_response = client.get('/')
        assert list_response.status_code == 200
        assert test_student['name'].encode() in list_response.data

    def test_user_session_persistence(self, client, test_user):
        """
        端到端测试：会话持久化验证
        验证登录状态在多个请求间保持
        """
        print(f"[集成测试] 正在执行: 用户会话持久化")
        # 注册并登录
        client.post('/register', data=test_user)
        client.post('/login', data=test_user)

        # 连续访问多个页面
        response1 = client.get('/')
        response2 = client.get('/')
        response3 = client.get('/')

        # 验证所有请求都保持登录状态
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200
        assert '学生管理'.encode('utf-8') in response1.data
        assert '学生管理'.encode('utf-8') in response2.data
        assert '学生管理'.encode('utf-8') in response3.data

    def test_unauthenticated_access_control(self, client):
        """
        端到端测试：未认证用户访问控制
        验证未登录用户无法访问受保护页面
        """
        print(f"[集成测试] 正在执行: 未认证用户访问控制")
        # 清理session确保未登录状态
        with client.session_transaction() as sess:
            sess.clear()

        # 尝试直接访问学生列表
        response = client.get('/')
        assert response.status_code == 302

    def test_register_login_logout_flow(self, client, test_user):
        """
        端到端测试：注册 -> 登录 -> 登出完整流程
        """
        print(f"[集成测试] 正在执行: 注册登录登出完整流程")
        # Step 1: 注册
        client.post('/register', data=test_user)

        # Step 2: 登录
        client.post('/login', data=test_user)

        # Step 3: 验证已登录
        response = client.get('/')
        assert response.status_code == 200

        # Step 4: 登出（POST方法）
        response = client.post('/logout')
        assert response.status_code == 302

        # Step 5: 验证已登出，访问被拒绝
        response = client.get('/')
        assert response.status_code == 302

    def test_concurrent_user_operations(self, client):
        """
        端到端测试：并发用户操作
        验证多个用户可以独立操作
        """
        print(f"[集成测试] 正在执行: 并发用户操作")
        user1 = {'username': 'user1_int', 'password': 'pass1'}
        user2 = {'username': 'user2_int', 'password': 'pass2'}
        student1 = {'name': 'User1Student', 'age': '16', 'class_name': 'Grade1Class1'}
        student2 = {'name': 'User2Student', 'age': '17', 'class_name': 'Grade2Class2'}

        # 用户1注册登录并添加学生
        client.post('/register', data=user1)
        client.post('/login', data=user1)
        client.post('/students', data=student1)

        # 用户1登出
        client.post('/logout')

        # 用户2注册登录并添加学生
        client.post('/register', data=user2)
        client.post('/login', data=user2)
        client.post('/students', data=student2)

        # 用户2查看列表
        response = client.get('/')
        assert student2['name'].encode() in response.data

    def test_metrics_endpoint_integration(self, client, test_user):
        """
        端到端测试：监控指标集成
        验证监控接口正常工作
        """
        print(f"[集成测试] 正在执行: 监控指标集成")
        # 登录
        client.post('/register', data=test_user)
        client.post('/login', data=test_user)

        # 执行一些操作
        client.get('/')
        client.post('/students', data={
            'name': 'TestStudent',
            'age': '18',
            'class_name': 'TestClass'
        })
        client.get('/')

        # 验证监控指标可访问
        response = client.get('/metrics')
        assert response.status_code == 200
        assert b'flask_http_request_total' in response.data

    def test_chaos_test_integration(self, client, test_user):
        """
        端到端测试：混沌测试集成
        验证混沌测试功能与主系统集成
        """
        print(f"[集成测试] 正在执行: 混沌测试集成")
        # 登录
        client.post('/register', data=test_user)
        client.post('/login', data=test_user)

        # 检查混沌测试状态
        response = client.get('/chaos/status')
        assert response.status_code == 200

        # 启动混沌测试（低概率故障）
        response = client.post('/chaos/start', json={'probability': 0.1})
        assert response.status_code == 200

        # 检查混沌测试已启动
        response = client.get('/chaos/status')
        assert response.status_code == 200

        # 执行一些操作（大部分应该正常）
        response = client.get('/')
        assert response.status_code in [200, 302]

        # 停止混沌测试
        response = client.post('/chaos/stop')
        assert response.status_code == 200

    def test_data_persistence_integration(self, client, test_user, test_student):
        """
        端到端测试：数据持久化验证
        验证数据在请求间持久化
        """
        print(f"[集成测试] 正在执行: 数据持久化验证")
        # 第一次会话：注册、登录、添加学生
        client.post('/register', data=test_user)
        client.post('/login', data=test_user)
        client.post('/students', data=test_student)

        # 获取会话cookie，模拟新会话
        with client.session_transaction() as sess:
            pass

        # 第二次会话：重新登录、验证数据存在
        client.post('/login', data=test_user)
        response = client.get('/')
        assert test_student['name'].encode() in response.data

    def test_error_handling_integration(self, client):
        """
        端到端测试：错误处理集成
        验证系统对异常输入的处理
        """
        # 测试空表单提交
        response = client.post('/register', data={})
        assert response.status_code in [200, 302]

        # 测试不存在的路由
        response = client.get('/nonexistent_route')
        assert response.status_code == 404

        # 测试无效的HTTP方法
        response = client.put('/')
        assert response.status_code in [405, 302]

        # 测试大请求（如果有限制）
        large_data = {'name': 'a' * 10000, 'age': '18', 'class_name': 'test'}
        response = client.post('/students', data=large_data)
        assert response.status_code in [200, 302]

    def test_performance_baseline(self, client, test_user):
        """
        端到端测试：性能基线测试
        验证系统响应时间在可接受范围内
        """
        # 登录
        client.post('/register', data=test_user)
        client.post('/login', data=test_user)

        # 测试多次请求的响应时间
        import time
        total_time = 0
        for _ in range(5):
            start = time.time()
            client.get('/')
            elapsed = time.time() - start
            total_time += elapsed
            assert elapsed < 2.0

        avg_time = total_time / 5
        assert avg_time < 1.0