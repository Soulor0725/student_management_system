"""pytest 安全测试配置 — 使用共享 fixtures"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
