@echo off
chcp 65001 >nul
echo ============================================
echo   SmartAM_System - 智能制造监控系统
echo ============================================
echo.

:: 检查 Python
echo [1/3] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请安装 Python 3.8+
    pause
    exit /b 1
)

:: 检查虚拟环境
echo [2/3] 检查依赖...
if not exist "venv" (
    echo 创建虚拟环境...
    python -m venv venv
)

call venv\Scripts\activate

:: 检查并安装依赖
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo 安装依赖...
    pip install -r requirements.txt
)

echo [3/3] 启动服务...
echo.
echo 服务地址：
echo   - API 文档: http://localhost:8000/docs
echo   - 视频流:   http://localhost:8000/video_feed
echo.
echo 按 Ctrl+C 停止服务
echo ============================================
echo.

python main.py

pause
