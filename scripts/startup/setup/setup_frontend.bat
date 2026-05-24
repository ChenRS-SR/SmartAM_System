@echo off
chcp 65001 >nul
echo ==========================================
echo    SmartAM System - 前端环境安装
echo ==========================================
echo.

:: 获取脚本目录
set "SCRIPT_DIR=%~dp0"
set "FRONTEND_PATH=%SCRIPT_DIR%frontend"

echo [1/3] 检查 Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [错误] 未检测到 Node.js！
    echo.
    echo 请按以下步骤安装：
    echo   1. 访问 https://nodejs.org/
    echo   2. 下载 LTS 版本（左侧绿色按钮）
    echo   3. 双击安装，一路点击"下一步"
    echo   4. 安装完成后，关闭此窗口并重新运行此脚本
    echo.
    echo 或使用 winget 安装（管理员权限）：
    echo   winget install OpenJS.NodeJS.LTS
    echo.
    pause
    exit /b 1
)

echo        Node.js 版本:
node --version
echo        NPM 版本:
npm --version
echo.

echo [2/3] 安装前端依赖...
echo        这可能需要几分钟，请耐心等待...
echo.

cd /d "%FRONTEND_PATH%"

:: 检查是否已安装
if exist "node_modules" (
    echo        node_modules 已存在，跳过安装
    echo        如需重新安装，请删除 node_modules 文件夹后重试
) else (
    echo        正在执行 npm install...
    call npm install
    if errorlevel 1 (
        echo [错误] npm install 失败
        pause
        exit /b 1
    )
)

echo.
echo [3/3] 安装完成！
echo.
echo ==========================================
echo    现在可以启动前端了：
echo.
echo    cd frontend
echo    npm run dev
echo.
echo    访问地址: http://localhost:5173
echo ==========================================
echo.

set /p START_NOW=是否立即启动前端？(y/n): 
if /i "%START_NOW%"=="y" (
    echo.
    echo 正在启动前端...
    npm run dev
) else (
    echo.
    echo 您可以稍后手动启动：
    echo   cd frontend
    echo   npm run dev
    pause
)
