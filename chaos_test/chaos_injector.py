import random
import time
import threading
from functools import wraps
from flask import request, abort

# 混沌测试配置
CHAOS_ENABLED = False
FAILURE_PROBABILITY = 0.1  # 10% 概率触发故障
MAX_DELAY = 3  # 最大延迟秒数

# 故障类型
FAILURE_TYPES = {
    'latency': '网络延迟',
    'error': '随机错误',
    'timeout': '超时',
    'db_failure': '数据库故障'
}

def chaos_enabled():
    return CHAOS_ENABLED

def set_chaos_enabled(enabled):
    global CHAOS_ENABLED
    CHAOS_ENABLED = enabled

def set_failure_probability(probability):
    global FAILURE_PROBABILITY
    FAILURE_PROBABILITY = probability

def inject_latency(max_delay=MAX_DELAY):
    """注入随机延迟"""
    delay = random.uniform(0.1, max_delay)
    time.sleep(delay)
    return delay

def inject_error():
    """注入随机错误"""
    errors = [
        {'code': 500, 'message': 'Internal Server Error (Chaos)'},
        {'code': 503, 'message': 'Service Unavailable (Chaos)'},
        {'code': 408, 'message': 'Request Timeout (Chaos)'}
    ]
    return random.choice(errors)

def chaos_decorator(func):
    """混沌测试装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not CHAOS_ENABLED:
            return func(*args, **kwargs)
        
        # 根据概率决定是否注入故障
        if random.random() < FAILURE_PROBABILITY:
            failure_type = random.choice(list(FAILURE_TYPES.keys()))
            
            if failure_type == 'latency':
                delay = inject_latency()
                print(f"[CHAOS] 注入延迟: {delay:.2f}s")
                result = func(*args, **kwargs)
                return result
                
            elif failure_type == 'error':
                error = inject_error()
                print(f"[CHAOS] 注入错误: {error['code']} - {error['message']}")
                abort(error['code'], description=error['message'])
                
            elif failure_type == 'timeout':
                print(f"[CHAOS] 注入超时")
                time.sleep(10)  # 模拟超时
                abort(408, description='Request Timeout (Chaos)')
                
            elif failure_type == 'db_failure':
                print(f"[CHAOS] 注入数据库故障")
                abort(500, description='Database Connection Failed (Chaos)')
        
        return func(*args, **kwargs)
    
    return wrapper

class ChaosController:
    """混沌测试控制器"""
    
    def __init__(self):
        self.enabled = False
        self.probability = FAILURE_PROBABILITY
        self.running = False
        self.thread = None
    
    def start(self, probability=0.1):
        """启动混沌测试"""
        self.enabled = True
        self.probability = probability
        set_chaos_enabled(True)
        set_failure_probability(probability)
        self.running = True
        print(f"[CHAOS] 混沌测试已启动，故障概率: {probability*100}%")
    
    def stop(self):
        """停止混沌测试"""
        self.enabled = False
        set_chaos_enabled(False)
        self.running = False
        print("[CHAOS] 混沌测试已停止")
    
    def status(self):
        """获取混沌测试状态"""
        return {
            'enabled': self.enabled,
            'probability': self.probability,
            'running': self.running,
            'failure_types': list(FAILURE_TYPES.keys())
        }
    
    def simulate_db_failure(self, duration=30):
        """模拟数据库故障持续一段时间"""
        print(f"[CHAOS] 模拟数据库故障，持续 {duration} 秒")
        original_enabled = self.enabled
        self.enabled = True
        
        def restore_db():
            time.sleep(duration)
            self.enabled = original_enabled
            print("[CHAOS] 数据库故障模拟结束")
        
        thread = threading.Thread(target=restore_db)
        thread.daemon = True
        thread.start()
