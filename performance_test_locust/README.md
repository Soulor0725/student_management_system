# Locust 性能测试

## 📋 概述

使用 Locust 进行学生管理系统的 API 性能测试，支持分布式测试和 CI 集成。

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install locust
```

### 2. 启动 Flask 应用

```bash
python app.py
```

### 3. 运行性能测试

#### 方式1：Web UI 模式（推荐）

```bash
cd performance_test_locust
locust -f locustfile.py --host=http://localhost:5000
```

然后打开浏览器访问：http://localhost:8089

#### 方式2：无UI模式（CI/CD集成）

```bash
cd performance_test_locust
locust -f locustfile.py --host=http://localhost:5000 --headless -u 100 -r 10 -t 5m --csv=results
```

参数说明：
- `-u 100`：模拟100个并发用户
- `-r 10`：每秒启动10个用户
- `-t 5m`：测试持续5分钟
- `--csv=results`：生成CSV格式报告

## 📊 测试场景

| 任务 | 权重 | 说明 |
|------|------|------|
| 查看学生列表 | 3 | 访问首页获取学生列表 |
| 添加学生 | 2 | POST请求添加新学生 |
| 查看监控指标 | 1 | 访问 /metrics 端点 |
| 查看混沌状态 | 1 | 访问 /chaos/status 端点 |

## 📈 输出报告

### Web UI 模式

- 实时统计图表
- 响应时间分布
- 请求成功率
- RPS（每秒请求数）

### 无UI模式

生成以下文件：
- `results_stats.csv` - 统计数据
- `results_stats_history.csv` - 历史数据
- `results_failures.csv` - 失败详情

## 🔧 配置说明

### 修改测试参数

编辑 `locustfile.py`：

```python
class StudentManagementUser(HttpUser):
    wait_time = between(1, 3)  # 修改任务间隔时间
    host = "http://localhost:5000"  # 修改目标主机
```

### 修改并发用户数

```bash
locust -f locustfile.py -u 500 -r 50  # 500用户，每秒50
```

## 📝 测试报告解读

### 关键指标

- **平均响应时间**：所有请求的平均响应时间
- **中位数响应时间**：50%的请求响应时间
- **95%响应时间**：95%的请求响应时间
- **RPS**：每秒请求数
- **失败率**：失败请求占比

### 性能基准

| 指标 | 目标值 |
|------|--------|
| 平均响应时间 | < 200ms |
| 95%响应时间 | < 500ms |
| 失败率 | < 1% |
| RPS | > 100 |

## 🐛 调试技巧

### 1. 查看详细日志

```bash
locust -f locustfile.py --loglevel=DEBUG
```

### 2. 减少并发数测试

```bash
locust -f locustfile.py --headless -u 10 -r 1 -t 1m
```

### 3. 单独测试某个任务

临时修改 `locustfile.py`，只保留需要测试的任务。

## 📚 参考资料

- [Locust 官方文档](https://docs.locust.io/)
- [Locust GitHub](https://github.com/locustio/locust)