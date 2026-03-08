@echo off
chcp 65001 >nul
title SmartAM SLM 完整启动

:: 设置颜色
color 0A

echo =========================================
echo  SmartAM SLM 监控系统 - 完整启动脚本
echo =========================================
echo.

:: 检查并终止已有 Python 进程（避免端口占用）
echo [1/4] 检查端口占用...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000"') do (
    echo   终止占用 8000 端口的进程 PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

:: 启动后端服务
echo.
echo [2/4] 启动后端服务...
cd /d "%~dp0backend"
start "SmartAM Backend" cmd /c "python main.py"

:: 等待后端启动
echo   等待后端启动 (5秒)...
timeout /t 5 /nobreak >nul

:: 检查后端是否启动成功
echo   检查后端状态...
curl -s http://localhost:8000/ >nul 2>&1
if %errorlevel% equ 0 (
    echo   后端服务已启动: http://localhost:8000
) else (
    echo   警告: 后端服务可能未正常启动
)

:: 启动前端开发服务器
echo.
echo [3/4] 启动前端开发服务器...
cd /d "%~dp0frontend"
start "SmartAM Frontend" cmd /c "npm run dev"

:: 等待前端启动
echo   等待前端启动 (3秒)...
timeout /t 3 /nobreak >nul

echo.
echo [4/4] 服务启动完成！
echo =========================================
echo  后端地址: http://localhost:8000
echo  前端地址: http://localhost:5173
echo  完整界面: http://localhost:5173/slm/dashboard
echo =========================================
echo.
echo 按任意键打开浏览器访问系统...
pause >nul

:: 打开浏览器
start http://localhost:5173/slm/dashboard

echo.
echo 提示: 关闭此窗口不会停止服务
echo       请手动关闭 Backend 和 Frontend 窗口来停止服务
echo.
pause
