import time
import requests
import json
import argparse
from datetime import datetime

def run_chaos_scenario(base_url, scenario='normal', duration=60):
    """运行混沌测试场景"""
    print(f"\n=== 开始混沌测试场景: {scenario} ===")
    print(f"测试时长: {duration} 秒")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 启动混沌测试
    try:
        response = requests.post(f"{base_url}/chaos/start", json={'probability': 0.1})
        if response.status_code == 200:
            print("✅ 混沌测试已启动")
        else:
            print(f"❌ 启动失败: {response.text}")
            return
    except Exception as e:
        print(f"❌ 连接失败: {e}")
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
            
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            
            if response.status_code == 200:
                success_count += 1
            else:
                failure_count += 1
                error_codes[response.status_code] = error_codes.get(response.status_code, 0) + 1
            
            print(f"请求 {endpoint}: {response.status_code}", end='\r')
            
        except requests.exceptions.RequestException as e:
            failure_count += 1
            error_codes['exception'] = error_codes.get('exception', 0) + 1
            print(f"请求失败: {e}", end='\r')
        
        time.sleep(0.5)
    
    # 停止混沌测试
    try:
        requests.post(f"{base_url}/chaos/stop")
        print("\n✅ 混沌测试已停止")
    except Exception as e:
        print(f"\n❌ 停止失败: {e}")
    
    # 输出测试结果
    print("\n=== 测试结果 ===")
    print(f"总请求数: {success_count + failure_count}")
    print(f"成功请求: {success_count} ({success_count / (success_count + failure_count) * 100:.2f}%)")
    print(f"失败请求: {failure_count} ({failure_count / (success_count + failure_count) * 100:.2f}%)")
    print("错误码分布:")
    for code, count in error_codes.items():
        print(f"  - {code}: {count} 次")
    
    print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def main():
    parser = argparse.ArgumentParser(description='混沌测试运行器')
    parser.add_argument('--url', default='http://localhost:5000', help='目标应用URL')
    parser.add_argument('--scenario', default='normal', choices=['light', 'normal', 'heavy', 'extreme'], help='混沌场景')
    parser.add_argument('--duration', type=int, default=60, help='测试时长(秒)')
    
    args = parser.parse_args()
    
    run_chaos_scenario(args.url, args.scenario, args.duration)

if __name__ == '__main__':
    main()
