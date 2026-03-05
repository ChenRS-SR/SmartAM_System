@echo off
chcp 65001 >nul
echo ==========================================
echo    SmartAM System - 纯前端模式启动
@echo    无需后端，使用模拟数据运行
@echo ==========================================
echo.

set "SCRIPT_DIR=%~dp0"
set "FRONTEND_PATH=%SCRIPT_DIR%frontend"

echo [1/3] 检查环境...

:: 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Node.js！
    echo 请先安装 Node.js：https://nodejs.org/
    pause
    exit /b 1
)

echo        Node.js: 
node --version
echo.

echo [2/3] 启用前端模拟模式...

:: 写入模拟模式配置
cd /d "%FRONTEND_PATH%"
echo # 开发环境配置 > .env.local
echo VITE_API_BASE_URL=http://localhost:8000 >> .env.local
echo. >> .env.local
echo # 启用前端模拟模式（无需后端） >> .env.local
echo VITE_MOCK_MODE=true >> .env.local

echo        ✅ 已启用前端模拟模式
echo        前端将使用模拟数据运行
echo.

echo [3/3] 检查依赖并启动...

:: 检查依赖
if not exist "node_modules" (
    echo        安装前端依赖...
    call npm install
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

echo        启动前端服务...
echo.
echo ==========================================
echo    服务启动中...
echo ==========================================
echo.
echo 访问地址：
echo   http://localhost:5173
echo.
echo 功能说明：
echo   ✅ 界面完全可用（使用模拟数据）
echo   ✅ 视频流（模拟动画）
echo   ✅ 温度/位置数据（模拟生成）
echo   ✅ 打印机控制（模拟响应）
echo   ✅ 闭环控制（模拟状态）
echo.
echo 提示：
echo   - 如需连接真实后端，请运行 start_simulation_full.bat 或 start_all.bat
@echo   - 数据不会保存到服务器
@echo   - 适合开发和 UI 调试
@echo.

npm run dev

pause
