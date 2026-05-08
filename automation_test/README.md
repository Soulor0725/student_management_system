# agent-browser

一个基于 Python + Playwright 的自动化测试框架，用于测试学生管理系统的功能。

## 版本说明

版本号：**V0.2** | 升级日期：2026-04-23


## 项目大纲

1. **项目概述**
2. **启动依赖**
3. **安装步骤**
4. **使用方法**
5. **测试用例说明**
6. **报告生成**
7. **邮件通知**
8. **项目结构**
9. **常见问题**

## 1. 项目概述

agent-browser 是一个专门为学生管理系统设计的自动化测试框架，提供以下功能：
- 浏览器自动化操作
- 测试用例管理
- 测试结果截图
- 详细的测试报告生成
- 邮件通知功能

## 2. 启动依赖

**重要：使用前必须先启动学生管理系统**

1. **学生管理系统**：
   - 路径：`../student_management`
   - 启动命令：`python app.py`
   - 默认运行地址：`http://localhost:5000`

2. **Python 环境**：
   - Python 3.8+
   - 虚拟环境

3. **浏览器**：
   - Google Chrome（推荐）

## 3. 安装步骤

### 3.1 创建虚拟环境并激活

```powershell
python -m venv .venv
# Windows
.venv\Scripts\Activate.ps1
# Linux/Mac
# source .venv/bin/activate
```

### 3.2 安装依赖

```powershell
pip install -r requirements.txt
python -m playwright install
```

## 4. 使用方法

### 4.1 启动学生管理系统（必须）

```powershell
# 在 student_management 目录下
python app.py
```

### 4.2 运行自动化测试

#### 方法1：直接运行主脚本

```powershell
# 在 agent-browser 目录下
python app.py
```

#### 方法2：使用 CLI 工具（推荐）

```powershell
# 在 agent-browser 目录下
# 运行测试 + 查看报告 + 发送邮件
python cli.py run && python cli.py report && python cli.py send-mail

# 仅运行测试
python cli.py run

# 仅查看报告
python cli.py report

# 仅发送邮件
python cli.py send-mail

# 运行指定用例
python cli.py run --case 1  # 运行注册功能测试
python cli.py run --case 2  # 运行登录功能测试
python cli.py run --case 3  # 运行添加学生测试
python cli.py run --case 4  # 运行登录失败测试
```

### 4.3 查看测试结果

- **终端输出**：实时显示测试进度和结果
- **HTML 报告**：生成在 `output/` 目录，文件名格式：`系统名_年月日时分秒.html`
- **截图**：保存在 `output/` 目录
  - 失败截图：`用例名称_年月日时分秒.png`
  - 成功截图：保留 1 小时后自动删除

## 5. 测试用例说明

当前包含以下测试用例：

1. **注册功能**：测试用户注册流程
2. **登录功能**：测试用户登录流程
3. **添加学生**：测试添加学生信息功能
4. **登录失败**：测试登录失败场景（预期失败）

## 6. 报告生成

### 6.1 HTML 报告

- 生成位置：`reports/` 目录
- 报告内容：
  - 测试执行开始/结束时间
  - 每个测试用例的开始/结束时间
  - 测试结果统计
  - 测试用例占比饼图
  - 详细的测试步骤和截图

### 6.2 报告格式

报告使用 Allure 风格的 HTML 格式，包含：
- 测试结果概览
- 详细的测试步骤
- 测试截图
- 统计图表

## 7. 邮件通知

### 7.1 配置

在 `app.py` 中配置邮件参数：
- 发件人邮箱
- SMTP 服务器
- 邮箱密码（或授权码）
- 收件人邮箱

### 7.2 邮件内容

- 邮件标题：`系统名_自动化测试报告-年月日时分秒`
- 邮件正文：包含测试执行时间和结果统计
- 附件：HTML 测试报告
- 内嵌：测试结果饼图

## 8. 项目结构

```
agent-browser/
├── app.py              # 主测试脚本
├── requirements.txt    # Python 依赖
├── output/             # 测试输出（报告和截图）
└── README.md           # 项目文档
```

## 9. 常见问题

### 9.1 浏览器启动失败
- 检查 Chrome 浏览器是否安装
- 检查浏览器路径是否正确
- 尝试使用 `--no-sandbox` 参数

### 9.2 连接超时
- 确保学生管理系统已启动
- 检查网络连接
- 调整 `slow_mo` 参数

### 9.3 邮件发送失败
- 检查邮箱配置
- 检查 SMTP 服务器设置
- 确保网络连接正常

## 10. 注意事项

- 测试执行时浏览器会自动打开，请不要手动操作
- 测试过程中会自动生成截图和报告
- 成功的截图会在 1 小时后自动删除
- 确保学生管理系统在测试前已启动
