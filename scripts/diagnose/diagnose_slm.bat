@echo off
chcp 65001 >nul
title SLM 诊断工具
echo ========================================
echo   SLM 系统诊断工具
echo ========================================
echo.

cd /d "%~dp0"

echo [1/6] 检查后端服务状态...
curl -s http://localhost:8000/ >nul 2>&1
if %errorlevel% == 0 (
    echo        ✓ 后端服务正在运行
    curl -s http://localhost:8000/ | findstr "running"
) else (
    echo        ✗ 后端服务未启动
    echo        请先运行 start_slm_backend.bat
    pause
    exit /b 1
)

echo.
echo [2/6] 测试SLM状态接口...
curl -s http://localhost:8000/api/slm/status | python -m json.tool 2>nul || curl -s http://localhost:8000/api/slm/status

echo.
echo [3/6] 测试启动接口（模拟模式）...
curl -s -X POST "http://localhost:8000/api/slm/start?use_mock=true" | python -m json.tool 2>nul || curl -s -X POST "http://localhost:8000/api/slm/start?use_mock=true"

echo.
echo [4/6] 等待采集启动...
timeout /t 2 /nobreak >nul

echo.
echo [5/6] 再次检查状态...
curl -s http://localhost:8000/api/slm/status | python -m json.tool 2>nul || curl -s http://localhost:8000/api/slm/status

echo.
echo [6/6] 测试数据接口...
curl -s http://localhost:8000/api/slm/data/latest | python -m json.tool 2>nul || curl -s http://localhost:8000/api/slm/data/latest

echo.
echo ========================================
echo   诊断完成
echo ========================================
echo.
echo 常见问题:
echo   1. 如果状态仍然显示 is_running: false
echo      - 可能是前端调用失败，请打开浏览器F12查看控制台错误
echo   2. 如果显示 is_running: true 但前端不更新
echo      - 可能是WebSocket未连接，刷新页面重试
echo   3. 如果所有测试都失败
echo      - 请重启后端服务再试
echo.
pause
