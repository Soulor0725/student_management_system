"""混沌测试配置"""

# 默认配置
DEFAULT_CONFIG = {
    'enabled': False,
    'failure_probability': 0.1,
    'max_delay': 3,
    'failure_types': ['latency', 'error', 'timeout', 'db_failure'],
    'whitelisted_endpoints': [
        '/chaos/status',
        '/chaos/start',
        '/chaos/stop',
        '/chaos/toggle',
        '/chaos/config'
    ]
}

# 故障类型说明
FAILURE_TYPE_DESCRIPTIONS = {
    'latency': {
        'name': '网络延迟',
        'description': '随机延迟 0.1-3 秒',
        'severity': 'low'
    },
    'error': {
        'name': '随机错误',
        'description': '随机返回 500/503/408 错误',
        'severity': 'medium'
    },
    'timeout': {
        'name': '超时',
        'description': '模拟请求超时',
        'severity': 'high'
    },
    'db_failure': {
        'name': '数据库故障',
        'description': '模拟数据库连接失败',
        'severity': 'critical'
    }
}

# 预设场景
SCENARIOS = {
    'light': {
        'name': '轻度混沌',
        'probability': 0.05,
        'failure_types': ['latency']
    },
    'normal': {
        'name': '标准混沌',
        'probability': 0.1,
        'failure_types': ['latency', 'error']
    },
    'heavy': {
        'name': '重度混沌',
        'probability': 0.2,
        'failure_types': ['latency', 'error', 'timeout']
    },
    'extreme': {
        'name': '极端混沌',
        'probability': 0.3,
        'failure_types': ['latency', 'error', 'timeout', 'db_failure']
    }
}
