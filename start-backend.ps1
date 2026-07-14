<#
.SYNOPSIS
    Start the backend server (port 8001)
.DESCRIPTION
    Starts uvicorn on port 8001. Tracks PID to avoid duplicates.
    Waits for health check before reporting success.
#>

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$BackendDir = Join-Path $Root "backend"
$LogsDir = Join-Path $Root "logs"
$VenvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
$PidFile = Join-Path $Root ".backend.pid"
$StdoutLog = Join-Path $LogsDir "backend.log"
$StderrLog = Join-Path $LogsDir "backend_error.log"

if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

# Check venv exists
if (-not (Test-Path $VenvPython)) {
    Write-Host "ERROR: Python venv not found at $VenvPython" -ForegroundColor Red
    Write-Host "  Run .\setup.ps1 first" -ForegroundColor Yellow
    exit 1
}

# Check if already running
if (Test-Path $PidFile) {
    $existingPid = (Get-Content $PidFile -Raw).Trim()
    $proc = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
    if ($proc -and $proc.Path -like "*python*") {
        Write-Host "Backend already running (PID $existingPid)" -ForegroundColor Yellow
        exit 0
    } else {
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    }
}

# Check port: only block if an actual process is listening
$portListener = Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue
if ($portListener) {
    $listenerPid = $portListener.OwningProcess
    $listenerProc = Get-Process -Id $listenerPid -ErrorAction SilentlyContinue
    if ($listenerProc) {
        Write-Host "Port 8001 already in use by PID $listenerPid ($($listenerProc.ProcessName))." -ForegroundColor Red
        Write-Host "  Run .\stop-app.ps1 first, or kill the process manually." -ForegroundColor Yellow
        exit 1
    }
    # Ghost listener (PID dead) - OS will reclaim on bind
}

# Check MongoDB
$mongoListening = Get-NetTCPConnection -LocalPort 27017 -State Listen -ErrorAction SilentlyContinue
if (-not $mongoListening) {
    Write-Host "WARNING: MongoDB not detected on port 27017" -ForegroundColor Yellow
}

# Start backend
Write-Host "Starting backend on http://127.0.0.1:8001 ..." -ForegroundColor Cyan
$process = Start-Process -FilePath $VenvPython `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8001" `
    -WorkingDirectory $BackendDir `
    -WindowStyle Hidden `
    -PassThru `
    -RedirectStandardOutput $StdoutLog `
    -RedirectStandardError $StderrLog

$process.Id | Out-File -FilePath $PidFile -NoNewline

# Wait for health check
$maxWait = 30
$waited = 0
Start-Sleep -Seconds 3
while ($waited -lt $maxWait) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8001/health" -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) {
            Write-Host "Backend started (PID $($process.Id))" -ForegroundColor Green
            exit 0
        }
    } catch {}
    Start-Sleep -Seconds 1
    $waited++
}

# Health check failed - show last error lines
Write-Host "Backend health check timed out after ${maxWait}s" -ForegroundColor Red
Write-Host "  Last errors from $StderrLog:" -ForegroundColor Yellow
if (Test-Path $StderrLog) {
    Get-Content $StderrLog -Tail 20 -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Host "    $_" -ForegroundColor DarkGray
    }
}
exit 1
