@echo off
echo ===================================================
echo    ESP-HI Web Application Launcher
echo ===================================================

cd /d "%~dp0"

echo.
echo [1/3] Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    pause
    exit /b
)

echo.
echo [2/3] Installing dependencies...
pip install -r backend/requirements.txt
if %errorlevel% neq 0 (
    echo Error: Failed to install dependencies.
    pause
    exit /b
)

echo.
echo [3/3] Starting server...
echo.
echo Server will start at: http://localhost:5000
echo Press Ctrl+C to stop the server.
echo.

set FLASK_APP=backend/app.py
python backend/app.py

pause
