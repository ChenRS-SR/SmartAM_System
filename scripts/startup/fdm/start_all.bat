@echo off
chcp 65001 >nul
echo ==========================================
echo    SmartAM System 一键启动脚本
echo ==========================================
echo.

:: 获取脚本所在目录（SmartAM_System）
set "SCRIPT_DIR=%~dp0"
set "BACKEND_PATH=%SCRIPT_DIR%backend"
set "FRONTEND_PATH=%SCRIPT_DIR%frontend"
set "CONDA_ENV=pytorch_env"

echo [调试] 脚本目录: %SCRIPT_DIR%
echo [调试] 后端路径: %BACKEND_PATH%
echo [调试] 前端路径: %FRONTEND_PATH%
echo.

:: 检查后端文件
if not exist "%BACKEND_PATH%\main.py" (
    echo [错误] 找不到后端文件: %BACKEND_PATH%\main.py
    echo 请确保在 SmartAM_System 目录下运行此脚本
    pause
    exit /b 1
)

:: 检查前端文件
if not exist "%FRONTEND_PATH%\package.json" (
    echo [错误] 找不到前端文件: %FRONTEND_PATH%\package.json
    pause
    exit /b 1
)

echo [1/3] 正在检查环境...

:: 检查 conda
where conda >nul 2>&1
if errorlevel 1 (
    echo [错误] 找不到 conda，请确保已安装 Anaconda/Miniconda 并添加到 PATH
    pause
    exit /b 1
)
echo        Conda: 已找到

:: 检查 node
where node >nul 2>&1
if errorlevel 1 (
    echo [错误] 找不到 Node.js，请确保已安装
    pause
    exit /b 1
)
echo        Node.js: 已找到

echo.
echo [2/3] 正在启动后端服务...
echo        后端地址: http://localhost:8000
echo.

:: 创建后端启动脚本
echo @echo off > "%TEMP%\start_backend.bat"
echo chcp 65001 ^>nul >> "%TEMP%\start_backend.bat"
echo echo [后端] 正在激活 conda 环境... >> "%TEMP%\start_backend.bat"
echo call conda activate %CONDA_ENV% >> "%TEMP%\start_backend.bat"
echo if errorlevel 1 ( >> "%TEMP%\start_backend.bat"
echo   echo [错误] 无法激活 conda 环境: %CONDA_ENV% >> "%TEMP%\start_backend.bat"
echo   echo 请确保环境已创建: conda create -n %CONDA_ENV% python=3.9 >> "%TEMP%\start_backend.bat"
echo   pause >> "%TEMP%\start_backend.bat"
echo   exit /b 1 >> "%TEMP%\start_backend.bat"
echo ) >> "%TEMP%\start_backend.bat"
echo echo [后端] 启动 uvicorn... >> "%TEMP%\start_backend.bat"
echo cd /d "%BACKEND_PATH%" >> "%TEMP%\start_backend.bat"
echo uvicorn main:app --host 0.0.0.0 --port 8000 --reload >> "%TEMP%\start_backend.bat"
echo pause >> "%TEMP%\start_backend.bat"

:: 启动后端
start "SmartAM Backend" "%TEMP%\start_backend.bat"

:: 等待后端启动
echo        等待 5 秒让后端启动...
timeout /t 5 /nobreak >nul

echo.
echo [3/3] 正在启动前端服务...
echo        前端地址: http://localhost:5173
echo.

:: 检查 node_modules
if not exist "%FRONTEND_PATH%\node_modules" (
    echo [警告] 首次运行，正在安装前端依赖...
    echo        这可能需要几分钟，请耐心等待...
    cd /d "%FRONTEND_PATH%"
    call npm install
    if errorlevel 1 (
        echo [错误] npm install 失败
        pause
        exit /b 1
    )
)

:: 创建前端启动脚本
echo @echo off > "%TEMP%\start_frontend.bat"
echo chcp 65001 ^>nul >> "%TEMP%\start_frontend.bat"
echo echo [前端] 正在启动... >> "%TEMP%\start_frontend.bat"
echo cd /d "%FRONTEND_PATH%" >> "%TEMP%\start_frontend.bat"
echo npm run dev >> "%TEMP%\start_frontend.bat"
echo pause >> "%TEMP%\start_frontend.bat"

:: 启动前端
start "SmartAM Frontend" "%TEMP%\start_frontend.bat"

echo.
echo ==========================================
echo    启动命令已发送！
echo ==========================================
echo.
echo 请检查弹出的两个命令行窗口：
echo   - SmartAM Backend  (后端)
echo   - SmartAM Frontend (前端)
echo.
echo 访问地址：
echo   前端: http://localhost:5173
echo   后端: http://localhost:8000
echo   API文档: http://localhost:8000/docs
echo.
echo 按任意键关闭此窗口（服务仍在后台运行）
pause >nul
