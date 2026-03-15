@echo off
chcp 65001 >nul
title SmartAM SLM 快速启动
echo ========================================
echo   SmartAM SLM 快速启动
echo ========================================
echo.

:: 启动后端
echo [1/3] 启动后端服务...
start "SLM后端" cmd /k "cd /d D:\FDM_Monitor_Diagnosis\SmartAM_System\backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000"

:: 等待后端启动
timeout /t 2 /nobreak >nul

:: 启动前端
echo [2/3] 启动前端服务（自动打开浏览器）...
start "SLM前端" cmd /k "cd /d D:\FDM_Monitor_Diagnosis\SmartAM_System\frontend && npm run dev"

:: 等待前端启动
timeout /t 3 /nobreak >nul

:: 尝试打开浏览器
echo [3/3] 正在打开浏览器...
start http://localhost:5173/#/slm/dashboard

echo.
echo ========================================
echo   启动完成！
echo ========================================
echo.
echo 如果浏览器没有自动打开，请手动访问:
echo   http://localhost:5173/#/slm/dashboard
echo.
echo 操作步骤:
echo   1. 等待页面加载完成
echo   2. 选择 SLM 设备
echo   3. 点击"开始采集"
echo.
timeout /t 5 >nul
