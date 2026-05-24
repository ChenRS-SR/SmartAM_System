@echo off
chcp 65001 >nul
title SmartAM SLM 后端服务
echo ========================================
echo   SmartAM SLM 后端服务启动脚本
echo ========================================
echo.

cd /d "%~dp0"

:: 配置代理
set http_proxy=http://127.0.0.1:7890
set https_proxy=http://127.0.0.1:7890

echo [配置] HTTP_PROXY=%http_proxy%
echo.

cd backend

:: 激活虚拟环境
if exist "..\venv\Scripts\activate.bat" (
    echo [环境] 激活虚拟环境...
    call "..\venv\Scripts\activate.bat"
) else if exist ".venv\Scripts\activate.bat" (
    echo [环境] 激活虚拟环境...
    call ".venv\Scripts\activate.bat"
)

:: 添加SLM数据采集目录到Python路径
echo [配置] 添加SLM数据采集模块路径...
set PYTHONPATH=%PYTHONPATH%;D:\FDM_Monitor_Diagnosis\SLM数据采集

echo.
echo [启动] 正在启动FastAPI服务...
echo        地址: http://localhost:8000
echo        API文档: http://localhost:8000/docs
echo        SLM端点: http://localhost:8000/api/slm/
echo.
echo 按 Ctrl+C 停止服务
echo.

python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

pause
