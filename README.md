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

## 6. 性能测试

### 6.1 JMeter 压测脚本

项目包含 JMeter 压测脚本：`performance_test_jmeter/add_student.jmx`

**功能说明**：
- 自动化添加学生数据
- 支持并发压力测试
- 配套数据清理脚本

**使用方式**：
1. 使用 JMeter 打开 `performance_test_jmx/add_student.jmx`
2. 配置目标服务器地址
3. 运行压测

### 6.2 性能测试数据清理

压测后会产生大量测试数据，可使用脚本快速清理：

```bash
python performance_test_jmeter/delete_performanceTesting_data.py
```

**注意**：该脚本会删除 `students` 表中的所有数据，`users` 表不受影响。

---

## 7. 后续建议

- 增加密码复杂度校验
- 增加 CSRF 防护
- 增加管理员角色和权限控制
- 增加按姓名/班级搜索与分页

