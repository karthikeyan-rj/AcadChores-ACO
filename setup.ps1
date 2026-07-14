<#
.SYNOPSIS
    First-time setup for Autonomous Computer Operator
.DESCRIPTION
    Installs Python 3.12, creates venv, installs deps, installs Playwright browsers,
    generates secure secrets, installs frontend deps.
    Run once before starting the app for the first time.
#>

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$LogsDir = Join-Path $Root "logs"
$VenvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
$VenvPip = Join-Path $BackendDir ".venv\Scripts\pip.exe"

if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Autonomous Computer Operator - Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# --- Step 1: Check Python 3.12 ---
Write-Host "[1/7] Checking Python 3.12..." -ForegroundColor Yellow
$python312 = $null
try {
    $pyVersion = & python --version 2>&1
    if ($pyVersion -match "Python 3\.12") {
        $python312 = "python"
        Write-Host "  Found Python 3.12 via 'python' command" -ForegroundColor Green
    }
} catch {}
if (-not $python312) {
    try {
        $pyVersion = & py -3.12 --version 2>&1
        if ($pyVersion -match "Python 3\.12") {
            $python312 = "py -3.12"
            Write-Host "  Found Python 3.12 via 'py -3.12'" -ForegroundColor Green
        }
    } catch {}
}
if (-not $python312) {
    Write-Host "  Python 3.12 not found. Installing via winget..." -ForegroundColor Yellow
    winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
    $python312 = "python"
}

# --- Step 2: Create venv ---
Write-Host "[2/7] Creating backend virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path $VenvPython)) {
    Push-Location $BackendDir
    & $python312 -m venv .venv
    Pop-Location
    Write-Host "  Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "  Virtual environment already exists" -ForegroundColor Green
}

# --- Step 3: Install backend dependencies ---
Write-Host "[3/7] Installing backend dependencies..." -ForegroundColor Yellow
& $VenvPip install --upgrade pip 2>&1 | Out-Null
& $VenvPip install -r (Join-Path $BackendDir "requirements.txt") 2>&1 | Out-Null
& $VenvPip install pytest pytest-asyncio pytest-cov 2>&1 | Out-Null
Write-Host "  Dependencies installed" -ForegroundColor Green

# --- Step 4: Install Playwright browsers ---
Write-Host "[4/7] Installing Playwright Chromium browser..." -ForegroundColor Yellow
& $VenvPython -m playwright install chromium 2>&1 | Out-Null
Write-Host "  Playwright browsers installed" -ForegroundColor Green

# --- Step 5: Generate secure secrets if needed ---
Write-Host "[5/7] Configuring backend .env..." -ForegroundColor Yellow
$envFile = Join-Path $BackendDir ".env"
$envExample = Join-Path $BackendDir ".env.example"
if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Write-Host "  Copied .env.example to .env" -ForegroundColor Green
    } else {
        Write-Host "  ERROR: No .env or .env.example found" -ForegroundColor Red
        exit 1
    }
}
$envContent = Get-Content $envFile -Raw
if ($envContent -match "SECRET_KEY=dev-secret-key-change-in-production") {
    $secretKey = & $VenvPython -c "import secrets; print(secrets.token_hex(32))"
    $credKey = & $VenvPython -c "import secrets; print(secrets.token_urlsafe(32))"
    $envContent = $envContent -replace "SECRET_KEY=dev-secret-key-change-in-production", "SECRET_KEY=$secretKey"
    $envContent = $envContent -replace "CREDENTIAL_ENCRYPTION_KEY=", "CREDENTIAL_ENCRYPTION_KEY=$credKey"
    Set-Content -Path $envFile -Value $envContent
    Write-Host "  Generated secure SECRET_KEY and CREDENTIAL_ENCRYPTION_KEY" -ForegroundColor Green
} else {
    Write-Host "  .env already has secure secrets" -ForegroundColor Green
}

# --- Step 6: Install frontend dependencies ---
Write-Host "[6/7] Installing frontend dependencies..." -ForegroundColor Yellow
$npmPath = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
if (-not $npmPath) {
    Write-Host "  ERROR: npm.cmd not found. Install Node.js and ensure npm is in your PATH." -ForegroundColor Red
    exit 1
}
Push-Location $FrontendDir
if (-not (Test-Path "node_modules")) {
    & $npmPath install 2>&1 | Out-Null
    Write-Host "  Frontend dependencies installed" -ForegroundColor Green
} else {
    Write-Host "  Frontend dependencies already installed" -ForegroundColor Green
}
Pop-Location

# --- Step 7: Build frontend ---
Write-Host "[7/7] Building frontend..." -ForegroundColor Yellow
Push-Location $FrontendDir
& $npmPath run build 2>&1 | Out-Null
Pop-Location
Write-Host "  Frontend built successfully" -ForegroundColor Green

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Setup complete!" -ForegroundColor Green
Write-Host " Run .\start-app.ps1 to start the app" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
