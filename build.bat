@echo off
echo ===================================================
echo    ESP-HI Application Build Script
echo ===================================================

cd /d "%~dp0"

echo.
echo [1/6] Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    pause
    exit /b
)
python --version

echo.
echo [2/6] Installing build dependencies...
pip install pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Failed to install PyInstaller.
    pause
    exit /b
)
echo PyInstaller installed successfully.

echo.
echo [3/6] Installing application dependencies...
pip install -r backend/requirements.txt
if %errorlevel% neq 0 (
    echo Error: Failed to install application dependencies.
    pause
    exit /b
)
echo Application dependencies installed successfully.

echo.
echo [4/6] Cleaning previous build artifacts...
if exist "build" (
    rmdir /s /q "build"
    echo Removed build directory.
)
if exist "dist" (
    rmdir /s /q "dist"
    echo Removed dist directory.
)
if exist "*.spec" (
    echo Spec file found, will use existing configuration.
)

echo.
echo [5/6] Building executable with PyInstaller...
pyinstaller esp_hi.spec --clean
if %errorlevel% neq 0 (
    echo Error: PyInstaller build failed.
    pause
    exit /b
)

echo.
echo [6/6] Build completed successfully!
echo.
echo Executable location: dist\ESP_HI_Control.exe
echo.
echo You can now run the application by executing:
echo   dist\ESP_HI_Control.exe
echo.

pause