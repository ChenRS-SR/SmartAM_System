@echo off
setlocal
chcp 65001 >nul
title SmartAM Auto Start Setup
set "TASK_NAME=SmartAM_System_AutoStart"
set "START_SCRIPT=%~dp0start_smartam.bat"
schtasks /Create /TN "%TASK_NAME%" /SC ONLOGON /DELAY 0000:30 /TR "\"%START_SCRIPT%\"" /RL HIGHEST /F
if errorlevel 1 (
    echo Failed to register SmartAM auto-start task.
    pause
    exit /b 1
)
schtasks /Run /TN "%TASK_NAME%"
if errorlevel 1 (
    echo Task registered, but it could not be started immediately.
    pause
    exit /b 1
)
echo SmartAM auto-start task registered and started: %TASK_NAME%
echo It will start SmartAM 30 seconds after the current user logs in.
pause
exit /b 0
