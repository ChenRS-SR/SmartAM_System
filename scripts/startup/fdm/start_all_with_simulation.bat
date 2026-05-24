@echo off
chcp 65001 >nul
echo ==========================================
echo    SmartAM System - 完整启动（模拟模式）
echo ==========================================
echo.

set "SCRIPT_DIR=%~dp0"
set "BACKEND_PATH=%SCRIPT_DIR%backend"
set "FRONTEND_PATH=%SCRIPT_DIR%frontend"

:: 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Node.js！
    echo.
    echo 请先安装 Node.js：
    echo   1. 访问 https://nodejs.org/
    echo   2. 下载并安装 LTS 版本
    echo   3. 重新运行此脚本
    echo.
    echo 或运行 setup_frontend.bat 获取详细指导
    pause
    exit /b 1
)

:: 检查前端依赖
if not exist "%FRONTEND_PATH%\node_modules" (
    echo [警告] 前端依赖未安装，正在自动安装...
    cd /d "%FRONTEND_PATH%"
    call npm install
    if errorlevel 1 (
        echo [错误] 前端依赖安装失败
        pause
        exit /b 1
    )
)

echo [1/3] 正在启动后端服务（模拟模式）...
echo        地址: http://localhost:8000

:: 配置模拟模式
if not exist "%BACKEND_PATH%\.env" (
    copy "%BACKEND_PATH%\.env.example" "%BACKEND_PATH%\.env" >nul
    echo SIMULATION_MODE=true >> "%BACKEND_PATH%\.env"
    echo SIMULATION_AUTO_FALLBACK=true >> "%BACKEND_PATH%\.env"
)

echo.
echo [激活 Conda 环境...]
call conda activate pytorch_env
if errorlevel 1 (
    echo [错误] 无法激活 Conda 环境 pytorch_env
    echo 请确保 Anaconda/Miniconda 已正确安装
    pause
    exit /b 1
)

:: 启动后端（在新窗口）- 使用 Conda 环境
start "SmartAM Backend (Simulation)" cmd /k "conda activate pytorch_env && cd /d "%BACKEND_PATH%" && python main.py"

echo        等待后端启动...
timeout /t 3 /nobreak >nul

echo.
echo [2/3] 正在启动前端服务...
echo        地址: http://localhost:5173

:: 启动前端（在新窗口）
start "SmartAM Frontend" cmd /k "cd /d "%FRONTEND_PATH%" && npm run dev"

echo        等待前端启动...
timeout /t 3 /nobreak >nul

echo.
echo [3/3] 正在打开浏览器...
timeout /t 2 /nobreak >nul
start http://localhost:5173

echo.
echo ==========================================
echo    启动完成！
echo ==========================================
echo.
echo 访问地址：
echo   前端界面: http://localhost:5173
echo   后端API:  http://localhost:8000
echo   API文档:  http://localhost:8000/docs
echo   视频流:   http://localhost:8000/video_feed
echo.
echo 当前模式：模拟模式（无需硬件）
echo.
echo 提示：关闭弹出的命令行窗口即可停止服务
echo.
pause
