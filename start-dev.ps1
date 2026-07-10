# SmartAM 开发环境启动脚本
# 同时启动后端 (FastAPI) 和前端 (Vite)

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " SmartAM 开发环境启动" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 获取项目根目录
$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $root

# 启动后端
Write-Host "正在启动后端 (FastAPI) ..." -ForegroundColor Green
$backendJob = Start-Job -ScriptBlock {
    param($root)
    Set-Location $root
    python start_backend_daemon.py
} -ArgumentList $root

# 等待后端初始化
Write-Host "等待后端初始化 (3秒) ..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# 启动前端
Write-Host "正在启动前端 (Vite) ..." -ForegroundColor Green
$frontendJob = Start-Job -ScriptBlock {
    param($root)
    Set-Location "$root\frontend"
    npm run dev
} -ArgumentList $root

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 启动完成" -ForegroundColor Green
Write-Host " 前端访问: http://localhost:5173" -ForegroundColor Yellow
Write-Host " 后端访问: http://localhost:8000" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "按 Ctrl+C 停止前后端服务" -ForegroundColor Magenta

# 保持脚本运行并输出任务日志
try {
    while ($true) {
        Receive-Job -Job $backendJob
        Receive-Job -Job $frontendJob
        Start-Sleep -Seconds 1
    }
}
finally {
    Stop-Job -Job $backendJob -ErrorAction SilentlyContinue
    Stop-Job -Job $frontendJob -ErrorAction SilentlyContinue
    Remove-Job -Job $backendJob -ErrorAction SilentlyContinue
    Remove-Job -Job $frontendJob -ErrorAction SilentlyContinue
    Write-Host "服务已停止" -ForegroundColor Red
}
