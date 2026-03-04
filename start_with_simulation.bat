@echo off
chcp 65001 >nul
echo ==========================================
echo    SmartAM System - 模拟模式启动
echo    (无需硬件，用于界面调试)
echo ==========================================
echo.

:: 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
set "BACKEND_PATH=%SCRIPT_DIR%backend"

echo [1/2] 检查环境...

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 找不到 Python
    pause
    exit /b 1
)

:: 检查 .env 文件，如果不存在则从示例创建
if not exist "%BACKEND_PATH%\.env" (
    echo        创建 .env 配置文件...
    copy "%BACKEND_PATH%\.env.example" "%BACKEND_PATH%\.env" >nul
    
    :: 启用模拟模式
    echo SIMULATION_MODE=true >> "%BACKEND_PATH%\.env"
    echo SIMULATION_AUTO_FALLBACK=true >> "%BACKEND_PATH%\.env"
    echo        已启用模拟模式
)

echo        Python: 
python --version
echo.

echo [2/2] 启动后端服务（模拟模式）...
echo        地址: http://localhost:8000
echo        API文档: http://localhost:8000/docs
echo        视频流: http://localhost:8000/video_feed
echo.
echo        提示: 当前为模拟模式，无需连接传感器
echo        所有图像和数据均为模拟生成
echo.

cd /d "%BACKEND_PATH%"
python main.py

pause
