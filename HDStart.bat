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

:: ─── Headroom Container ─────────────────────────────────────────────
echo [INFO] Checking Headroom container...
docker inspect headroom --format "{{.State.Status}}" 2>nul >nul
if %errorlevel% equ 0 (
    :: Container exists
    for /f "usebackq tokens=*" %%s in (`docker inspect headroom --format "{{.State.Status}}"`) do (
        if "%%s"=="running" (
            echo [OK] Headroom container is running.
        ) else (
            echo [INFO] Starting existing Headroom container...
            docker start headroom >nul
            if %errorlevel% equ 0 (
                echo [OK] Headroom container started.
            ) else (
                echo [WARN] Failed to start Headroom container.
            )
        )
    )
) else (
    echo [INFO] Creating Headroom container...
    docker run -d --name headroom --restart unless-stopped ^
        -p 8787:8787 ^
        ghcr.io/chopratejas/headroom:latest >nul
    if %errorlevel% equ 0 (
        echo [OK] Headroom container created.
    ) else (
        echo [WARN] Failed to create Headroom container. Docker Desktop running?
    )
)

:: Start Flask
echo [INFO] Starting web server...
start "" http://localhost:5000
%PYTHON_CMD% app.py

echo [INFO] Server stopped.
pause
