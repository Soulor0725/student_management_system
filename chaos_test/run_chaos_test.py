import time
import requests
import json
import argparse
from datetime import datetime

# 场景配置
SCENARIOS = {
    'light': {'probability': 0.05, 'name': '轻度混沌'},
    'normal': {'probability': 0.1, 'name': '标准混沌'},
    'heavy': {'probability': 0.2, 'name': '重度混沌'},
    'extreme': {'probability': 0.5, 'name': '极端混沌'}
}

def run_chaos_scenario(base_url, scenario='normal', duration=60):
    """运行混沌测试场景"""
    scenario_config = SCENARIOS.get(scenario, SCENARIOS['normal'])
    probability = scenario_config['probability']
    
    print("\n=== 开始混沌测试场景: %s ===" % scenario_config['name'])
    print("测试时长: %d 秒" % duration)
    print("故障概率: %.1f%%" % (probability*100))
    print("开始时间: %s" % datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    # 启动混沌测试
    try:
        response = requests.post("%s/chaos/start" % base_url, json={'probability': probability})
        if response.status_code == 200:
            print("[OK] 混沌测试已启动")
        else:
            print("[FAIL] 启动失败: %s" % response.text)
            return
    except Exception as e:
        print("[FAIL] 连接失败: %s" % str(e))
        return
    
    # 模拟用户请求
    success_count = 0
    failure_count = 0
    error_codes = {}
    
    start_time = time.time()
    while time.time() - start_time < duration:
        try:
            # 随机访问接口
            endpoints = ['/login', '/students', '/']
            endpoint = endpoints[0]  # 测试登录接口
            
            response = requests.get("%s%s" % (base_url, endpoint), timeout=10)
            
            if response.status_code == 200:
                success_count += 1
            else:
                failure_count += 1
                error_codes[response.status_code] = error_codes.get(response.status_code, 0) + 1
            
            print("请求 %s: %d" % (endpoint, response.status_code), end='\r')
            
        except requests.exceptions.RequestException as e:
            failure_count += 1
            error_codes['exception'] = error_codes.get('exception', 0) + 1
            print("请求失败: %s" % str(e), end='\r')
        
        time.sleep(0.5)
    
    # 停止混沌测试
    try:
        requests.post("%s/chaos/stop" % base_url)
        print("\n[OK] 混沌测试已停止")
    except Exception as e:
        print("\n[FAIL] 停止失败: %s" % str(e))
    
    # 输出测试结果
    print("\n=== 测试结果 ===")
    total = success_count + failure_count
    print("总请求数: %d" % total)
    print("成功请求: %d (%.2f%%)" % (success_count, success_count / total * 100))
    print("失败请求: %d (%.2f%%)" % (failure_count, failure_count / total * 100))
    print("错误码分布:")
    for code, count in error_codes.items():
        print("  - %s: %d 次" % (str(code), count))
    
    print("\n结束时间: %s" % datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

def main():
    parser = argparse.ArgumentParser(description='混沌测试运行器')
    parser.add_argument('--url', default='http://localhost:5000', help='目标应用URL')
    parser.add_argument('--scenario', default='normal', choices=['light', 'normal', 'heavy', 'extreme'], help='混沌场景')
    parser.add_argument('--duration', type=int, default=60, help='测试时长(秒)')
    
    args = parser.parse_args()
    
    run_chaos_scenario(args.url, args.scenario, args.duration)

if __name__ == '__main__':
    main()