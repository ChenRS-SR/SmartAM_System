@echo off
chcp 65001 >nul
echo ==========================================
echo    SmartAM System 停止服务脚本
echo ==========================================
echo.

echo [1/3] 正在停止后端服务...
taskkill /FI "WINDOWTITLE eq SmartAM Backend*" /F >nul 2>&1
if errorlevel 1 (
    echo        后端窗口未找到（可能已停止）
) else (
    echo        后端服务已停止
)

echo.
echo [2/3] 正在停止前端服务...
taskkill /FI "WINDOWTITLE eq SmartAM Frontend*" /F >nul 2>&1
if errorlevel 1 (
    echo        前端窗口未找到（可能已停止）
) else (
    echo        前端服务已停止
)

echo.
echo [3/3] 检查并清理端口占用...

:: 结束占用 8000 端口的进程
taskkill /FI "IMAGENAME eq python.exe" /F >nul 2>&1

:: 结束占用 5173 端口的进程（vite/node）
taskkill /FI "IMAGENAME eq node.exe" /F >nul 2>&1

echo        端口清理完成

echo.
echo ==========================================
echo    所有服务已停止
echo ==========================================
pause
