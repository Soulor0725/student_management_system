# 学生管理系统（Python + Flask）

一个简单的学生管理系统，支持：

- 用户注册
- 用户登录 / 退出登录
- 登录成功 Toast 提示后跳转
- 学生新增、查看、编辑、删除
- 会话登录保护（未登录不可访问学生管理页）

当前默认数据库：`SQLite`（本地文件数据库）。

---

## 1. 版本说明

### V0.1（当前版本）

- 完成基础学生管理系统（Flask + Jinja2）
- 实现注册、登录、退出登录
- 实现登录成功 Toast 提示后跳转
- 实现学生增删改查
- 增加 SQLite 持久化存储
- 提供 MySQL 连接改造说明

---

## 2. 项目结构

```text
student_management/
├─ app.py
├─ requirements.txt
├─ README.md
├─ data/
│  └─ student_management.db
├─ templates/
│  ├─ auth.html
│  └─ index.html
└─ static/
   └─ style.css
```

---

## 3. 运行项目

### 2.1 安装依赖

```bash
pip install -r requirements.txt
```

### 2.2 启动服务

```bash
python app.py
```

启动后访问：

- 登录页：[http://127.0.0.1:5000/login](http://127.0.0.1:5000/login)

---

## 4. 默认数据库说明（SQLite）

- 数据库文件：`data/student_management.db`
- 程序启动时会自动初始化表：
  - `users`
  - `students`

---

## 5. 如果要连接 MySQL，怎么改

下面给一套最小改造方案（保持现有业务逻辑不变）。

### 4.1 安装 MySQL 驱动

推荐用 `PyMySQL`：

```bash
pip install pymysql
```

并把 `requirements.txt` 增加：

```txt
flask>=3.0.0
pymysql>=1.1.0
```

### 4.2 创建 MySQL 数据库

先在 MySQL 中执行：

```sql
CREATE DATABASE student_management DEFAULT CHARACTER SET utf8mb4;
```

### 4.3 在 `app.py` 中改连接方式

把当前 `sqlite3` 连接改为 MySQL 连接（示例）：

```python
import pymysql

def get_db_connection():
    return pymysql.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="你的密码",
        database="student_management",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )
```

### 4.4 初始化建表 SQL（MySQL）

将初始化逻辑中的 SQL 改成兼容 MySQL 的写法：

```sql
CREATE TABLE IF NOT EXISTS users (
  id INT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(100) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS students (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  age INT NOT NULL,
  class_name VARCHAR(100) NOT NULL
);
```

### 4.5 参数占位符注意事项

- SQLite 占位符是 `?`
- PyMySQL 占位符是 `%s`

例如：

```python
# SQLite
conn.execute("SELECT 1 FROM users WHERE username = ?", (username,))

# MySQL(PyMySQL)
cursor.execute("SELECT 1 FROM users WHERE username = %s", (username,))
```

### 4.6 事务提交

MySQL 下保留 `conn.commit()`，发生异常时可 `conn.rollback()`。

---

## 6. 自动化测试

### 6.1 Browser Automation 测试

项目包含浏览器自动化测试：`automation_test/`

**功能说明**：
- 基于 Playwright 的浏览器自动化测试
- 支持学生管理功能自动化测试
- 生成测试报告

**使用方式**：
```bash
cd automation_test
pip install -r requirements.txt
python -m pytest
# 或使用 cli.py 运行特定测试
python cli.py
```

### 6.2 性能测试

#### 6.2.1 JMeter 压测脚本

项目包含 JMeter 压测脚本：`performance_test_jmeter/add_student.jmx`

**功能说明**：
- 自动化添加学生数据
- 支持并发压力测试
- 配套数据清理脚本

**使用方式**：
1. 使用 JMeter 打开 `performance_test_jmeter/add_student.jmx`
2. 配置目标服务器地址
3. 运行压测

#### 6.2.2 性能测试数据清理

压测后会产生大量测试数据，可使用脚本快速清理：

```bash
python performance_test_jmeter/delete_performanceTesting_data.py
```

**注意**：该脚本会删除 `students` 表中的所有数据，`users` 表不受影响。

---

## 7. 单元测试

项目包含完整的单元测试：`unit_test/test_app.py`

**测试覆盖**：
- 密码哈希函数测试
- 用户注册功能测试（空字段、成功、重复用户名）
- 用户登录功能测试（错误密码、成功登录）
- 学生管理功能测试（登录拦截、增删操作）

**使用方式**：
```bash
cd student_management
pip install pytest
python -m pytest unit_test/test_app.py -v
```

---

## 8. 持续集成 CI/CD

项目配置了 GitHub Actions：`.github/workflows/ci.yml`

**功能**：
- Push 和 PR 时自动运行单元测试
- 自动检查 Flask 应用是否能正常启动

**工作流**：
1. 拉取代码
2. 安装 Python 环境
3. 安装依赖 (requirements.txt + pytest)
4. 运行 `pytest unit_test/test_app.py`
5. 验证 Flask 应用导入

**状态查看**：
- GitHub 仓库 → Actions 标签页
- Push 后自动触发，无需手动操作

---

## 9. 性能监控（Prometheus + Grafana）

项目集成了 Prometheus + Grafana 监控方案，可实时监控接口请求指标。

### 9.1 监控配置

**Prometheus 配置**：
- 配置文件：`monitoring/prometheus.yml`
- 默认抓取地址：`http://localhost:5000/metrics`
- 抓取间隔：5秒

**Flask 应用指标**：
- `flask_http_request_total` - 请求总数（含 path, method, status 标签）
- `flask_http_request_duration_seconds` - 请求耗时（直方图）

### 9.2 启动监控

**启动 Prometheus**：
```bash
cd C:\Users\Administrator\Documents\Downloads\prometheus-3.11.3.windows-amd64
prometheus.exe --config.file=prometheus.yml
```

**启动 Grafana**：
```bash
grafana-server.exe start
```

### 9.3 导入仪表盘

1. 打开 Grafana：`http://localhost:3000`
2. 配置 Prometheus 数据源
3. 导入仪表盘文件：`monitoring/student-management-dashboard.json`

### 9.4 仪表盘面板

| 面板 | 说明 |
|------|------|
| 总请求数 | 所有接口总请求量趋势 |
| 按接口路径统计请求数 | 各接口请求数量对比 |
| 成功请求数(200) | 成功请求总数 |
| 非200请求数 | 失败请求总数 |
| 平均请求延迟 | 整体平均延迟趋势 |
| 各接口平均耗时(秒) | 各接口平均耗时对比 |
| 各接口失败请求数 | 各接口失败请求统计 |
| 状态码分布 | 饼图展示状态码占比 |

---

## 10. 混沌测试（Chaos Engineering）

项目集成了混沌测试功能，用于验证系统在故障场景下的稳定性。

### 10.1 混沌测试模块

**目录结构**：
```
chaos_test/
├─ chaos_injector.py    # 故障注入核心模块
├─ chaos_api.py         # 混沌测试 API 控制器
├─ config.py            # 混沌测试配置
└─ run_chaos_test.py    # 混沌测试运行脚本
```

### 10.2 支持的故障类型

| 故障类型 | 说明 | 严重程度 |
|---------|------|---------|
| `latency` | 随机延迟 0.1-3 秒 | 低 |
| `error` | 随机返回 500/503/408 错误 | 中 |
| `timeout` | 模拟请求超时 | 高 |
| `db_failure` | 模拟数据库连接失败 | 严重 |

### 10.3 API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/chaos/status` | GET | 获取混沌测试状态 |
| `/chaos/start` | POST | 启动混沌测试 |
| `/chaos/stop` | POST | 停止混沌测试 |
| `/chaos/toggle` | POST | 切换混沌测试状态 |
| `/chaos/config` | PUT | 更新混沌测试配置 |

### 10.4 使用方式

**方式1：通过 API 控制**
```bash
# 启动混沌测试（默认10%故障概率）
curl -X POST http://localhost:5000/chaos/start

# 启动混沌测试（设置20%故障概率）
curl -X POST http://localhost:5000/chaos/start -H "Content-Type: application/json" -d '{"probability": 0.2}'

# 查看状态
curl http://localhost:5000/chaos/status

# 停止混沌测试
curl -X POST http://localhost:5000/chaos/stop
```

**方式2：使用运行脚本**
```bash
cd chaos_test
python run_chaos_test.py --url http://localhost:5000 --scenario normal --duration 60
```

### 10.5 预设场景

| 场景 | 故障概率 | 故障类型 |
|------|---------|---------|
| `light` | 5% | 延迟 |
| `normal` | 10% | 延迟、错误 |
| `heavy` | 20% | 延迟、错误、超时 |
| `extreme` | 30% | 全部类型 |

### 10.6 注意事项

- 混沌测试仅用于测试环境，**请勿在生产环境启用**
- 启用混沌测试后，系统会随机模拟故障，可能影响正常测试
- 建议在性能监控配合下进行混沌测试，观察系统响应

---

## 11. 后续建议

- 增加密码复杂度校验
- 增加 CSRF 防护
- 增加管理员角色和权限控制
- 增加按姓名/班级搜索与分页
- 添加分布式追踪（OpenTelemetry + Jaeger）
- 扩展混沌测试场景（网络分区、资源耗尽等）

