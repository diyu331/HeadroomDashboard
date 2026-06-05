@echo off
title Headroom Dashboard

echo ============================================
echo    Headroom Dashboard - Starting...
echo ============================================

:: Detect Python
set PYTHON_CMD=python
where python 2>nul >nul
if %errorlevel% neq 0 (
    where python3 2>nul >nul
    if %errorlevel% neq 0 (
        echo [ERROR] Python not found. Please install Python 3.12+
        echo Download: https://www.python.org/downloads/
        pause
        exit /b 1
    )
    set PYTHON_CMD=python3
)

:: Check flask installed, auto-install if missing
%PYTHON_CMD% -c "import flask" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Installing dependencies: flask requests...
    %PYTHON_CMD% -m pip install flask requests -q
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)

:: Start Flask
echo [INFO] Starting web server...
start "" http://localhost:5000
%PYTHON_CMD% app.py

echo [INFO] Server stopped.
pause
