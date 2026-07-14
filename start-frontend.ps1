<#
.SYNOPSIS
    Start the frontend dev server (port 3000)
.DESCRIPTION
    Starts Next.js dev server on port 3000. Tracks PID to avoid duplicates.
#>

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$FrontendDir = Join-Path $Root "frontend"
$LogsDir = Join-Path $Root "logs"
$PidFile = Join-Path $Root ".frontend.pid"
$StdoutLog = Join-Path $LogsDir "frontend.log"
$StderrLog = Join-Path $LogsDir "frontend_error.log"

if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

# Check if already running
if (Test-Path $PidFile) {
    $existingPid = (Get-Content $PidFile -Raw).Trim()
    $proc = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
    if ($proc -and $proc.Path -like "*node*") {
        Write-Host "Frontend already running (PID $existingPid)" -ForegroundColor Yellow
        exit 0
    } else {
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    }
}

# Check port: only block if an actual process is listening
$portListener = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
if ($portListener) {
    $listenerPid = $portListener.OwningProcess
    $listenerProc = Get-Process -Id $listenerPid -ErrorAction SilentlyContinue
    if ($listenerProc) {
        Write-Host "Port 3000 already in use by PID $listenerPid ($($listenerProc.ProcessName))." -ForegroundColor Red
        Write-Host "  Run .\stop-app.ps1 first, or kill the process manually." -ForegroundColor Yellow
        exit 1
    }
    # Ghost listener (PID dead) - OS will reclaim on bind
}

# Resolve npm.cmd
$npmCmd = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
if (-not $npmCmd) {
    Write-Host "ERROR: npm.cmd not found. Install Node.js and ensure npm is in your PATH." -ForegroundColor Red
    exit 1
}

# Start frontend
Write-Host "Starting frontend on http://localhost:3000 ..." -ForegroundColor Cyan
$process = Start-Process -FilePath $npmCmd `
    -ArgumentList "run", "dev" `
    -WorkingDirectory $FrontendDir `
    -WindowStyle Hidden `
    -PassThru `
    -RedirectStandardOutput $StdoutLog `
    -RedirectStandardError $StderrLog

$process.Id | Out-File -FilePath $PidFile -NoNewline

# Wait for ready
$maxWait = 30
$waited = 0
Start-Sleep -Seconds 5
while ($waited -lt $maxWait) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) {
            Write-Host "Frontend started (PID $($process.Id))" -ForegroundColor Green
            exit 0
        }
    } catch {}
    Start-Sleep -Seconds 1
    $waited++
}

# Readiness failed
Write-Host "Frontend readiness check timed out after ${maxWait}s" -ForegroundColor Red
Write-Host "  Last errors from $StderrLog:" -ForegroundColor Yellow
if (Test-Path $StderrLog) {
    Get-Content $StderrLog -Tail 20 -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Host "    $_" -ForegroundColor DarkGray
    }
}
exit 1
