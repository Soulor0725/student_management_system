#!/usr/bin/env python
"""
agent-browser CLI 工具
用法：
    python cli.py run              # 运行所有测试
    python cli.py run --case 1     # 运行指定用例
    python cli.py report           # 生成测试报告
    python cli.py send-mail        # 发送测试报告邮件
    python cli.py --help           # 显示帮助信息
"""

import argparse
import sys
import subprocess
from pathlib import Path

def run_tests(case=None):
    """运行测试"""
    if case:
        print(f"正在运行用例 {case}...")
    else:
        print("正在运行所有测试...")

    cmd = [sys.executable, "app.py"]
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode

def show_help():
    """显示帮助信息"""
    help_text = """
agent-browser CLI 工具

用法：
    python cli.py run              # 运行所有测试
    python cli.py run --case 1     # 运行指定用例（1-4）
    python cli.py report           # 查看测试报告目录
    python cli.py send-mail        # 发送测试报告邮件
    python cli.py --help           # 显示帮助信息

示例：
    python cli.py run              # 运行所有测试
    python cli.py run --case 1     # 只运行注册功能测试
    python cli.py run --case 2     # 只运行登录功能测试
    python cli.py run --case 3     # 只运行添加学生测试
    python cli.py run --case 4     # 只运行登录失败测试

测试用例说明：
    1 - 注册功能测试
    2 - 登录功能测试
    3 - 添加学生功能测试
    4 - 登录失败测试
"""
    print(help_text)

def main():
    parser = argparse.ArgumentParser(
        description="agent-browser 自动化测试框架 CLI 工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python cli.py run              运行所有测试
  python cli.py run --case 1     运行指定用例
  python cli.py --help           显示帮助信息
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    run_parser = subparsers.add_parser("run", help="运行测试")
    run_parser.add_argument("--case", type=int, choices=[1, 2, 3, 4],
                          help="指定运行的测试用例（1-4）")

    subparsers.add_parser("report", help="查看测试报告目录")

    subparsers.add_parser("send-mail", help="发送测试报告邮件")

    args = parser.parse_args()

    if args.command == "run":
        return run_tests(args.case if hasattr(args, 'case') else None)
    elif args.command == "report":
        output_dir = Path(__file__).parent / "output"
        if output_dir.exists():
            print(f"测试报告目录：{output_dir}")
            print("\n报告文件：")
            for f in sorted(output_dir.glob("*.html"), key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
                print(f"  - {f.name}")
        else:
            print("暂无测试报告")
        return 0
    elif args.command == "send-mail":
        print("发送测试报告邮件...")
        print("请在 app.py 中配置邮件发送功能")
        return 0
    else:
        show_help()
        return 0

if __name__ == "__main__":
    sys.exit(main() or 0)
