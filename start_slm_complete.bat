@echo off
chcp 65001 >nul
title SmartAM SLM Complete Startup
setlocal EnableDelayedExpansion

:: 统一使用项目文档和旧一键脚本约定的 Conda 环境名。
set "CONDA_ENV=pytorch_env"

:: 设置控制台颜色。
color 0A

:: 获取本机局域网IP
set "LOCAL_IP="
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set "ip=%%a"
    set "ip=!ip: =!"
    echo !ip! | findstr /V "^127\." >nul
    if !errorlevel! equ 0 (
        if not defined LOCAL_IP set "LOCAL_IP=!ip!"
    )
)
if not defined LOCAL_IP set "LOCAL_IP=localhost"

echo =========================================
echo  SmartAM SLM Monitoring System - Complete Startup
echo =========================================
echo.

:: 检查基础命令，缺少依赖时直接停止，避免误用系统 Python。
echo [1/5] Checking runtime environment...
where conda >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Conda not found. Please install Anaconda/Miniconda and add it to PATH.
    pause
    exit /b 1
)

call conda activate %CONDA_ENV% >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Cannot activate Conda environment: %CONDA_ENV%
    echo   Please create it first: conda create -n %CONDA_ENV% python=3.9
    pause
    exit /b 1
)

where node >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Node.js not found. Please install Node.js 18+.
    pause
    exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] npm not found. Please reinstall Node.js.
    pause
    exit /b 1
)
echo   Conda environment: %CONDA_ENV%
python --version
node --version
echo.

:: 检查并释放端口，避免重复启动造成端口冲突。
echo [2/5] Checking port usage...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000"') do (
    echo   Terminating process PID %%a using port 8000
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173"') do (
    echo   Terminating process PID %%a using port 5173
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

:: 启动后端服务，子窗口中再次激活环境，确保服务进程继承正确 Python。
echo.
echo [3/5] Starting backend service...
cd /d "%~dp0backend"
start "SmartAM Backend" cmd /k "call conda activate %CONDA_ENV% && python main.py"

:: 等待后端完成初始化。
echo   Waiting for backend to start (5 seconds)...
timeout /t 5 /nobreak >nul

:: 检查后端是否启动成功。
echo   Checking backend status...
curl -s http://localhost:8000/ >nul 2>&1
if %errorlevel% equ 0 (
    echo   Backend service started: http://%LOCAL_IP%:8000
) else (
    echo   Warning: Backend service may not have started properly
)

:: 首次运行时安装前端依赖。
echo.
echo [4/5] Starting frontend dev server...
cd /d "%~dp0frontend"
if not exist "node_modules" (
    echo   Installing frontend dependencies...
    call npm install
    if errorlevel 1 (
        echo   [ERROR] npm install failed.
        pause
        exit /b 1
    )
)
start "SmartAM Frontend" cmd /k "npm run dev -- --host 0.0.0.0 --port 5173"

:: 等待前端开发服务器启动。
echo   Waiting for frontend to start (3 seconds)...
timeout /t 3 /nobreak >nul

echo.
echo [5/5] Services startup complete!
echo =========================================
echo  Backend: http://%LOCAL_IP%:8000
echo  Frontend: http://%LOCAL_IP%:5173
echo  Full Interface: http://%LOCAL_IP%:5173
echo =========================================
echo.
echo Opening browser...
timeout /t 2 /nobreak >nul
start "" "http://%LOCAL_IP%:5173"

echo.
echo Note: Closing this window will NOT stop the services
echo       Please manually close the Backend and Frontend windows to stop
echo.
pause
