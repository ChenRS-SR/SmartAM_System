# SmartAM_System Integrated Start Script
param([switch]$NoBrowser, [switch]$SkipFrontend)

$ErrorActionPreference = "Stop"
$ProjectRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Get-Location }
Set-Location $ProjectRoot

# Config
$BackendPort = 8000
$FrontendPort = 5173
$VenvPath = Join-Path $ProjectRoot "venv"
$BackendPath = Join-Path $ProjectRoot "backend"
$FrontendPath = Join-Path $ProjectRoot "frontend"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$VenvActivate = Join-Path $VenvPath "Scripts\activate.bat"

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-OK($msg) { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red }

Clear-Host
Write-Host "========================================"
Write-Host "   SmartAM_System Start Tool"
Write-Host "========================================"
Write-Host ""

# ========== Step 1: Check Virtual Environment ==========
Write-Info "Checking Python virtual environment..."

if (-not (Test-Path $VenvPython)) {
    Write-Err "Virtual environment not found at: $VenvPath"
    Write-Host ""
    Write-Host "Please run setup.bat first to create the environment."
    Write-Host ""
    pause
    exit 1
}

Write-OK "Virtual environment found"

# ========== Step 2: Check Directories ==========
if (-not (Test-Path $BackendPath)) {
    Write-Err "Backend directory not found: $BackendPath"
    pause
    exit 1
}

if ((-not $SkipFrontend) -and (-not (Test-Path $FrontendPath))) {
    Write-Warn "Frontend directory not found, will start backend only"
    $SkipFrontend = $true
}

# ========== Step 3: Check Ports ==========
function Test-PortInUse($port) {
    try { return $null -ne (Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue) }
    catch { return $false }
}

if (Test-PortInUse $BackendPort) {
    Write-Warn "Port $BackendPort is already in use"
}
if ((-not $SkipFrontend) -and (Test-PortInUse $FrontendPort)) {
    Write-Warn "Port $FrontendPort is already in use"
}

# ========== Step 4: Check Node.js (if needed) ==========
$HasNode = $false
if (-not $SkipFrontend) {
    try {
        $nodeVer = node --version 2>$null
        if ($nodeVer) {
            $HasNode = $true
            Write-OK "Node.js found: $nodeVer"
        }
    } catch {}
    
    if (-not $HasNode) {
        Write-Warn "Node.js not found, will start backend only"
        Write-Host "       To install: https://nodejs.org" -ForegroundColor Gray
        $SkipFrontend = $true
    }
}

Write-Host ""

# ========== Step 5: Start Backend ==========
Write-Info "Starting Backend Service..."
Write-Host "       Port: $BackendPort"
Write-Host "       URL:  http://localhost:$BackendPort"
Write-Host ""

# Build backend command - use cmd.exe with proper quoting
$backendCmdLine = "cd /d `"$BackendPath`" && call `"$VenvActivate`" && python main.py"

Start-Process cmd.exe -ArgumentList "/k", $backendCmdLine -WindowStyle Normal

# Wait for backend
Write-Info "Waiting for backend to start (5 seconds)..."
for ($i = 5; $i -gt 0; $i--) {
    Write-Host "       $i..." -ForegroundColor Gray
    Start-Sleep -Seconds 1
}

# Test if backend is responding
try {
    $response = Invoke-WebRequest -Uri "http://localhost:$BackendPort/health" -Method GET -TimeoutSec 3 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        Write-OK "Backend is responding"
    }
} catch {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$BackendPort/docs" -Method GET -TimeoutSec 3 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-OK "Backend is responding"
        }
    } catch {
        Write-Warn "Backend may still be starting..."
    }
}

Write-Host ""

# ========== Step 6: Start Frontend ==========
if (-not $SkipFrontend) {
    Write-Info "Starting Frontend Service..."
    Write-Host "       Port: $FrontendPort"
    Write-Host "       URL:  http://localhost:$FrontendPort"
    Write-Host ""
    
    $frontendCmdLine = "cd /d `"$FrontendPath`" && npm run dev"
    
    Start-Process cmd.exe -ArgumentList "/k", $frontendCmdLine -WindowStyle Normal
    
    Write-Info "Waiting for frontend to start (5 seconds)..."
    for ($i = 5; $i -gt 0; $i--) {
        Write-Host "       $i..." -ForegroundColor Gray
        Start-Sleep -Seconds 1
    }
    
    Write-Host ""
}

# ========== Step 7: Open Browser ==========
if (-not $NoBrowser) {
    $url = if ($SkipFrontend) { "http://localhost:$BackendPort/docs" } else { "http://localhost:$FrontendPort" }
    Write-Info "Opening browser: $url"
    Start-Process $url
}

# ========== Summary ==========
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "   All Services Started!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backend API:    http://localhost:$BackendPort"
Write-Host "API Docs:       http://localhost:$BackendPort/docs"
if (-not $SkipFrontend) {
    Write-Host "Frontend:       http://localhost:$FrontendPort"
}
Write-Host ""
Write-Host "Note: Close the service windows to stop" -ForegroundColor Yellow
Write-Host "========================================"
Write-Host ""

pause
