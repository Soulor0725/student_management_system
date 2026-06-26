# IBM MQ XML消息发送器

## 概述

本项目提供一个简单的IBM MQ消息发送脚本，用于发送XML格式的消息到MQ队列。

## 文件结构

```
mq_sender/
├── MQXmlSender.java    # Java发送代码
├── run_sender.bat      # Windows运行脚本
└── README.md           # 使用说明
```

## 前提条件

1. **Java环境**：需要Java 8或更高版本
2. **IBM MQ JAR文件**：需要 `com.ibm.mq.allclient.jar`

## 使用步骤

### 1. 准备MQ JAR文件

将 `com.ibm.mq.allclient.jar` 复制到以下任一位置：
- `mq_sender/lib/` 目录（推荐）
- `mq_sender/` 目录（当前目录）

### 2. 修改MQ连接配置

编辑 `MQXmlSender.java` 文件，修改以下配置：

```java
private static final String HOST = "localhost";      // MQ主机地址
private static final int PORT = 1414;               // MQ端口
private static final String CHANNEL = "SYSTEM.DEF.SVRCONN";  // 通道名称
private static final String QMGR = "QM1";           // 队列管理器名称
private static final String QUEUE_NAME = "DEV.QUEUE.1";  // 目标队列
```

### 3. 运行脚本

双击运行 `run_sender.bat` 或在命令行执行：

```bash
run_sender.bat
```

## XML消息格式

发送的XML消息示例：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<student>
    <id>2024001</id>
    <name>张三</name>
    <age>20</age>
    <className>计算机科学与技术</className>
    <department>信息学院</department>
    <enrollmentDate>2024-09-01</enrollmentDate>
    <status>active</status>
    <metadata>
        <sender>StudentManagementSystem</sender>
        <timestamp>2024-01-15T10:30:00</timestamp>
        <version>1.0</version>
    </metadata>
</student>
```

## 编译命令（手动）

```bash
# 编译
javac -cp "path/to/com.ibm.mq.allclient.jar" -d bin MQXmlSender.java

# 运行
java -cp "bin;path/to/com.ibm.mq.allclient.jar" MQXmlSender
```

## 注意事项

1. 确保MQ队列管理器已启动并运行
2. 确保目标队列存在且有写入权限
3. 通道配置需要允许客户端连接
4. 如果使用远程MQ服务器，需要确保网络可达

## 错误处理

- **连接失败**：检查MQ主机、端口、通道配置是否正确
- **队列不存在**：确认队列名称和队列管理器名称正确
- **权限问题**：检查MQ用户权限配置
