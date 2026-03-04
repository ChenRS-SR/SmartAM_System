@echo off
chcp 65001 >nul
echo ==========================================
echo    SmartAM System 后端启动脚本
echo    (使用系统 Python - 无需 Conda)
echo ==========================================
echo.

:: 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
set "BACKEND_PATH=%SCRIPT_DIR%backend"

echo [调试] 后端路径: %BACKEND_PATH%
echo.

:: 检查后端文件
if not exist "%BACKEND_PATH%\main.py" (
    echo [错误] 找不到后端文件: %BACKEND_PATH%\main.py
    pause
    exit /b 1
)

echo [1/2] 检查 Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 找不到 Python，请确保 Python 已安装并添加到 PATH
    pause
    exit /b 1
)
echo        Python: 
python --version

echo.
echo [2/2] 检查依赖...
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo [警告] 缺少依赖，正在安装基本依赖...
    echo        这可能需要几分钟...
    python -m pip install fastapi uvicorn python-multipart websockets numpy opencv-python pillow pydantic pydantic-settings pyserial requests python-dotenv -i https://pypi.tuna.tsinghua.edu.cn/simple
)

echo.
echo ==========================================
echo    正在启动后端服务...
echo    地址: http://localhost:8000
echo    API文档: http://localhost:8000/docs
echo ==========================================
echo.

cd /d "%BACKEND_PATH%"
python main.py

pause
