# SmartAM_System Environment Setup Script
param([switch]$SkipNode, [switch]$Force)

$ErrorActionPreference = "Stop"
$ProjectRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Get-Location }
Set-Location $ProjectRoot

# Paths
$VenvPath = Join-Path $ProjectRoot "venv"
$BackendPath = Join-Path $ProjectRoot "backend"
$FrontendPath = Join-Path $ProjectRoot "frontend"

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-OK($msg) { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red }

Clear-Host
Write-Host "========================================"
Write-Host "   SmartAM_System Environment Setup"
Write-Host "========================================"
Write-Host ""

# ========== Check Python ==========
Write-Info "Checking Python installation..."

try {
    $pyVer = python --version 2>&1
    if ($pyVer -match "Python 3\.(\d+)") {
        $minor = [int]$matches[1]
        if ($minor -ge 8) {
            Write-OK "$pyVer"
        } else {
            Write-Err "Python 3.8+ required, found: $pyVer"
            pause
            exit 1
        }
    } else {
        throw "Python not found"
    }
} catch {
    Write-Err "Python not found!"
    Write-Host "Please install Python 3.8+ from https://python.org"
    Write-Host "Make sure to check 'Add Python to PATH' during installation"
    pause
    exit 1
}

# ========== Create Virtual Environment ==========
Write-Host ""
Write-Info "Setting up Python virtual environment..."

if ((Test-Path $VenvPath) -and (-not $Force)) {
    Write-OK "Virtual environment already exists (use -Force to recreate)"
} else {
    if (Test-Path $VenvPath) {
        Write-Info "Removing old virtual environment..."
        Remove-Item -Recurse -Force $VenvPath
    }
    
    Write-Info "Creating virtual environment..."
    python -m venv $VenvPath
    
    if (-not (Test-Path $VenvPath)) {
        Write-Err "Failed to create virtual environment"
        pause
        exit 1
    }
    Write-OK "Virtual environment created"
}

$VenvPython = Join-Path $VenvPath "Scripts\python.exe"

# ========== Upgrade pip ==========
Write-Host ""
Write-Info "Upgrading pip..."
& $VenvPython -m pip install --upgrade pip | Out-Null
Write-OK "pip upgraded"

# ========== Install Python Dependencies ==========
Write-Host ""
Write-Info "Installing Python dependencies..."
Write-Host "       (This may take a few minutes...)"
Write-Host ""

$reqFile = Join-Path $BackendPath "requirements.txt"
if (Test-Path $reqFile) {
    & $VenvPython -m pip install -r $reqFile
    if ($?) {
        Write-OK "Python dependencies installed"
    } else {
        Write-Warn "Some packages may have failed to install"
    }
} else {
    Write-Warn "requirements.txt not found"
}

# ========== Check/Install Node.js ==========
Write-Host ""
Write-Info "Checking Node.js..."

$hasNode = $false
try {
    $nodeVer = node --version 2>$null
    $npmVer = npm --version 2>$null
    if ($nodeVer -and $npmVer) {
        $hasNode = $true
        Write-OK "Node.js $nodeVer, npm $npmVer"
    }
} catch {}

if (-not $hasNode) {
    Write-Warn "Node.js not found!"
    Write-Host ""
    Write-Host "Frontend will not work without Node.js."
    Write-Host "Download from: https://nodejs.org"
    Write-Host ""
    
    if (-not $SkipNode) {
        Write-Host "Options:"
        Write-Host "  1. Install Node.js now (opens browser)"
        Write-Host "  2. Continue without Node.js (backend only)"
        Write-Host "  3. Exit and install later"
        Write-Host ""
        
        $choice = Read-Host "Enter choice (1/2/3)"
        
        switch ($choice) {
            "1" { 
                Start-Process "https://nodejs.org"
                Write-Host ""
                Write-Host "Please install Node.js and run setup again."
                pause
                exit 0
            }
            "2" { 
                $SkipNode = $true
                Write-Host "Continuing without Node.js..."
            }
            default { 
                exit 0 
            }
        }
    }
}

# ========== Install Frontend Dependencies ==========
if ($hasNode -and (-not $SkipNode)) {
    Write-Host ""
    Write-Info "Installing frontend dependencies..."
    Write-Host "       (This may take a few minutes...)"
    Write-Host ""
    
    Push-Location $FrontendPath
    npm install
    $npmResult = $?
    Pop-Location
    
    if ($npmResult) {
        Write-OK "Frontend dependencies installed"
    } else {
        Write-Warn "npm install may have encountered issues"
    }
}

# ========== Summary ==========
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "   Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Virtual Environment: $VenvPath"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  - Run 'start.bat' to start services"
Write-Host ""

if (-not $hasNode) {
    Write-Host "Note: Install Node.js for frontend support"
    Write-Host "      https://nodejs.org"
}

Write-Host ""
pause
