@echo off
chcp 65001 >nul
echo ==========================================
echo    SmartAM System - 完整模拟模式启动
echo    (无需任何硬件：相机+打印机)
echo ==========================================
echo.

set "SCRIPT_DIR=%~dp0"
set "BACKEND_PATH=%SCRIPT_DIR%backend"
set "FRONTEND_PATH=%SCRIPT_DIR%frontend"

echo [1/4] 检查环境...

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 找不到 Python
    pause
    exit /b 1
)

:: 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Node.js！
    echo 请先运行 setup_frontend.bat 安装 Node.js
    pause
    exit /b 1
)

echo        Python: 
python --version
echo        Node.js: 
node --version
echo.

echo [2/4] 配置模拟模式...

:: 创建/更新 .env 文件
if not exist "%BACKEND_PATH%\.env" (
    copy "%BACKEND_PATH%\.env.example" "%BACKEND_PATH%\.env" >nul
)

:: 启用所有模拟模式
echo SIMULATION_MODE=true > "%BACKEND_PATH%\.env.temp"
echo SIMULATION_AUTO_FALLBACK=true >> "%BACKEND_PATH%\.env.temp"
echo OCTOPRINT_SIMULATION=true >> "%BACKEND_PATH%\.env.temp"
echo OCTOPRINT_SIMULATION_AUTO_FALLBACK=true >> "%BACKEND_PATH%\.env.temp"
echo IDS_ENABLE=false >> "%BACKEND_PATH%\.env.temp"
echo SIDE_CAMERA_ENABLE=false >> "%BACKEND_PATH%\.env.temp"
echo FOTRIC_ENABLE=false >> "%BACKEND_PATH%\.env.temp"
echo SIMULATION_HOTEND_TEMP=200 >> "%BACKEND_PATH%\.env.temp"
echo SIMULATION_BED_TEMP=60 >> "%BACKEND_PATH%\.env.temp"

:: 保留原有的 OctoPrint 配置（如果存在）
if exist "%BACKEND_PATH%\.env" (
    for /f "tokens=*" %%a in ('type "%BACKEND_PATH%\.env"') do (
        echo %%a | findstr /B "OCTOPRINT_URL=" >nul && echo %%a >> "%BACKEND_PATH%\.env.temp"
        echo %%a | findstr /B "OCTOPRINT_API_KEY=" >nul && echo %%a >> "%BACKEND_PATH%\.env.temp"
    )
)

move /Y "%BACKEND_PATH%\.env.temp" "%BACKEND_PATH%\.env" >nul

echo        已启用：
echo          - 相机模拟（IDS/旁轴/热像）
echo          - OctoPrint 模拟（打印机状态/温度/位置）
echo.

echo [3/4] 检查前端依赖...
if not exist "%FRONTEND_PATH%\node_modules" (
    echo        正在安装前端依赖...
    cd /d "%FRONTEND_PATH%"
    call npm install
    if errorlevel 1 (
        echo [错误] 前端依赖安装失败
        pause
        exit /b 1
    )
) else (
    echo        前端依赖已安装
)
echo.

echo [4/4] 启动服务...
echo.
echo        正在启动后端（模拟模式）...
start "SmartAM Backend (Full Simulation)" cmd /k "cd /d "%BACKEND_PATH%" && echo [模拟模式] 正在启动... && python main.py"

echo        等待后端启动...
timeout /t 4 /nobreak >nul

echo        正在启动前端...
start "SmartAM Frontend" cmd /k "cd /d "%FRONTEND_PATH%" && npm run dev"

echo        等待前端启动...
timeout /t 4 /nobreak >nul

echo        正在打开浏览器...
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
echo 当前模式：完整模拟模式
echo   - 相机: 模拟图像
echo   - 打印机: 模拟 OctoPrint
echo   - 温度: 模拟数据
echo   - 位置: 模拟运动
echo.
echo 提示：
echo   - 关闭弹出的命令行窗口即可停止服务
echo   - 连接真实硬件时，修改 backend/.env：
echo     SIMULATION_MODE=false
echo     OCTOPRINT_SIMULATION=false
echo.
pause
