@echo off
chcp 65001 >nul
title SmartAM 开发启动器
echo ========================================
echo  SmartAM 开发环境启动
echo ========================================
echo.
echo 正在启动后端 (FastAPI) ...
start "SmartAM Backend" python start_backend_daemon.py
echo.
echo 等待后端初始化 ...
timeout /t 3 /nobreak >nul
echo.
echo 正在启动前端 (Vite) ...
start "SmartAM Frontend" cmd /k "cd /d frontend && npm run dev"
echo.
echo ========================================
echo  启动完成
echo  前端访问: http://localhost:5173
echo  后端访问: http://localhost:8000
echo ========================================
echo.
pause
