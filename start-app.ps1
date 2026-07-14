<#
.SYNOPSIS
    Start the full application (backend + frontend)
.DESCRIPTION
    Main entry point. Checks prerequisites, starts backend on port 8001 and
    frontend on port 3000. Tracks PIDs, avoids duplicate processes, verifies
    services are ready.
    Usage: .\start-app.ps1
    Stop:  .\stop-app.ps1
#>

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$LogsDir = Join-Path $Root "logs"
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$BackendPidFile = Join-Path $Root ".backend.pid"
$FrontendPidFile = Join-Path $Root ".frontend.pid"
$BackendStdoutLog = Join-Path $LogsDir "backend.log"
$BackendStderrLog = Join-Path $LogsDir "backend_error.log"
$FrontendStdoutLog = Join-Path $LogsDir "frontend.log"
$FrontendStderrLog = Join-Path $LogsDir "frontend_error.log"

# Ensure logs directory exists
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

# Track what we started so we can clean up on failure
$startedBackend = $false
$startedFrontend = $false

function Stop-StartedServices {
    if ($startedFrontend) {
        if (Test-Path $FrontendPidFile) {
            $fp = (Get-Content $FrontendPidFile -Raw).Trim()
            $p = Get-Process -Id $fp -ErrorAction SilentlyContinue
            if ($p) { Stop-Process -Id $fp -Force -ErrorAction SilentlyContinue }
            Remove-Item $FrontendPidFile -Force -ErrorAction SilentlyContinue
        }
    }
    if ($startedBackend) {
        if (Test-Path $BackendPidFile) {
            $bp = (Get-Content $BackendPidFile -Raw).Trim()
            $p = Get-Process -Id $bp -ErrorAction SilentlyContinue
            if ($p) { Stop-Process -Id $bp -Force -ErrorAction SilentlyContinue }
            Remove-Item $BackendPidFile -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Autonomous Computer Operator - Starting" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ---- Stage 1: Verify prerequisites ----
Write-Host "[1/5] Checking prerequisites..." -ForegroundColor Yellow

# Check Python venv
$VenvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "  ERROR: Python venv not found at $VenvPython" -ForegroundColor Red
    Write-Host "  Run .\setup.ps1 first." -ForegroundColor Yellow
    exit 1
}
Write-Host "  Python venv: OK" -ForegroundColor Green

# Check npm
$npmCmd = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
if (-not $npmCmd) {
    Write-Host "  ERROR: npm.cmd not found. Ensure Node.js is installed and in PATH." -ForegroundColor Red
    exit 1
}
Write-Host "  npm: OK" -ForegroundColor Green

# Check MongoDB
$mongoOk = Get-NetTCPConnection -LocalPort 27017 -State Listen -ErrorAction SilentlyContinue
if ($mongoOk) {
    Write-Host "  MongoDB (27017): OK" -ForegroundColor Green
} else {
    Write-Host "  WARNING: MongoDB not detected on port 27017" -ForegroundColor Yellow
    Write-Host "  Backend may fail to start if MongoDB is required." -ForegroundColor Yellow
}

# Check Ollama
$ollamaOk = $false
try {
    $tags = Invoke-RestMethod http://localhost:11434/api/tags -TimeoutSec 3
    $ollamaOk = $true
    Write-Host "  Ollama (11434): OK" -ForegroundColor Green
} catch {
    Write-Host "  WARNING: Ollama not detected on port 11434" -ForegroundColor Yellow
}

# Check required model
if ($ollamaOk) {
    $hasModel = $tags.models | Where-Object { $_.name -eq "qwen2.5-coder:7b" }
    if ($hasModel) {
        Write-Host "  Model qwen2.5-coder:7b: OK" -ForegroundColor Green
    } else {
        Write-Host "  WARNING: Model qwen2.5-coder:7b not found. Pulling will be needed." -ForegroundColor Yellow
        Write-Host "  Run: ollama pull qwen2.5-coder:7b" -ForegroundColor Yellow
    }
}

# Clear stale PID files
foreach ($pf in @($BackendPidFile, $FrontendPidFile)) {
    if (Test-Path $pf) {
        $stalePid = (Get-Content $pf -Raw).Trim()
        $staleProc = Get-Process -Id $stalePid -ErrorAction SilentlyContinue
        if (-not $staleProc) {
            Remove-Item $pf -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Host ""

# ---- Stage 2: Check ports ----
Write-Host "[2/5] Checking ports..." -ForegroundColor Yellow

$portIssues = @()
foreach ($portInfo in @(@{Port=8001; Name="Backend"}, @{Port=3000; Name="Frontend"})) {
    $port = $portInfo.Port
    $name = $portInfo.Name
    $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($listener) {
        $lp = $listener.OwningProcess
        $lpProc = Get-Process -Id $lp -ErrorAction SilentlyContinue
        if ($lpProc) {
            $portIssues += "$name port $port is in use by PID $lp ($($lpProc.ProcessName))"
        }
        # Ghost listener is OK - OS will reclaim
    }
}

if ($portIssues.Count -gt 0) {
    Write-Host "  Port conflicts:" -ForegroundColor Red
    foreach ($issue in $portIssues) {
        Write-Host "    $issue" -ForegroundColor Red
    }
    Write-Host "  Run .\stop-app.ps1 first." -ForegroundColor Yellow
    exit 1
}
Write-Host "  Ports 8001 and 3000: OK" -ForegroundColor Green
Write-Host ""

# ---- Stage 3: Start backend ----
Write-Host "[3/5] Starting backend..." -ForegroundColor Yellow
Write-Host "  Command: uvicorn app.main:app --host 127.0.0.1 --port 8001" -ForegroundColor DarkGray

$backendProcess = Start-Process -FilePath $VenvPython `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8001" `
    -WorkingDirectory $BackendDir `
    -WindowStyle Hidden `
    -PassThru `
    -RedirectStandardOutput $BackendStdoutLog `
    -RedirectStandardError $BackendStderrLog

$backendProcess.Id | Out-File -FilePath $BackendPidFile -NoNewline
$startedBackend = $true

# Wait for health check
$backendReady = $false
$maxWait = 30
$waited = 0
Start-Sleep -Seconds 3
while ($waited -lt $maxWait) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8001/health" -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) {
            $backendReady = $true
            break
        }
    } catch {}
    Start-Sleep -Seconds 1
    $waited++
}

if (-not $backendReady) {
    Write-Host "  FAILED: Backend health check timed out after ${maxWait}s" -ForegroundColor Red
    Write-Host "  Log: $BackendStderrLog" -ForegroundColor Yellow
    Stop-StartedServices
    exit 1
}
Write-Host "  Backend started (PID $($backendProcess.Id))" -ForegroundColor Green
Write-Host ""

# ---- Stage 4: Start frontend ----
Write-Host "[4/5] Starting frontend..." -ForegroundColor Yellow
Write-Host "  Command: npm run dev" -ForegroundColor DarkGray

$frontendProcess = Start-Process -FilePath $npmCmd `
    -ArgumentList "run", "dev" `
    -WorkingDirectory $FrontendDir `
    -WindowStyle Hidden `
    -PassThru `
    -RedirectStandardOutput $FrontendStdoutLog `
    -RedirectStandardError $FrontendStderrLog

$frontendProcess.Id | Out-File -FilePath $FrontendPidFile -NoNewline
$startedFrontend = $true

# Wait for ready
$frontendReady = $false
$maxWait = 40
$waited = 0
Start-Sleep -Seconds 5
while ($waited -lt $maxWait) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) {
            $frontendReady = $true
            break
        }
    } catch {}
    Start-Sleep -Seconds 1
    $waited++
}

if (-not $frontendReady) {
    Write-Host "  FAILED: Frontend readiness check timed out after ${maxWait}s" -ForegroundColor Red
    Write-Host "  Log: $FrontendStderrLog" -ForegroundColor Yellow
    Stop-StartedServices
    exit 1
}
Write-Host "  Frontend started (PID $($frontendProcess.Id))" -ForegroundColor Green
Write-Host ""

# ---- Stage 5: Verify ----
Write-Host "[5/5] Verifying services..." -ForegroundColor Yellow

# Final health checks
$finalBackend = $false
$finalFrontend = $false
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:8001/health" -UseBasicParsing -TimeoutSec 3
    if ($r.StatusCode -eq 200) { $finalBackend = $true }
} catch {}
try {
    $r = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 3
    if ($r.StatusCode -eq 200) { $finalFrontend = $true }
} catch {}

if ($finalBackend -and $finalFrontend) {
    Write-Host "  All services verified" -ForegroundColor Green
} else {
    if (-not $finalBackend) { Write-Host "  WARNING: Backend health check failed on final verify" -ForegroundColor Yellow }
    if (-not $finalFrontend) { Write-Host "  WARNING: Frontend check failed on final verify" -ForegroundColor Yellow }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Application is running!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Backend:   http://127.0.0.1:8001" -ForegroundColor White
Write-Host " Frontend:  http://localhost:3000" -ForegroundColor White
Write-Host " API docs:  http://127.0.0.1:8001/docs" -ForegroundColor White
Write-Host " Logs:      $LogsDir" -ForegroundColor White
Write-Host " Stop:      .\stop-app.ps1" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Cyan
