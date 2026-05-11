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

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config import TEST_STAGES, EXECUTION_ORDER, REPORTS_DIR, ALLURE_RESULTS_DIR, ALLURE_REPORT_DIR

# 邮件配置 - 从外部配置文件读取
try:
    from email_config import EMAIL_CONFIG
except ImportError:
    # 如果配置文件不存在，使用默认占位符
    EMAIL_CONFIG = {
        "smtp_server": "smtp.qq.com",
        "smtp_port": 465,
        "sender": "your_email@qq.com",
        "password": "your_smtp_password",
        "recipient": "recipient@example.com",
        "subject": "学生管理系统测试报告"
    }
    print("⚠️ 未找到 email_config.py，使用默认配置。请复制 email_config.py.example 并配置实际邮箱信息。")

FLASK_PROCESS = None

def run_command(cmd, cwd=None, live_output=False):
    """执行命令并返回结果"""
    try:
        if live_output:
            # 实时输出模式 - 同时保存输出以便解析
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
            # 实时打印输出
            print(result.stdout)
            if result.stderr:
                print("错误信息:", result.stderr)
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
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


def send_email_report(report_path, results=None):
    """发送测试报告邮件（包含详细HTML内容）"""
    print("\n" + "="*60)
    print("  正在发送测试报告邮件...")
    print("="*60)
    
    try:
        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG["sender"]
        msg['To'] = EMAIL_CONFIG["recipient"]
        msg['Subject'] = Header(EMAIL_CONFIG["subject"], 'utf-8')
        
        # 计算统计数据
        if results:
            total_tests = sum(r.get('passed', 0) + r.get('failed', 0) for r in results)
            total_passed = sum(r.get('passed', 0) for r in results)
            total_failed = sum(r.get('failed', 0) for r in results)
            pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
            
            # 获取测试时间范围（第一条用例开始时间，最后一条用例结束时间）
            test_start_time = results[0].get('start_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            test_end_time = results[-1].get('end_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        else:
            total_tests = total_passed = total_failed = 0
            pass_rate = 0
            test_start_time = test_end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 计算各阶段用例占比（用于饼图）
        stage_percentages = []
        stage_success_percentages = []
        stage_failed_percentages = []
        
        for stage in results:
            stage_tests = stage.get('passed', 0) + stage.get('failed', 0)
            stage_passed = stage.get('passed', 0)
            stage_failed = stage.get('failed', 0)
            
            # 总用例占比
            if total_tests > 0:
                percentage = (stage_tests / total_tests) * 100
                success_percentage = (stage_passed / total_tests) * 100
                failed_percentage = (stage_failed / total_tests) * 100 if total_failed > 0 else 0
            else:
                percentage = success_percentage = failed_percentage = 0
            
            stage_percentages.append({
                'name': stage.get('name', 'N/A'),
                'percentage': percentage,
                'tests': stage_tests
            })
            
            stage_success_percentages.append({
                'name': stage.get('name', 'N/A'),
                'percentage': success_percentage,
                'passed': stage_passed
            })
            
            stage_failed_percentages.append({
                'name': stage.get('name', 'N/A'),
                'percentage': failed_percentage,
                'failed': stage_failed
            })
        
        # 失败率
        fail_rate = (total_failed / total_tests * 100) if total_tests > 0 else 0
        
        # 生成饼图颜色
        colors = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#f44336', '#E91E63', '#00BCD4']
        
        # 邮件正文 - 参考自动化测试报告样式
        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
                h2 {{ color: #666; margin-top: 20px; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .passed {{ color: green; font-weight: bold; }}
                .failed {{ color: red; font-weight: bold; }}
                .summary {{ display: flex; justify-content: space-between; align-items: center; }}
                .pie-container {{ display: flex; gap: 30px; align-items: center; flex-wrap: wrap; }}
                .pie-chart {{ width: 120px; height: 120px; border-radius: 50%; position: relative; }}
                .pie-center {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); 
                           background: white; width: 70px; height: 70px; border-radius: 50%; 
                           display: flex; flex-direction: column; align-items: center; justify-content: center; }}
                .pie-label {{ font-size: 12px; text-align: center; }}
                .stats-table {{ width: 100%; margin-top: 20px; }}
                .pie-item {{ text-align: center; }}
            </style>
        </head>
        <body>
            <h1>学生管理系统测试报告</h1>
            
            <p><strong>测试开始时间:</strong> {test_start_time}</p>
            <p><strong>测试结束时间:</strong> {test_end_time}</p>
            
            <h2>测试统计</h2>
            <div class="pie-container">
                <div class="pie-item">
                    <div class="pie-chart" style="background: conic-gradient(green {pass_rate}%, red {pass_rate}% 100%);">
                        <div class="pie-center">
                            <div class="pie-label" style="font-size: 18px; font-weight: bold;">{pass_rate:.1f}%</div>
                            <div class="pie-label">通过率</div>
                        </div>
                    </div>
                    <p style="text-align: center; margin-top: 10px; font-size: 14px; color: #666;">测试通过率</p>
                </div>
                <div class="pie-item">
                    <div class="pie-chart" style="background: conic-gradient({','.join([f'{colors[i % len(colors)]} {sum(s["percentage"] for s in stage_success_percentages[:i+1])}%' for i in range(len(stage_success_percentages))])});">
                        <div class="pie-center">
                            <div class="pie-label" style="font-size: 18px; font-weight: bold;">{total_passed}</div>
                            <div class="pie-label">成功数</div>
                        </div>
                    </div>
                    <p style="text-align: center; margin-top: 10px; font-size: 14px; color: #666;">各阶段成功占比</p>
                </div>
                <div class="pie-item">
                    <div class="pie-chart" style="background: conic-gradient(red {fail_rate}%, #f0f0f0 {fail_rate}% 100%);">
                        <div class="pie-center">
                            <div class="pie-label" style="font-size: 18px; font-weight: bold;">{total_failed}</div>
                            <div class="pie-label">失败数</div>
                        </div>
                    </div>
                    <p style="text-align: center; margin-top: 10px; font-size: 14px; color: #666;">失败占比 {fail_rate:.1f}%</p>
                </div>
            </div>
            
            <table class="stats-table">
                <tr><th>总用例数</th><th>失败</th><th>通过</th><th>通过率</th><th>失败率</th></tr>
                <tr>
                    <td style="text-align: center; font-size: 18px;">{total_tests}</td>
                    <td style="text-align: center; font-size: 18px; color: red;">{total_failed}</td>
                    <td style="text-align: center; font-size: 18px; color: green;">{total_passed}</td>
                    <td style="text-align: center; font-size: 18px; color: green;">{pass_rate:.1f}%</td>
                    <td style="text-align: center; font-size: 18px; color: red;">{fail_rate:.1f}%</td>
                </tr>
            </table>
            
            <h2>各阶段测试详情</h2>
            <table style="width: 100%;">
                <tr><th>阶段名称</th><th>用例数</th><th>成功数</th><th>失败数</th><th>成功率</th><th>颜色</th></tr>
        """
        
        for i, stage in enumerate(stage_success_percentages):
            passed = stage['passed']
            failed = stage_failed_percentages[i]['failed']
            total = passed + failed
            rate = (passed / total * 100) if total > 0 else 0
            body += f"""
                <tr>
                    <td>{stage['name']}</td>
                    <td style="text-align: center;">{total}</td>
                    <td style="text-align: center; color: green;">{passed}</td>
                    <td style="text-align: center; color: red;">{failed}</td>
                    <td style="text-align: center;">{rate:.1f}%</td>
                    <td><div style="width: 20px; height: 20px; background-color: {colors[i % len(colors)]}; border-radius: 4px; margin: 0 auto;"></div></td>
                </tr>
                """
        
        body += """
            </table>
            
            <h2>各阶段时间详情</h2>
            <table>
                <tr>
                    <th>序号</th>
                    <th>阶段名称</th>
                    <th>开始时间</th>
                    <th>结束时间</th>
                    <th>耗时</th>
                    <th>通过</th>
                    <th>失败</th>
                    <th>状态</th>
                </tr>
        """
        
        if results:
            for i, stage in enumerate(results, 1):
                status = "✅ 通过" if stage.get('success', False) else "❌ 失败"
                status_class = "passed" if stage.get('success', False) else "failed"
                body += f"""
                <tr>
                    <td>{i}</td>
                    <td>{stage.get('name', 'N/A')}</td>
                    <td>{stage.get('start_time', 'N/A')}</td>
                    <td>{stage.get('end_time', 'N/A')}</td>
                    <td>{stage.get('duration', 'N/A')}</td>
                    <td>{stage.get('passed', 0)}</td>
                    <td>{stage.get('failed', 0)}</td>
                    <td class="{status_class}">{status}</td>
                </tr>
                """
        
        body += """
            </table>
            
            <p style="margin-top: 20px; color: #666; font-size: 12px;">
                详细报告请查看附件。
            </p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html', 'utf-8'))
        
        # 添加附件
        if os.path.exists(report_path):
            with open(report_path, 'rb') as f:
                attachment = MIMEApplication(f.read())
                attachment.add_header('Content-Disposition', 'attachment', 
                                    filename=os.path.basename(report_path))
                msg.attach(attachment)
        
        # 发送邮件（添加调试信息和重试机制）
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                print(f"  正在连接SMTP服务器: {EMAIL_CONFIG['smtp_server']}:{EMAIL_CONFIG['smtp_port']}")
                server = smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"])
                server.set_debuglevel(1)  # 启用调试模式
                
                print(f"  正在登录: {EMAIL_CONFIG['sender']}")
                server.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])
                
                print(f"  正在发送邮件到: {EMAIL_CONFIG['recipient']}")
                server.sendmail(EMAIL_CONFIG["sender"], EMAIL_CONFIG["recipient"], msg.as_string())
                server.quit()
                
                print(f"✅ 邮件已成功发送至: {EMAIL_CONFIG['recipient']}")
                return True
            except smtplib.SMTPAuthenticationError as e:
                print(f"❌ SMTP认证失败: {e}")
                print(f"  请检查邮箱授权码是否正确")
                return False
            except smtplib.SMTPException as e:
                retry_count += 1
                print(f"⚠️ SMTP错误 (尝试 {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    print("  等待2秒后重试...")
                    time.sleep(2)
                else:
                    print(f"❌ 邮件发送失败，已达到最大重试次数")
                    return False
            except Exception as e:
                print(f"❌ 邮件发送失败: {e}")
                print(f"  错误类型: {type(e).__name__}")
                import traceback
                traceback.print_exc()
                return False
        
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        print(f"  错误类型: {type(e).__name__}")
        import traceback
        traceback.print_exc()
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
            # 从混沌测试输出中解析测试结果
            passed = 0
            failed = 0
            if result["stdout"]:
                # 解析混沌测试输出
                if "成功请求" in result["stdout"]:
                    import re
                    success_match = re.search(r'成功请求:\s*(\d+)', result["stdout"])
                    failed_match = re.search(r'失败请求:\s*(\d+)', result["stdout"])
                    if success_match:
                        passed = int(success_match.group(1))
                    if failed_match:
                        failed = int(failed_match.group(1))
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            results.append({
                "name": TEST_STAGES[stage]["name"],
                "stage": stage,
                "success": result["success"],
                "duration": f"{duration:.2f}s",
                "returncode": result["returncode"],
                "passed": passed,
                "failed": failed,
                "start_time": start_time.strftime('%Y-%m-%d %H:%M:%S'),
                "end_time": end_time.strftime('%Y-%m-%d %H:%M:%S')
            })
            continue
        elif stage == "performance":
            # 性能测试跳过（需要JMeter）
            print(f"\n{'='*60}")
            print(f"  跳过: 性能测试（需要JMeter）")
            print(f"{'='*60}")
            end_time = datetime.now()
            results.append({
                "name": TEST_STAGES[stage]["name"],
                "stage": stage,
                "success": True,
                "duration": "跳过",
                "passed": 0,
                "failed": 0,
                "message": "性能测试需要JMeter环境，已跳过",
                "start_time": start_time.strftime('%Y-%m-%d %H:%M:%S'),
                "end_time": end_time.strftime('%Y-%m-%d %H:%M:%S')
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
            
            # 从自动化测试输出中解析测试结果
            passed = 0
            failed = 0
            if result["stdout"]:
                import re
                # 解析自动化测试输出中的通过/失败数量
                pass_match = re.search(r'通过:\s*(\d+)', result["stdout"])
                fail_match = re.search(r'失败:\s*(\d+)', result["stdout"])
                if pass_match:
                    passed = int(pass_match.group(1))
                if fail_match:
                    failed = int(fail_match.group(1))
            
            results.append({
                "name": TEST_STAGES[stage]["name"],
                "stage": stage,
                "success": result["success"],
                "duration": f"{duration:.2f}s",
                "returncode": result["returncode"],
                "passed": passed,
                "failed": failed,
                "start_time": start_time.strftime('%Y-%m-%d %H:%M:%S'),
                "end_time": end_time.strftime('%Y-%m-%d %H:%M:%S')
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
            "failed": result.get("failed", 0),
            "start_time": start_time.strftime('%Y-%m-%d %H:%M:%S'),
            "end_time": end_time.strftime('%Y-%m-%d %H:%M:%S')
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
        send_email_report(report_path, results)

if __name__ == "__main__":
    main()