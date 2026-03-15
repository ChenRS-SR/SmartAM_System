@echo off
chcp 65001 >nul
echo ============================================
echo     SmartAM 系统 - 纯前端模拟模式
echo ============================================
echo.
echo  此模式不需要运行任何后端服务
echo  所有数据（温度、打印状态、视频流）都是模拟生成的
echo.
echo  前端地址: http://localhost:5173
echo.
echo ============================================
echo.

:: 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Node.js，请先安装 Node.js
    pause
    exit /b 1
)

echo [1/2] 正在进入前端目录...
cd /d "%~dp0\frontend"

echo [2/2] 正在启动前端开发服务器...
echo.
echo ============================================
echo  按 Ctrl+C 停止服务
echo ============================================
echo.

:: 设置环境变量并启动
set VITE_MOCK_MODE=true
set VITE_API_URL=http://localhost:8000
set VITE_WS_URL=ws://localhost:8000/ws

npm run dev

pause
