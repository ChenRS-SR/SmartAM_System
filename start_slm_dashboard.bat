@echo off
chcp 65001 >nul
title SmartAM SLM 系统启动

:: 设置颜色
color 0A

echo =========================================
echo  SmartAM SLM 监控系统 - 一键启动
echo =========================================
echo.

:: 获取脚本所在目录
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

:: 检查端口占用并释放
echo [1/3] 检查端口占用...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000"') do (
    echo   释放端口 8000，终止进程 PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

:: 启动后端
echo.
echo [2/3] 启动后端服务 (端口 8000)...
cd /d "%PROJECT_DIR%backend"
start "SmartAM Backend" cmd /k "python main.py"

:: 等待后端启动
echo   等待后端启动...
timeout /t 5 /nobreak >nul

:: 验证后端是否启动
curl -s http://localhost:8000/ >nul 2>&1
if %errorlevel% equ 0 (
    echo   后端启动成功: http://localhost:8000
) else (
    echo   警告: 后端可能未正常启动，请检查后端窗口
)

:: 启动前端
echo.
echo [3/3] 启动前端开发服务器...
cd /d "%PROJECT_DIR%frontend"
start "SmartAM Frontend" cmd /k "npm run dev"

:: 等待前端启动
echo   等待前端启动...
timeout /t 3 /nobreak >nul

echo.
echo =========================================
echo  启动完成！
echo =========================================
echo  后端 API: http://localhost:8000
echo  前端界面: http://localhost:5173
echo  SLM 仪表盘: http://localhost:5173/slm/dashboard
echo =========================================
echo.
echo 按任意键打开浏览器...
pause >nul

:: 打开浏览器
start http://localhost:5173/slm/dashboard

echo.
echo 提示: 关闭此窗口不会停止服务
echo       请手动关闭 Backend 和 Frontend 窗口来停止服务
echo.
pause
