@echo off
chcp 65001 >nul
title SmartAM SLM Complete Startup
setlocal EnableDelayedExpansion

:: 统一使用项目文档和旧一键脚本约定的 Conda 环境名。
set "CONDA_ENV=pytorch_env"
:: 日志存储上限：单文件5MB，保留5份，总日志目录128MB。
set "SMARTAM_LOG_MAX_BYTES=5242880"
set "SMARTAM_LOG_BACKUP_COUNT=5"
set "SMARTAM_LOG_TOTAL_BYTES=134217728"
set "SMARTAM_RELOAD=0"
set "SMARTAM_ACCESS_LOG=0"

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
echo [1/6] Checking runtime environment...
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

:: 启动前执行日志轮转和总量清理，避免旧日志持续占用磁盘。
echo [2/6] Cleaning managed logs...
python "%~dp0scripts\manage_logs.py" --clean --status
if errorlevel 1 (
    echo   [ERROR] Log storage cleanup failed.
    pause
    exit /b 1
)
echo.

:: 检查并释放端口，避免重复启动造成端口冲突。
echo [3/6] Checking port usage...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000"') do (
    echo   Terminating process PID %%a using port 8000
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173"') do (
    echo   Terminating process PID %%a using port 5173
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

:: 构建前端静态页面，正式界面由后端 8000 端口统一提供。
echo.
echo [4/6] Building frontend static assets...
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
call npm run build
if errorlevel 1 (
    echo   [ERROR] frontend build failed.
    pause
    exit /b 1
)

:: 启动后端服务，子窗口中再次激活环境，确保服务进程继承正确 Python。
echo.
echo [5/6] Starting backend service...
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

echo.
echo [6/6] Services startup complete!
echo =========================================
echo  Full Interface: http://%LOCAL_IP%:8000/slm/dashboard
echo  API Docs: http://%LOCAL_IP%:8000/docs
echo  Managed Logs: %~dp0logs
echo =========================================
echo.
echo Opening browser...
timeout /t 2 /nobreak >nul
start "" "http://%LOCAL_IP%:8000/slm/dashboard"

echo.
echo Note: Closing this window will NOT stop the services
echo       Please manually close the Backend window to stop
echo.
pause
