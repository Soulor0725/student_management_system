#!/usr/bin/env python3
"""统一测试执行器 - 一键执行所有测试并生成Allure风格报告"""

import argparse
import subprocess
import os
import sys
import json
import time
import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.header import Header
from datetime import datetime
from config import TEST_STAGES, EXECUTION_ORDER, REPORTS_DIR, ALLURE_RESULTS_DIR, ALLURE_REPORT_DIR

# 邮件配置
EMAIL_CONFIG = {
    "smtp_server": "smtp.qq.com",
    "smtp_port": 465,
    "sender": "249379218@qq.com",
    "password": "afnimcejgiygbhij",
    "recipient": "249379218@qq.com",
    "subject": "学生管理系统测试报告"
}

FLASK_PROCESS = None

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
    cmd = f"python -m pytest {test_path} -v --tb=short -s"
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


def is_port_in_use(port):
    """检查指定端口是否被占用"""
    try:
        with requests.get(f"http://localhost:{port}/login", timeout=2):
            return True
    except requests.exceptions.RequestException:
        return False


def kill_process_on_port(port):
    """杀掉占用指定端口的进程"""
    print(f"  正在查找并杀掉占用端口 {port} 的进程...")
    
    if sys.platform == "win32":
        # Windows系统使用netstat和taskkill
        try:
            # 获取占用端口的进程ID
            result = subprocess.run(
                ["netstat", "-ano", "|", "findstr", f":{port}"],
                capture_output=True,
                text=True,
                shell=True
            )
            if result.stdout:
                # 解析进程ID
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        print(f"    找到进程 PID: {pid}")
                        # 杀掉进程
                        subprocess.run(
                            ["taskkill", "/F", "/PID", pid],
                            capture_output=True
                        )
                        print(f"    已杀掉进程 PID: {pid}")
                        time.sleep(1)
        except Exception as e:
            print(f"    查找进程失败: {e}")
    else:
        # Linux/macOS系统使用lsof和kill
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True
            )
            if result.stdout:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        print(f"    找到进程 PID: {pid}")
                        subprocess.run(["kill", "-9", pid])
                        print(f"    已杀掉进程 PID: {pid}")
                        time.sleep(1)
        except Exception as e:
            print(f"    查找进程失败: {e}")


def start_flask_app():
    """启动Flask应用（包含状态检测和强制重启）"""
    global FLASK_PROCESS
    PORT = 5000
    
    print("\n" + "="*60)
    print("  应用状态检测与启动")
    print("="*60)
    
    # 检查应用是否已启动
    if is_port_in_use(PORT):
        print(f"  ⚠️ 检测到端口 {PORT} 已被占用，应用可能已启动")
        print("  正在强制关闭现有进程...")
        kill_process_on_port(PORT)
        time.sleep(2)
    
    # 启动Flask应用
    print("\n  正在启动 Flask 应用...")
    cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    if sys.platform == "win32":
        FLASK_PROCESS = subprocess.Popen(
            ["python", "app.py"],
            cwd=cwd,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        FLASK_PROCESS = subprocess.Popen(
            ["python", "app.py"],
            cwd=cwd,
            preexec_fn=os.setsid
        )
    
    # 等待应用启动
    print("  等待应用启动 (5秒)...")
    time.sleep(5)
    
    # 检查应用是否成功启动
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            response = requests.get(f"http://localhost:{PORT}/login", timeout=5)
            if response.status_code == 200:
                print("  ✅ Flask 应用启动成功！")
                return True
        except Exception as e:
            retry_count += 1
            print(f"  ⚠️ 应用启动检查失败 ({retry_count}/{max_retries}): {e}")
            if retry_count < max_retries:
                print("  等待2秒后重试...")
                time.sleep(2)
    
    print("  ❌ 应用启动失败，请检查应用配置")
    return False


def stop_flask_app():
    """停止Flask应用"""
    global FLASK_PROCESS
    print("\n" + "="*60)
    print("  正在停止 Flask 应用...")
    print("="*60)
    
    if FLASK_PROCESS:
        try:
            if sys.platform == "win32":
                FLASK_PROCESS.terminate()
            else:
                os.killpg(os.getpgid(FLASK_PROCESS.pid), 9)
            print("✅ Flask 应用已停止")
        except Exception as e:
            print(f"⚠️ 停止应用时出错: {e}")
    else:
        print("⚠️ 没有找到运行的Flask进程")


def send_email_report(report_path):
    """发送测试报告邮件"""
    print("\n" + "="*60)
    print("  正在发送测试报告邮件...")
    print("="*60)
    
    try:
        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG["sender"]
        msg['To'] = EMAIL_CONFIG["recipient"]
        msg['Subject'] = Header(EMAIL_CONFIG["subject"], 'utf-8')
        
        # 邮件正文
        body = f"""
        <h2>学生管理系统测试报告</h2>
        <p>测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>详细报告请查看附件。</p>
        """
        msg.attach(MIMEText(body, 'html', 'utf-8'))
        
        # 添加附件
        if os.path.exists(report_path):
            with open(report_path, 'rb') as f:
                attachment = MIMEApplication(f.read())
                attachment.add_header('Content-Disposition', 'attachment', 
                                    filename=os.path.basename(report_path))
                msg.attach(attachment)
        
        # 发送邮件
        server = smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"])
        server.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])
        server.sendmail(EMAIL_CONFIG["sender"], EMAIL_CONFIG["recipient"], msg.as_string())
        server.quit()
        
        print(f"✅ 邮件已发送至: {EMAIL_CONFIG['recipient']}")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False

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
    parser.add_argument("--no-start-server", action="store_true", help="不自动启动Flask应用")
    parser.add_argument("--no-stop-server", action="store_true", help="测试完成后不停止Flask应用")
    parser.add_argument("--no-email", action="store_true", help="不发送邮件报告")
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
    
    # 启动Flask应用
    if not args.no_start_server:
        start_flask_app()
    
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
    
    # 生成报告路径
    report_path = os.path.join(REPORTS_DIR, f"test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    
    # 停止Flask应用
    if not args.no_stop_server:
        stop_flask_app()
    
    # 发送邮件报告
    if not args.no_email:
        send_email_report(report_path)

if __name__ == "__main__":
    main()