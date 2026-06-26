@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================
echo IBM MQ XML消息发送器
echo ============================================
echo.

:: 检查Java是否安装
java -version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Java环境，请确保Java已安装并配置环境变量
    pause
    exit /b 1
)

:: 设置MQ JAR路径
set MQ_JAR_PATH=..\lib
set MQ_JAR=

:: 查找IBM MQ的JAR文件
for /r "%MQ_JAR_PATH%" %%f in (*mq*.jar) do (
    if exist "%%f" (
        set MQ_JAR=%%f
        goto :found_jar
    )
)

:: 如果在lib目录没找到，检查当前目录
if not defined MQ_JAR (
    for /r "." %%f in (*mq*.jar) do (
        if exist "%%f" (
            set MQ_JAR=%%f
            goto :found_jar
        )
    )
)

:found_jar
if not defined MQ_JAR (
    echo 错误: 未找到IBM MQ JAR文件
    echo 请将com.ibm.mq.allclient.jar复制到以下任一位置:
    echo   - mq_sender/lib/ 目录
    echo   - mq_sender/ 目录（当前目录）
    pause
    exit /b 1
)

echo 找到MQ JAR文件: !MQ_JAR!
echo.

:: 创建输出目录
if not exist "bin" mkdir bin

:: 编译Java文件
echo 正在编译MQXmlSender.java...
javac -cp "!MQ_JAR!" -d bin MQXmlSender.java
if %errorlevel% neq 0 (
    echo 编译失败!
    pause
    exit /b 1
)
echo 编译成功!
echo.

:: 运行程序
echo 正在发送MQ消息...
echo.
java -cp "bin;!MQ_JAR!" MQXmlSender
echo.

pause
