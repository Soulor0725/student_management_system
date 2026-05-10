#!/usr/bin/env python3
"""API 测试运行脚本

运行所有 API 测试并生成详细报告。
"""

import os
import sys
import subprocess
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_tests():
    """运行 API 测试"""
    print("=" * 60)
    print("    API 接口测试套件")
    print("=" * 60)
    print()

    # 确保测试目录存在
    test_dir = Path(__file__).parent
    os.makedirs(test_dir / "reports", exist_ok=True)

    # 切换到项目根目录运行测试
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 运行 pytest
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            str(test_dir / "test_api.py"),
            "-v", "--tb=short"
        ],
        capture_output=True,
        text=True,
        cwd=project_root
    )

    # 输出测试结果
    print("📊 测试输出:")
    print("-" * 60)
    print(result.stdout)

    if result.stderr:
        print("\n❌ 错误输出:")
        print("-" * 60)
        print(result.stderr)

    return result.returncode


def main():
    """主函数"""
    # 运行测试
    exit_code = run_tests()

    print()
    print("=" * 60)
    print(f"测试完成，退出码: {exit_code}")
    print("=" * 60)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
