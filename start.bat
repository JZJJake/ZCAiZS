@echo off
chcp 65001 >nul
title 政策解答AI助手 - 启动脚本

echo ===================================================
echo             政策解答 AI 助手 启动程序
echo ===================================================

:: 检查 Python 环境
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [错误] 未检测到 Python，请确保已安装 Python 并添加到环境变量中。
    pause
    exit /b
)

echo [1/3] 检查并安装依赖库...
pip install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    echo [警告] 依赖库安装可能存在问题，尝试继续运行...
) ELSE (
    echo [OK] 依赖库检查完成。
)

echo.
echo [2/3] 检查本地向量化模型...
python download_model.py
IF %ERRORLEVEL% NEQ 0 (
    echo [警告] 模型下载可能失败，如果您在内网环境，请确保已手动拷贝模型。
) ELSE (
    echo [OK] 模型准备就绪。
)

echo.
echo [3/3] 启动服务器...
echo 服务器将在 http://127.0.0.1:5000 运行
echo - 客户端访问: http://127.0.0.1:5000/
echo - 管理端访问: http://127.0.0.1:5000/admin
echo.
echo [提示] 保持此窗口开启以维持服务器运行。关闭此窗口将停止服务器。
echo ===================================================

python app.py

pause
