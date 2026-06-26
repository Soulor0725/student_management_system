@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ===== IBM MQ 连接测试 =====
echo.

:: 检查Java
java -version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Java
    pause
    exit /b 1
)

:: 查找MQ JAR
set MQ_JAR=
for /r "." %%f in (*mq*.jar) do (
    set MQ_JAR=%%f
    goto :found
)
for /r "..\lib" %%f in (*mq*.jar) do (
    set MQ_JAR=%%f
    goto :found
)

:found
if not defined MQ_JAR (
    echo 错误: 未找到IBM MQ JAR
    echo 请将com.ibm.mq.allclient.jar放入当前目录
    pause
    exit /b 1
)

echo 找到MQ JAR: !MQ_JAR!
echo.

:: 编译并运行
javac -cp "!MQ_JAR!" MQConnectTest.java
java -cp ".;!MQ_JAR!" MQConnectTest

pause
