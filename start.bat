@echo off
chcp 65001 >nul
title SmartAM_System Launcher

echo ========================================
echo    SmartAM_System
echo ========================================
echo.

cd /d "%~dp0"

where powershell >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] PowerShell is required but not found
    pause
    exit /b 1
)

:: Check if virtual environment exists
if not exist "venv\Scripts\python.exe" (
    echo [INFO] Virtual environment not found!
    echo.
    echo Would you like to run setup first?
    choice /C YN /M "Run setup now"
    if %errorlevel% == 1 (
        call setup.bat
        if %errorlevel% neq 0 (
            echo.
            echo [ERROR] Setup failed
            pause
            exit /b 1
        )
    ) else (
        echo.
        echo Cannot start without virtual environment.
        pause
        exit /b 1
    )
)

echo [INFO] Starting SmartAM_System...
echo.

powershell -ExecutionPolicy Bypass -File "start.ps1" %*

exit /b 0
