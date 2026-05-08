from pathlib import Path
import hashlib
import sqlite3
import time
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.header import Header
from datetime import datetime, timedelta

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


BASE_URL = "http://127.0.0.1:5000"
LOGIN_URL = f"{BASE_URL}/login"
REGISTER_URL = f"{BASE_URL}/register"
USERNAME = "soulor"
PASSWORD = "root123"
REGISTER_USERNAME = "root"
REGISTER_PASSWORD = "root123"

STUDENT_NAME = "浪子"
STUDENT_AGE = "29"
STUDENT_CLASS = "21131"
STEP_WAIT_MS = 1200
DB_FILE = Path(__file__).resolve().parent.parent / "student_management" / "data" / "student_management.db"

# 邮件配置
EMAIL_CONFIG = {
    "smtp_server": "smtp.qq.com",
    "smtp_port": 465,
    "sender": "249379218@qq.com",  # 发件人QQ邮箱
    "password": "afnimcejgiygbhij",  # QQ邮箱SMTP授权码
    "recipient": "249379218@qq.com",  # 收件人邮箱
    "subject": "自动化测试报告"
}


def cleanup_old_screenshots(hours=1):
    """清理超过指定小时的截图文件"""
    output_dir = Path("output")
    if not output_dir.exists():
        return
    
    cutoff_time = datetime.now() - timedelta(hours=hours)
    removed_count = 0
    
    for screenshot in output_dir.glob("*.png"):
        if screenshot.stat().st_mtime < cutoff_time.timestamp():
            screenshot.unlink()
            removed_count += 1
    
    if removed_count > 0:
        print(f"[CLEANUP] 已清理 {removed_count} 个超过{hours}小时的截图")


def save_screenshot(page, case_name):
    """保存截图到output目录"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    screenshot_path = Path("output") / f"{case_name}_{timestamp}.png"
    Path("output").mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(screenshot_path), full_page=True)
    print(f"[截图已保存] {screenshot_path}")
    return screenshot_path


def assert_login_success(page) -> None:
    page.wait_for_selector("text=当前用户：soulor", timeout=5000)
    print("[ASSERT PASS] 登录成功，页面显示当前用户 soulor")


def assert_student_added(page) -> None:
    student_row = page.locator(
        f"tr:has(td:text-is('{STUDENT_NAME}')):has(td:text-is('{STUDENT_AGE}')):has(td:text-is('{STUDENT_CLASS}'))"
    ).first
    student_row.wait_for(state="visible", timeout=5000)
    print(f"[ASSERT PASS] 新增学生成功：{STUDENT_NAME} / {STUDENT_AGE} / {STUDENT_CLASS}")


def generate_terminal_report(results: list) -> None:
    """生成终端风格的 Allure 报告"""
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    pass_rate = (passed / total * 100) if total > 0 else 0
    
    report_start_time = results[0]["start_time"] if results else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_end_time = results[-1]["end_time"] if results else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print("\n")
    print("=" * 70)
    print("                        📊 自动化测试报告")
    print("=" * 70)
    print(f"  执行开始时间：{report_start_time}")
    print(f"  执行结束时间：{report_end_time}")
    print("-" * 70)
    
    print("\n  ┌─────────────────────────────────────────────────────────────────┐")
    print("  │                         📈 测试统计                              │")
    print("  └─────────────────────────────────────────────────────────────────┘")
    
    print(f"""
  ╔═══════════════════════════════════════════════════════════════════════╗
  ║                                                                       ║
  ║     总用例数        通过           失败           通过率                  ║
  ║                                                                       ║
  ║       {total:>2}            {passed:>2}            {failed:>2}           {pass_rate:>5.1f}%                 ║
  ║                                                                       ║
  ╚═══════════════════════════════════════════════════════════════════════╝
    """)
    
    print("  ┌─────────────────────────────────────────────────────────────────┐")
    print("  │                         🥧 用例占比饼图                           │")
    print("  └─────────────────────────────────────────────────────────────────┘")
    
    case_rate = 100 / total if total > 0 else 0
    
    pie_chart = """
  ╔═══════════════════════════════════════════════════════════════════╗
  ║                                                                   ║"""
    
    for i, r in enumerate(results, 1):
        case_angle = case_rate * 3.6
        pie_chart += f"""
  ║    用例{i}  {r['name']:<10}  ████████████████████████████ {case_rate:>5.1f}%  ║
  ║                         ({i}/3)                                  ║"""
    
    pie_chart += """
  ║                                                                   ║
  ╚═══════════════════════════════════════════════════════════════════╝
    """
    
    print(pie_chart)
    
    bar_length = 40
    pass_bar = int(bar_length * passed / total) if total > 0 else 0
    fail_bar = bar_length - pass_bar
    
    print("""
  ┌─────────────────────────────────────────────────────────────────┐
  │                       📊 通过率统计                               │
  └─────────────────────────────────────────────────────────────────┘
    """)
    
    print(f"""
        ┌──────────────────────────────────────────┐
        │                                          │
        │    绿色(通过)  {"█" * pass_bar:<40} {pass_rate:>5.1f}%     │
        │                  {passed:>2} 条                        │
        │                                          │
        │    红色(失败)  {"█" * fail_bar:<40} {100-pass_rate:>5.1f}%     │
        │                  {failed:>2} 条                        │
        │                                          │
        └──────────────────────────────────────────┘
    """)
    
    print("  ┌─────────────────────────────────────────────────────────────────┐")
    print("  │                         📋 用例详情                              │")
    print("  └─────────────────────────────────────────────────────────────────┘")
    
    for i, r in enumerate(results, 1):
        status = "✅ 通过" if r["passed"] else "❌ 失败"
        status_color = "\033[92m" if r["passed"] else "\033[91m"
        reset = "\033[0m"
        
        print(f"""
  {i}. {r['name']}
     开始时间: {r['start_time']}
     结束时间: {r['end_time']}
     耗时: {r['duration']:.2f}s
     状态: {status_color}{status}{reset}
        """)
    
    print("=" * 70)
    print("                    测试报告生成完毕")
    print("=" * 70 + "\n")


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def cleanup_existing_user(username: str) -> None:
    with sqlite3.connect(DB_FILE) as conn:
        row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if row:
            conn.execute("DELETE FROM users WHERE username = ?", (username,))
            conn.commit()
            print(f"[CLEANUP] 已删除历史账号: {username}")
        else:
            print(f"[CLEANUP] 账号不存在，无需删除: {username}")


def assert_user_exists_in_db(username: str, password: str) -> None:
    with sqlite3.connect(DB_FILE) as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE username = ? AND password = ?",
            (username, hash_password(password)),
        ).fetchone()
    if not row:
        raise AssertionError(f"注册断言失败：数据库未找到账号 {username}")
    print(f"[ASSERT PASS] 注册成功，数据库已存在账号: {username}")


# ==================== 测试用例1：注册功能 ====================
def test_register_case(page) -> bool:
    """测试用例1：注册功能"""
    print("\n" + "="*50)
    print("【用例1】注册功能测试")
    print("="*50)
    
    try:
        cleanup_existing_user(REGISTER_USERNAME)
        page.goto(REGISTER_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(STEP_WAIT_MS)
        
        # 强制刷新页面，清除可能的缓存错误信息
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(STEP_WAIT_MS)
        
        print(f"[DEBUG] 注册页面 URL: {page.url}")
        print(f"[DEBUG] 注册页面标题: {page.title()}")
        
        # 检查页面是否有错误信息
        try:
            error_element = page.locator(".error-text")
            if error_element.count() > 0:
                error_text = error_element.text_content()
                print(f"[DEBUG] 页面存在错误信息: {error_text}")
        except:
            print("[DEBUG] 页面没有错误信息")
        
        page.fill("#username", REGISTER_USERNAME)
        page.wait_for_timeout(STEP_WAIT_MS)
        page.fill("#password", REGISTER_PASSWORD)
        page.wait_for_timeout(STEP_WAIT_MS)
        
        # 点击注册按钮
        print("[DEBUG] 准备点击注册按钮")
        
        # 监听网络请求
        def handle_response(response):
            if response.url.endswith("/register") and response.status == 200:
                print(f"[DEBUG] 注册请求已发送: {response.url}, 状态码: {response.status}")
        
        page.on("response", handle_response)
        
        page.click("button[type='submit']")
        print("[DEBUG] 已点击注册按钮")
        page.wait_for_timeout(3000)
        
        # 停止监听网络请求
        page.remove_listener("response", handle_response)
        
        # 等待页面加载完成
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(STEP_WAIT_MS)
        
        # 打印当前页面的 URL 和标题，用于调试
        print(f"[DEBUG] 注册后页面 URL: {page.url}")
        print(f"[DEBUG] 注册后页面标题: {page.title()}")
        
        # 尝试获取当前页面的 h2 元素文本
        try:
            h2_element = page.locator("h2").first
            h2_text = h2_element.text_content()
            print(f"[DEBUG] 注册后页面 h2 文本: {h2_text}")
        except Exception as e:
            print(f"[DEBUG] 获取 h2 元素失败: {e}")
        
        # 检查是否跳转到登录页
        if "login" not in page.url.lower():
            print("[DEBUG] 未跳转到登录页，尝试检查页面内容")
            try:
                error_text = page.locator(".error-text").text_content()
                print(f"[DEBUG] 页面错误信息: {error_text}")
            except:
                print("[DEBUG] 没有错误信息")
        else:
            print("[DEBUG] 已跳转到登录页")
        
        # 验证用户是否在数据库中
        print(f"[DEBUG] 开始验证数据库中是否存在用户: {REGISTER_USERNAME}")
        assert_user_exists_in_db(REGISTER_USERNAME, REGISTER_PASSWORD)
        
        save_screenshot(page, "用例1_注册功能")
        print("【用例1】注册功能测试 - 通过")
        return True
        
    except Exception as e:
        print(f"【用例1】注册功能测试 - 失败: {e}")
        save_screenshot(page, "用例1_注册功能")
        return False


# ==================== 测试用例2：登录功能 ====================
def test_login_case(page) -> bool:
    """测试用例2：登录功能"""
    print("\n" + "="*50)
    print("【用例2】登录功能测试")
    print("="*50)
    
    try:
        page.goto(LOGIN_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(STEP_WAIT_MS)
        
        page.fill("#username", USERNAME)
        page.wait_for_timeout(STEP_WAIT_MS)
        page.fill("#password", PASSWORD)
        page.wait_for_timeout(STEP_WAIT_MS)
        page.click("button[type='submit']")
        page.wait_for_timeout(STEP_WAIT_MS)
        
        # 验证登录成功
        page.wait_for_selector("text=当前用户：soulor", timeout=5000)
        print("[ASSERT PASS] 登录成功，页面显示当前用户 soulor")
        
        save_screenshot(page, "用例2_登录功能")
        print("【用例2】登录功能测试 - 通过")
        return True
        
    except Exception as e:
        print(f"【用例2】登录功能测试 - 失败: {e}")
        save_screenshot(page, "用例2_登录功能")
        return False


# ==================== 测试用例3：添加学生功能 ====================
def test_add_student_case(page) -> bool:
    """测试用例3：添加学生功能"""
    print("\n" + "="*50)
    print("【用例3】添加学生功能测试")
    print("="*50)
    
    try:
        # 清理现有的学生
        row_selector = (
            f"tr:has(td:text-is('{STUDENT_NAME}')):has(td:text-is('{STUDENT_AGE}')):has(td:text-is('{STUDENT_CLASS}'))"
        )
        removed_count = 0
        while page.locator(row_selector).count() > 0:
            row = page.locator(row_selector).first
            row.locator("button.danger").click()
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(STEP_WAIT_MS)
            removed_count += 1
        
        if removed_count > 0:
            print(f"[CLEANUP] 已删除历史重复学生 {removed_count} 条")
        else:
            print("[CLEANUP] 无历史重复学生，无需删除")
        
        # 添加新学生
        page.fill("#name", STUDENT_NAME)
        page.wait_for_timeout(STEP_WAIT_MS)
        page.fill("#age", STUDENT_AGE)
        page.wait_for_timeout(STEP_WAIT_MS)
        page.fill("#class_name", STUDENT_CLASS)
        page.wait_for_timeout(STEP_WAIT_MS)
        page.click("button:has-text('添加学生')")
        page.wait_for_timeout(STEP_WAIT_MS)
        
        # 验证学生添加成功
        student_row = page.locator(
            f"tr:has(td:text-is('{STUDENT_NAME}')):has(td:text-is('{STUDENT_AGE}')):has(td:text-is('{STUDENT_CLASS}'))"
        ).first
        student_row.wait_for(state="visible", timeout=5000)
        print(f"[ASSERT PASS] 新增学生成功：{STUDENT_NAME} / {STUDENT_AGE} / {STUDENT_CLASS}")
        
        save_screenshot(page, "用例3_添加学生功能")
        
        # 退出登录
        try:
            page.click("a:has-text('退出登录')")
            page.wait_for_timeout(STEP_WAIT_MS)
            page.wait_for_load_state("domcontentloaded")
            print("[DEBUG] 已退出登录")
        except:
            print("[DEBUG] 退出登录失败")
        
        print("【用例3】添加学生功能测试 - 通过")
        return True
        
    except Exception as e:
        print(f"【用例3】添加学生功能测试 - 失败: {e}")
        save_screenshot(page, "用例3_添加学生功能")
        return False


# ==================== 测试用例4：登录失败测试 ====================
def test_login_fail_case(page) -> bool:
    """测试用例4：登录失败 - 用户名root1，密码空"""
    print("\n" + "="*50)
    print("【用例4】登录失败测试")
    print("="*50)
    
    try:
        # 先尝试退出登录（处理可能的登录状态）
        try:
            # 查找退出按钮
            logout_buttons = page.locator("a, button").filter(has_text=re.compile(r'退出|登出', re.IGNORECASE))
            if logout_buttons.count() > 0:
                logout_buttons.first.click()
                page.wait_for_timeout(STEP_WAIT_MS)
                page.wait_for_load_state("domcontentloaded")
                print("[DEBUG] 已退出登录")
            else:
                print("[DEBUG] 未找到退出按钮")
        except Exception as e:
            print(f"[DEBUG] 退出登录失败: {e}")
        
        # 直接导航到登录页面
        page.goto(LOGIN_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(STEP_WAIT_MS * 2)
        
        # 检查当前页面
        print(f"[DEBUG] 当前页面 URL: {page.url}")
        print(f"[DEBUG] 当前页面标题: {page.title()}")
        
        # 如果不在登录页面，强制访问登录页
        if "login" not in page.url.lower():
            print("[DEBUG] 不在登录页，强制访问登录页")
            page.goto(LOGIN_URL, wait_until="domcontentloaded")
            page.wait_for_timeout(STEP_WAIT_MS * 2)
        
        # 等待登录表单出现
        page.wait_for_selector("h2", timeout=10000)
        h2_text = page.locator("h2").first.text_content()
        print(f"[DEBUG] 页面h2内容: {h2_text}")
        
        # 等待用户名输入框出现
        page.wait_for_selector("input[type='text'], #username", timeout=10000)
        
        # 输入用户名root1，密码为空
        page.fill("#username", "root1")
        page.wait_for_timeout(STEP_WAIT_MS)
        page.fill("#password", "")
        page.wait_for_timeout(STEP_WAIT_MS)
        page.click("button[type='submit']")
        page.wait_for_timeout(STEP_WAIT_MS)
        
        # 错误断言：期望登录成功（但实际会失败，所以这里会抛出异常）
        page.wait_for_selector("text=当前用户：root1", timeout=5000)
        print("[ASSERT PASS] 登录成功，页面显示当前用户 root1")
        
        save_screenshot(page, "用例4_登录失败")
        print("【用例4】登录失败测试 - 通过")
        return True
        
    except Exception as e:
        print(f"【用例4】登录失败测试 - 失败: {e}")
        save_screenshot(page, "用例4_登录失败")
        return False


def main() -> None:
    """主函数"""
    print("\n" + "="*60)
    print("学生管理系统自动化测试开始")
    print("="*60)
    
    cleanup_old_screenshots(hours=1)
    
    with sync_playwright() as p:
        # 启动浏览器，使用最大化参数
        browser = p.chromium.launch(
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            headless=False,
            slow_mo=400,
            args=["--start-maximized"]
        )
        
        # 创建页面
        page = browser.new_page()
        
        # 等待页面完全加载
        page.wait_for_load_state("networkidle")
        
        # 执行4个测试用例
        results = []
        
        for case_name, test_func in [
            ("用例1：注册功能", test_register_case),
            ("用例2：登录功能", test_login_case),
            ("用例3：添加学生功能", test_add_student_case),
            ("用例4：登录失败", test_login_fail_case),
        ]:
            start_time = datetime.now()
            result = test_func(page)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # 查找该用例的截图
            screenshots = []
            output_dir = Path("output")
            case_key = case_name.replace("：", "_")
            for screenshot in output_dir.glob(f"{case_key}*.png"):
                if screenshot.stat().st_mtime >= start_time.timestamp() - 60:
                    screenshots.append(str(screenshot))
            
            results.append({
                "name": case_name,
                "passed": result,
                "duration": duration,
                "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
                "screenshots": screenshots
            })
        
        # 关闭浏览器
        print("\n" + "="*60)
        print("自动化执行完成，3秒后关闭浏览器")
        print("="*60)
        page.wait_for_timeout(3000)
        browser.close()
        
        generate_html_report(results)


def generate_html_report(results: list) -> None:
    """生成 Allure 风格的 HTML 测试报告"""
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    pass_rate = (passed / total * 100) if total > 0 else 0
    fail_rate = (failed / total * 100) if total > 0 else 0
    case_rate = 100 / total if total > 0 else 0
    
    report_start_time = results[0]["start_time"] if results else ""
    report_end_time = results[-1]["end_time"] if results else ""
    total_duration = sum(r["duration"] for r in results)
    
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Allure 自动化测试报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            padding: 30px;
            color: #fff;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .header {{
            text-align: center;
            padding: 30px 0;
            border-bottom: 2px solid rgba(255,255,255,0.1);
            margin-bottom: 30px;
        }}
        .header h1 {{
            font-size: 2.8em;
            margin-bottom: 15px;
            background: linear-gradient(135deg, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .header-info {{
            display: flex;
            justify-content: center;
            gap: 40px;
            color: #888;
            font-size: 0.95em;
        }}
        .header-info span {{ color: #00d9ff; }}
        
        .card {{
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 25px;
            margin-bottom: 25px;
            border: 1px solid rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
        }}
        .card-title {{
            font-size: 1.3em;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 20px;
        }}
        .stat-box {{
            background: linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0.05));
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .stat-box.passed {{ background: linear-gradient(135deg, #00c853, #00e676); }}
        .stat-box.failed {{ background: linear-gradient(135deg, #ff1744, #ff5252); }}
        .stat-box.duration {{ background: linear-gradient(135deg, #651fff, #b388ff); }}
        .stat-value {{ font-size: 2.5em; font-weight: bold; margin-bottom: 5px; }}
        .stat-label {{ font-size: 0.9em; opacity: 0.8; }}
        
        .charts-container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }}
        
        .pie-chart-wrapper {{
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .pie-chart {{
            width: 220px;
            height: 220px;
            border-radius: 50%;
            background: conic-gradient(
                #00e676 0deg {pass_rate * 3.6}deg,
                #ff1744 {pass_rate * 3.6}deg 360deg
            );
            position: relative;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }}
        .pie-chart::before {{
            content: '';
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            width: 130px; height: 130px;
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            border-radius: 50%;
        }}
        .pie-chart::after {{
            content: '{pass_rate:.1f}%';
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            font-size: 1.8em;
            font-weight: bold;
            color: #fff;
        }}
        .pie-legend {{
            display: flex;
            gap: 30px;
            margin-top: 25px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .legend-dot {{
            width: 14px; height: 14px;
            border-radius: 4px;
        }}
        .legend-dot.passed {{ background: #00e676; }}
        .legend-dot.failed {{ background: #ff1744; }}
        
        .case-chart {{
            padding: 20px;
        }}
        .case-item {{
            margin-bottom: 20px;
        }}
        .case-item-header {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            font-size: 0.95em;
        }}
        .case-item-bar {{
            height: 24px;
            background: rgba(255,255,255,0.1);
            border-radius: 12px;
            overflow: hidden;
            position: relative;
        }}
        .case-item-fill {{
            height: 100%;
            background: linear-gradient(135deg, #00d9ff, #00ff88);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding-right: 10px;
            font-size: 0.85em;
            font-weight: bold;
        }}
        
        .cases-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .cases-table th, .cases-table td {{
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .cases-table th {{
            background: rgba(255,255,255,0.05);
            font-weight: 600;
            color: #00d9ff;
        }}
        .cases-table tr:hover {{
            background: rgba(255,255,255,0.03);
        }}
        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 500;
        }}
        .status-badge.passed {{
            background: rgba(0, 230, 118, 0.2);
            color: #00e676;
        }}
        .status-badge.failed {{
            background: rgba(255, 23, 68, 0.2);
            color: #ff1744;
        }}
        .duration-badge {{
            background: rgba(101, 31, 255, 0.2);
            color: #b388ff;
            padding: 4px 10px;
            border-radius: 8px;
            font-size: 0.85em;
        }}
        
        .footer {{
            text-align: center;
            padding: 30px 0;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Allure 自动化测试报告</h1>
            <div class="header-info">
                <div>执行开始时间：<span>{report_start_time}</span></div>
                <div>执行结束时间：<span>{report_end_time}</span></div>
                <div>总耗时：<span>{total_duration:.2f}s</span></div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-title">📈 测试概览</div>
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="stat-value">{total}</div>
                    <div class="stat-label">总用例数</div>
                </div>
                <div class="stat-box passed">
                    <div class="stat-value">{passed}</div>
                    <div class="stat-label">通过</div>
                </div>
                <div class="stat-box failed">
                    <div class="stat-value">{failed}</div>
                    <div class="stat-label">失败</div>
                </div>
                <div class="stat-box passed">
                    <div class="stat-value">{pass_rate:.1f}%</div>
                    <div class="stat-label">通过率</div>
                </div>
                <div class="stat-box duration">
                    <div class="stat-value">{total_duration:.1f}s</div>
                    <div class="stat-label">总耗时</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-title">📊 用例统计</div>
            <div class="charts-container">
                <div class="pie-chart-wrapper">
                    <div class="pie-chart"></div>
                    <div class="pie-legend">
                        <div class="legend-item">
                            <div class="legend-dot passed"></div>
                            <span>通过 {passed} ({pass_rate:.1f}%)</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-dot failed"></div>
                            <span>失败 {failed} ({fail_rate:.1f}%)</span>
                        </div>
                    </div>
                </div>
                <div class="case-chart">
"""
    
    for i, r in enumerate(results, 1):
        status_color = "#00e676" if r["passed"] else "#ff1744"
        html_content += f"""
                    <div class="case-item">
                        <div class="case-item-header">
                            <span>{r['name']}</span>
                            <span>{case_rate:.1f}%</span>
                        </div>
                        <div class="case-item-bar">
                            <div class="case-item-fill" style="width: {case_rate}%; background: linear-gradient(135deg, {status_color}, {status_color}88);">
                                {r['duration']:.2f}s
                            </div>
                        </div>
                    </div>
"""
    
    html_content += """
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-title">📋 用例详情</div>
            <table class="cases-table">
                <thead>
                    <tr>
                        <th>序号</th>
                        <th>用例名称</th>
                        <th>开始时间</th>
                        <th>结束时间</th>
                        <th>耗时</th>
                        <th>状态</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    for i, r in enumerate(results, 1):
        status_icon = "✅" if r["passed"] else "❌"
        status_text = "通过" if r["passed"] else "失败"
        status_class = "passed" if r["passed"] else "failed"
        
        html_content += f"""
                    <tr>
                        <td>{i}</td>
                        <td>{r['name']}</td>
                        <td>{r['start_time']}</td>
                        <td>{r['end_time']}</td>
                        <td><span class="duration-badge">{r['duration']:.2f}s</span></td>
                        <td><span class="status-badge {status_class}">{status_icon} {status_text}</span></td>
                    </tr>
"""
    
    html_content += """
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>Allure 自动化测试报告 | 学生管理系统</p>
        </div>
    </div>
</body>
</html>"""
    
    report_dir = Path("output")
    report_dir.mkdir(parents=True, exist_ok=True)
    
    # 使用系统名_年月日时分秒命名HTML报告
    system_name = "学生管理系统"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    report_filename = f"{system_name}_{timestamp}.html"
    report_path = report_dir / report_filename
    report_path.write_text(html_content, encoding="utf-8")
    print(f"\n[REPORT] HTML报告已生成: {report_path}")
    
    # 发送邮件
    send_report_email(report_path, results)


def send_report_email(report_path: Path, results: list) -> None:
    """发送测试报告邮件"""
    try:
        print("\n[EMAIL] 准备发送测试报告邮件...")
        
        # 检查邮件配置
        if EMAIL_CONFIG["sender"] == "your_qq_email@qq.com" or EMAIL_CONFIG["password"] == "your_smtp_password":
            print("[EMAIL] 请先配置邮件发送者信息和SMTP授权码")
            return
        
        # 统计测试结果
        total = len(results)
        passed = sum(1 for r in results if r["passed"])
        failed = total - passed
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        # 获取测试开始时间和结束时间
        test_start_time = results[0]["start_time"] if results else ""
        test_end_time = results[-1]["end_time"] if results else ""
        
        # 创建邮件
        msg = MIMEMultipart()
        msg["From"] = EMAIL_CONFIG["sender"]
        msg["To"] = EMAIL_CONFIG["recipient"]
        
        # 邮件标题格式：系统名_自动化测试报告-年月日时分秒
        system_name = "学生管理系统"
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        email_subject = f"{system_name}_自动化测试报告-{timestamp}"
        msg["Subject"] = Header(email_subject, "utf-8")
        
        # 计算饼图角度
        pass_angle = (passed / total * 360) if total > 0 else 0
        
        # 计算SVG路径坐标（使用正确的角度方向）
        import math
        # SVG角度从正x轴开始，顺时针方向
        pass_radians = pass_angle * math.pi / 180
        pass_x = 60 + 50 * math.cos(pass_radians - math.pi/2)  # 调整为从12点钟方向开始
        pass_y = 60 + 50 * math.sin(pass_radians - math.pi/2)
        
        # 构建用例详情表格内容
        case_details = ""
        for i, r in enumerate(results, 1):
            status_icon = "✅" if r["passed"] else "❌"
            status_text = "通过" if r["passed"] else "失败"
            case_details += f"""
            <tr>
                <td>{i}</td>
                <td style="text-align: left;">{r['name']}</td>
                <td>{r['start_time']}</td>
                <td>{r['end_time']}</td>
                <td>{r['duration']:.2f}s</td>
                <td>{status_icon} {status_text}</td>
            </tr>
            """
        
        # 邮件正文
        body = f"""
        <h2>自动化测试报告</h2>
        
        <div style="margin: 20px 0; font-family: Arial, sans-serif; display: flex; justify-content: space-between;">
            <div>测试开始时间：<strong>{test_start_time}</strong></div>
            <div>测试结束时间：<strong>{test_end_time}</strong></div>
        </div>
        
        <div style="display: flex; align-items: center; margin: 20px 0; gap: 40px;">
            <div style="flex: 1; text-align: center;">
                <svg width="120" height="120" viewBox="0 0 120 120">
                    <circle cx="60" cy="60" r="50" fill="#f0f0f0" />
                    <path d="M60,60 L60,10 A50,50 0 {1 if pass_angle > 180 else 0},1 {pass_x:.1f},{pass_y:.1f} Z" fill="#4CAF50" />
                    <path d="M60,60 L{pass_x:.1f},{pass_y:.1f} A50,50 0 {1 if (360 - pass_angle) > 180 else 0},1 60,10 Z" fill="#F44336" />
                    <circle cx="60" cy="60" r="30" fill="white" />
                    <text x="60" y="55" text-anchor="middle" font-size="14" fill="#333">{pass_rate:.0f}%</text>
                    <text x="60" y="75" text-anchor="middle" font-size="10" fill="#666">通过率</text>
                </svg>
            </div>
            <div style="flex: 2;">
                <table border="1" cellpadding="10" cellspacing="0" style="border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; text-align: center;">
                    <tr style="background-color: #f2f2f2; font-weight: bold;">
                        <td>总用例数</td>
                        <td>失败</td>
                        <td>通过</td>
                        <td>通过率</td>
                    </tr>
                    <tr>
                        <td>{total}</td>
                        <td>{failed}</td>
                        <td>{passed}</td>
                        <td>{pass_rate:.1f}%</td>
                    </tr>
                </table>
            </div>
        </div>
        
        <h3 style="margin-top: 30px; margin-bottom: 15px;">用例详情</h3>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; text-align: center;">
            <tr style="background-color: #f2f2f2; font-weight: bold;">
                <td>序号</td>
                <td style="text-align: left;">用例名称</td>
                <td>开始时间</td>
                <td>结束时间</td>
                <td>耗时</td>
                <td>状态</td>
            </tr>
            {case_details}
        </table>
        
        <p style="margin-top: 20px;">详细报告请查看附件（Allure 格式 HTML）。</p>
        """
        
        msg.attach(MIMEText(body, "html", "utf-8"))
        
        # 添加附件 - 只发送 Allure 格式的 HTML 报告
        with open(report_path, "rb") as f:
            attachment = MIMEApplication(f.read())
            attachment.add_header("Content-Disposition", "attachment", filename=str(report_path.name))
            msg.attach(attachment)
        
        # 发送邮件
        with smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"]) as server:
            server.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])
            server.send_message(msg)
        
        print(f"[EMAIL] Allure 格式测试报告已发送至: {EMAIL_CONFIG['recipient']}")
        
    except Exception as e:
        print(f"[EMAIL] 发送邮件失败: {e}")


if __name__ == "__main__":
    main()
