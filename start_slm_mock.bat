@echo off
chcp 65001 >nul
title SmartAM SLM 模拟模式启动
echo ========================================
echo   SLM 模拟模式启动器
echo   （无需硬件，用于测试界面）
echo ========================================
echo.

cd /d "%~dp0"

:: 启动后端（模拟模式）
echo [1/2] 启动后端服务（模拟模式）...
start "SLM后端-模拟" cmd /k "cd /d D:\FDM_Monitor_Diagnosis\SmartAM_System\backend && python -c "
import sys
sys.path.insert(0, r'D:\FDM_Monitor_Diagnosis\SLM数据采集')
from core.slm import get_slm_acquisition
acq = get_slm_acquisition(use_mock=True)
acq.initialize(use_mock=True)
acq.start()
print('[模拟模式] 采集已启动')
print('[模拟模式] 所有传感器使用模拟数据')
import uvicorn
uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=False)
"

:: 等待后端
timeout /t 3 /nobreak >nul

:: 启动前端
echo [2/2] 启动前端（自动打开浏览器）...
start "SLM前端" cmd /k "cd /d D:\FDM_Monitor_Diagnosis\SmartAM_System\frontend && npm run dev"

:: 等待前端
timeout /t 3 /nobreak >nul

:: 打开浏览器
echo 正在打开浏览器...
start http://localhost:5173/#/slm/dashboard

echo.
echo ========================================
echo   模拟模式已启动！
echo ========================================
echo.
echo 当前状态:
echo   - 后端: http://localhost:8000
echo   - 前端: http://localhost:5173
echo   - 模式: 模拟数据（无需硬件）
echo.
echo 提示:
echo   - 模拟数据会自动生成波形和图像
echo   - 可以直接测试所有功能
echo   - 如需真实硬件，请使用 start_slm_dashboard.bat
echo.
timeout /t 5 >nul
