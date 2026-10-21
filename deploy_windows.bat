@echo off
setlocal
chcp 65001 >nul
title SmartAM Windows Deployment
:: 使用系统 PowerShell，策略仅对本次进程生效，不修改机器的执行策略。
set "DEPLOY_POWERSHELL=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if defined PROCESSOR_ARCHITEW6432 set "DEPLOY_POWERSHELL=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
"%DEPLOY_POWERSHELL%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\deploy_windows.ps1"
set "DEPLOY_EXIT=%ERRORLEVEL%"
if not "%DEPLOY_EXIT%"=="0" echo Deployment failed. See the message above and logs\deployment.
pause
exit /b %DEPLOY_EXIT%
