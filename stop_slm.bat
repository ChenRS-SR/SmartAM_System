@echo off
chcp 65001 >nul
title SmartAM SLM 停止服务
echo ========================================
echo   停止SLM相关服务
echo ========================================
echo.

echo [1/3] 正在查找并停止Python后端进程...
tasklist /fi "imagename eq python.exe" /fo csv 2>nul | findstr /i "uvicorn\|main:app" >nul
if %errorlevel% == 0 (
    taskkill /f /im python.exe /fi "windowtitle eq SLM Backend*" 2>nul
    taskkill /f /im python.exe /fi "commandline eq *main:app*" 2>nul
    echo        已停止Python后端服务
) else (
    echo        Python后端服务未运行
)

echo.
echo [2/3] 正在查找并停止Node前端进程...
tasklist /fi "imagename eq node.exe" /fo csv 2>nul | findstr /i "vite" >nul
if %errorlevel% == 0 (
    taskkill /f /im node.exe /fi "windowtitle eq SLM Frontend*" 2>nul
    echo        已停止Node前端服务
) else (
    echo        Node前端服务未运行
)

echo.
echo [3/3] 清理临时文件...
if exist "temp_start_slm.bat" (
    del /f /q temp_start_slm.bat 2>nul
    echo        已清理临时文件
)

echo.
echo ========================================
echo   所有SLM服务已停止
echo ========================================
echo.
pause
