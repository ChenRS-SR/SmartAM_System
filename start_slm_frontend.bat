@echo off
chcp 65001 >nul
title SmartAM SLM 前端服务
echo ========================================
echo   SmartAM SLM 前端服务启动脚本
echo ========================================
echo.

cd /d "%~dp0\frontend"

:: 检查Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Node.js，请安装Node.js 16+
    pause
    exit /b 1
)

echo [环境] Node.js版本:
node --version
echo.

:: 检查依赖
if not exist "node_modules" (
    echo [依赖] 首次运行，正在安装npm依赖...
    echo.
    call npm install
    echo.
)

echo [启动] 正在启动Vite开发服务器...
echo        地址: http://localhost:5173
echo        SLM仪表盘: http://localhost:5173/#/slm/dashboard
echo.
echo 按 Ctrl+C 停止服务
echo.

npm run dev

pause
