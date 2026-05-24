@echo off
chcp 65001 >nul
title SmartAM_System Environment Setup

echo ========================================
echo    SmartAM_System Environment Setup
echo ========================================
echo.

cd /d "%~dp0"

where powershell >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] PowerShell is required but not found
    pause
    exit /b 1
)

powershell -ExecutionPolicy Bypass -File "setup.ps1" %*

exit /b %errorlevel%
