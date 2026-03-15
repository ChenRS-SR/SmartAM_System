@echo off
chcp 65001 >nul
title SmartAM SLM Complete Startup

:: Set color
color 0A

echo =========================================
echo  SmartAM SLM Monitoring System - Complete Startup
echo =========================================
echo.

:: Check and terminate existing Python processes (avoid port conflicts)
echo [1/4] Checking port usage...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000"') do (
    echo   Terminating process PID %%a using port 8000
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

:: Start backend service
echo.
echo [2/4] Starting backend service...
cd /d "%~dp0backend"
start "SmartAM Backend" cmd /c "python main.py"

:: Wait for backend to start
echo   Waiting for backend to start (5 seconds)...
timeout /t 5 /nobreak >nul

:: Check if backend started successfully
echo   Checking backend status...
curl -s http://localhost:8000/ >nul 2>&1
if %errorlevel% equ 0 (
    echo   Backend service started: http://localhost:8000
) else (
    echo   Warning: Backend service may not have started properly
)

:: Start frontend dev server
echo.
echo [3/4] Starting frontend dev server...
cd /d "%~dp0frontend"
start "SmartAM Frontend" cmd /c "npm run dev"

:: Wait for frontend to start
echo   Waiting for frontend to start (3 seconds)...
timeout /t 3 /nobreak >nul

echo.
echo [4/4] Services startup complete!
echo =========================================
echo  Backend: http://localhost:8000
echo  Frontend: http://localhost:5173
echo  Full Interface: http://localhost:5173/slm/dashboard
echo =========================================
echo.
echo Press any key to open browser...
pause >nul

:: Open browser
start http://localhost:5173/slm/dashboard

echo.
echo Note: Closing this window will NOT stop the services
echo       Please manually close the Backend and Frontend windows to stop
echo.
pause
