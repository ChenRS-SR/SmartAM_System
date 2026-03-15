@echo off
chcp 65001 >nul
title SmartAM SLM 仪表盘启动器(自动打开浏览器)
echo ========================================
echo   SmartAM SLM 监控系统启动脚本
echo   (自动打开浏览器版本)
echo ========================================
echo.

:: 设置工作目录
cd /d "%~dp0"

:: 检查是否在正确的目录
if not exist "backend\core\slm" (
    echo [错误] 未找到SLM模块，请确保在SmartAM_System目录下运行此脚本
    pause
    exit /b 1
)

echo [1/5] 正在检查环境...

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请安装Python 3.8+
    pause
    exit /b 1
)
echo        Python版本: 
python --version

:: 检查Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Node.js，请安装Node.js 16+
    pause
    exit /b 1
)
echo        Node.js版本: 
node --version

echo.
echo [2/5] 正在配置代理...
set http_proxy=http://127.0.0.1:7890
set https_proxy=http://127.0.0.1:7890
echo        HTTP_PROXY=%http_proxy%
echo        HTTPS_PROXY=%https_proxy%

echo.
echo [3/5] 正在启动后端服务...
cd backend

:: 检查虚拟环境
if exist "..\venv\Scripts\activate.bat" (
    echo        使用虚拟环境
    call "..\venv\Scripts\activate.bat"
) else if exist ".venv\Scripts\activate.bat" (
    echo        使用虚拟环境
    call ".venv\Scripts\activate.bat"
)

:: 启动后端（在新窗口）
echo        启动FastAPI后端服务...
start "SmartAM SLM 后端" cmd /k "title SLM Backend && python -c ^"import sys; sys.path.insert(0, r'D:\FDM_Monitor_Diagnosis\SLM数据采集')^" && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

cd ..

echo.
echo [4/5] 正在启动前端服务（将自动打开浏览器）...
cd frontend

:: 检查node_modules
if not exist "node_modules" (
    echo        首次运行，正在安装依赖...
    call npm install
)

:: 启动前端（在新窗口，--open参数会自动打开浏览器）
echo        启动Vite前端服务...
start "SmartAM SLM 前端" cmd /k "title SLM Frontend && npm run dev"

cd ..

echo.
echo [5/5] 等待服务启动...
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo   启动完成！
echo ========================================
echo.
echo 服务状态:
echo   ✓ 后端API:   http://localhost:8000
echo   ✓ 前端界面:  http://localhost:5173
echo   ✓ 浏览器:    应该已自动打开
echo.
echo 如果浏览器没有自动打开，请手动访问:
echo   http://localhost:5173
echo.
echo SLM专用链接:
echo   仪表盘: http://localhost:5173/#/slm/dashboard
echo.
echo 操作步骤:
echo   1. 在浏览器中选择 SLM 设备类型
echo   2. 进入仪表盘页面
echo   3. 点击"开始采集"按钮
echo.
echo 按任意键关闭此窗口（服务将继续在后台运行）
pause >nul
