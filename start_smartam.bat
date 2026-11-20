@echo off
setlocal
chcp 65001 >nul
title SmartAM Platform Service
set "DEPLOY_POWERSHELL=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if defined PROCESSOR_ARCHITEW6432 set "DEPLOY_POWERSHELL=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"

:restart
echo [%DATE% %TIME%] Checking deployment and starting SmartAM service...
"%DEPLOY_POWERSHELL%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\deploy_windows.ps1" -NoBrowser
set "SERVICE_EXIT=%ERRORLEVEL%"
echo [%DATE% %TIME%] Deployment or service exited with code %SERVICE_EXIT%. Retrying in 10 seconds...
timeout /t 10 /nobreak >nul
goto restart
