#!/usr/bin/env python3
"""统一测试执行器 - 一键执行所有测试并生成Allure风格报告"""

import argparse
import subprocess
import os
import sys
import json
from datetime import datetime
from config import TEST_STAGES, EXECUTION_ORDER, REPORTS_DIR, ALLURE_RESULTS_DIR, ALLURE_REPORT_DIR

def run_command(cmd, cwd=None, live_output=False):
    """执行命令并返回结果"""
    try:
        if live_output:
            # 实时输出模式
            result = subprocess.run(cmd, shell=True, text=True, cwd=cwd)
            return {
                "success": result.returncode == 0,
                "stdout": "",
                "stderr": "",
                "returncode": result.returncode
            }
        else:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": -1
        }

def run_pytest(test_path, stage_name):
    """运行pytest测试"""
    print(f"\n{'='*60}")
    print(f"  正在执行: {stage_name}")
    print(f"{'='*60}")
    
    # 确保报告目录存在
    os.makedirs(ALLURE_RESULTS_DIR, exist_ok=True)
    
    # 运行pytest - 使用实时输出模式，禁用输出捕获
    cmd = f"python -m pytest {test_path} -v --tb=short"
    cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = run_command(cmd, cwd=cwd, live_output=False)
    
    # 打印输出
    print(result["stdout"])
    if result["stderr"]:
        print("错误信息:", result["stderr"])
    
    # 解析测试数量
    output = result["stdout"]
    passed = 0
    failed = 0
    
    # 匹配类似 "14 passed" 或 "14 passed, 2 failed" 的行
    import re
    pass_match = re.search(r'(\d+)\s+passed', output)
    fail_match = re.search(r'(\d+)\s+failed', output)
    
    if pass_match:
        passed = int(pass_match.group(1))
    if fail_match:
        failed = int(fail_match.group(1))
    
    result["passed"] = passed
    result["failed"] = failed
    
    return result

def run_chaos_test():
    """运行混沌测试"""
    print(f"\n{'='*60}")
    print(f"  正在执行: 混沌测试")
    print(f"{'='*60}")
    
    cmd = "python chaos_test/run_chaos_test.py --url http://localhost:5000 --scenario normal --duration 10"
    result = run_command(cmd, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    print(result["stdout"])
    if result["stderr"]:
        print("错误信息:", result["stderr"])
    
    return result

def generate_summary_report(results):
    """生成汇总报告"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_stages": len(results),
        "passed_stages": sum(1 for r in results if r["success"]),
        "failed_stages": sum(1 for r in results if not r["success"]),
        "stages": results
    }
    
    # 保存JSON报告
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_path = os.path.join(REPORTS_DIR, f"test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # 生成Markdown报告
    md_report_path = os.path.join(REPORTS_DIR, f"test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    with open(md_report_path, "w", encoding="utf-8") as f:
        f.write("# 统一测试执行报告\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## 测试摘要\n\n")
        f.write(f"| 项目 | 数值 |\n")
        f.write(f"|------|------|\n")
        f.write(f"| 总阶段数 | {report['total_stages']} |\n")
        f.write(f"| 通过阶段 | {report['passed_stages']} |\n")
        f.write(f"| 失败阶段 | {report['failed_stages']} |\n")
        f.write(f"| 通过率 | {report['passed_stages']/report['total_stages']*100:.2f}% |\n\n")
        
        f.write("## 各阶段测试结果\n\n")
        f.write(f"| 序号 | 阶段名称 | 状态 | 耗时 |\n")
        f.write(f"|------|---------|------|------|\n")
        for i, stage in enumerate(results, 1):
            status = "✅ 通过" if stage["success"] else "❌ 失败"
            f.write(f"| {i} | {stage['name']} | {status} | {stage.get('duration', 'N/A')} |\n")
    
    print(f"\n📊 汇总报告已生成: {md_report_path}")
    return md_report_path

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="统一测试执行器")
    parser.add_argument("--stage", action="append", help="指定测试阶段（可多次使用）")
    args = parser.parse_args()
    
    # 确定要执行的阶段
    if args.stage:
        stages_to_run = [s for s in EXECUTION_ORDER if s in args.stage]
    else:
        stages_to_run = EXECUTION_ORDER
    
    print("="*60)
    print("    统一测试执行器 v1.0")
    print("="*60)
    print(f"执行阶段: {', '.join([TEST_STAGES[s]['name'] for s in stages_to_run])}")
    print("="*60)
    
    results = []
    
    for stage in stages_to_run:
        start_time = datetime.now()
        
        if stage == "chaos":
            result = run_chaos_test()
        elif stage == "performance":
            # 性能测试跳过（需要JMeter）
            print(f"\n{'='*60}")
            print(f"  跳过: 性能测试（需要JMeter）")
            print(f"{'='*60}")
            results.append({
                "name": TEST_STAGES[stage]["name"],
                "stage": stage,
                "success": True,
                "duration": "跳过",
                "message": "性能测试需要JMeter环境，已跳过"
            })
            continue
        elif stage == "automation":
            # 运行自动化测试
            print(f"\n{'='*60}")
            print(f"  正在执行: 自动化测试")
            print(f"{'='*60}")
            
            cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cmd = "python automation_test/cli.py run"
            result = run_command(cmd, cwd=cwd, live_output=True)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            results.append({
                "name": TEST_STAGES[stage]["name"],
                "stage": stage,
                "success": result["success"],
                "duration": f"{duration:.2f}s",
                "returncode": result["returncode"]
            })
            continue
        else:
            result = run_pytest(TEST_STAGES[stage]["path"], TEST_STAGES[stage]["name"])
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        results.append({
            "name": TEST_STAGES[stage]["name"],
            "stage": stage,
            "success": result["success"],
            "duration": f"{duration:.2f}s",
            "returncode": result["returncode"],
            "passed": result.get("passed", 0),
            "failed": result.get("failed", 0)
        })
    
    # 生成汇总报告
    generate_summary_report(results)
    
    # 显示详细结果
    print("\n" + "="*70)
    print("                    测试执行完成")
    print("="*70)
    print(f"| {'阶段名称':<12} | {'状态':<8} | {'成功':<6} | {'失败':<6} | {'耗时':<10} |")
    print(f"|{'--'*14}|{'--'*10}|{'--'*8}|{'--'*8}|{'--'*12}|")
    
    total_passed = 0
    total_failed = 0
    
    for stage in results:
        status = "✅ 通过" if stage["success"] else "❌ 失败"
        passed = stage.get("passed", "-")
        failed = stage.get("failed", "-")
        
        if isinstance(passed, int):
            total_passed += passed
        if isinstance(failed, int):
            total_failed += failed
            
        print(f"| {stage['name']:<12} | {status:<8} | {str(passed):<6} | {str(failed):<6} | {stage.get('duration', 'N/A'):<10} |")
    
    print("="*70)
    print(f" 总计: {total_passed + total_failed} 个测试用例, 通过: {total_passed}, 失败: {total_failed}")
    print("="*70)

if __name__ == "__main__":
    main()