@echo off
setlocal
chcp 65001 >nul
title SmartAM Platform Service
set "DEPLOY_POWERSHELL=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if defined PROCESSOR_ARCHITEW6432 set "DEPLOY_POWERSHELL=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
"%DEPLOY_POWERSHELL%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\deploy_windows.ps1" -StartOnly -NoBrowser
exit /b %ERRORLEVEL%
