@echo off
chcp 65001 >nul
title Policy QA AI Assistant - Startup Script

echo ===================================================
echo             Policy QA AI Assistant
echo ===================================================

REM Check Python Environment
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [Error] Python not found. Please install Python and add it to PATH.
    pause
    goto :EOF
)

echo [1/3] Checking and installing dependencies...
echo Upgrading pip to avoid build issues...
python -m pip install --upgrade pip

echo Using Tsinghua PyPI Mirror to speed up downloads...
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    echo [Warning] There might be an issue with dependencies. Trying to continue...
) ELSE (
    echo [OK] Dependencies ready.
)

echo.
echo [2/3] Checking local embedding model...
python download_model.py
IF %ERRORLEVEL% NEQ 0 (
    echo [Warning] Model download failed. If offline, please copy the model manually.
) ELSE (
    echo [OK] Model ready.
)

echo.
echo [3/3] Starting Server...
echo Server will run at http://127.0.0.1:5000
echo - Client URL: http://127.0.0.1:5000/
echo - Admin URL:  http://127.0.0.1:5000/admin
echo.
echo [Tip] Keep this window open to keep the server running.
echo ===================================================

python app.py

pause
