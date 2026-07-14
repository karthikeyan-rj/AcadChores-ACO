<#
.SYNOPSIS
    Stop the application (backend + frontend)
.DESCRIPTION
    Kills backend and frontend processes using tracked PIDs.
    Only kills processes owned by this application, never global Node/Python/MongoDB/Ollama.
#>

$ErrorActionPreference = "Continue"
$Root = $PSScriptRoot
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"

Write-Host "Stopping Autonomous Computer Operator..." -ForegroundColor Yellow

$stoppedAny = $false

# --- Stop backend (tracked PID) ---
$backendPidFile = Join-Path $Root ".backend.pid"
if (Test-Path $backendPidFile) {
    $backendPid = (Get-Content $backendPidFile -Raw).Trim()
    $proc = Get-Process -Id $backendPid -ErrorAction SilentlyContinue
    if ($proc -and $proc.Path -like "*python*") {
        Stop-Process -Id $backendPid -Force -ErrorAction SilentlyContinue
        Write-Host "  Backend stopped (PID $backendPid)" -ForegroundColor Green
        $stoppedAny = $true
    } elseif ($proc) {
        Write-Host "  Backend PID $backendPid is not a Python process (skipped)" -ForegroundColor Yellow
    } else {
        Write-Host "  Backend PID $backendPid already gone" -ForegroundColor Yellow
    }
    Remove-Item $backendPidFile -Force -ErrorAction SilentlyContinue
} else {
    Write-Host "  No backend PID file" -ForegroundColor DarkGray
}

# --- Stop frontend (tracked PID) ---
$frontendPidFile = Join-Path $Root ".frontend.pid"
if (Test-Path $frontendPidFile) {
    $frontendPid = (Get-Content $frontendPidFile -Raw).Trim()
    $proc = Get-Process -Id $frontendPid -ErrorAction SilentlyContinue
    if ($proc -and $proc.Path -like "*node*") {
        Stop-Process -Id $frontendPid -Force -ErrorAction SilentlyContinue
        Write-Host "  Frontend stopped (PID $frontendPid)" -ForegroundColor Green
        $stoppedAny = $true
    } elseif ($proc) {
        Write-Host "  Frontend PID $frontendPid is not a Node process (skipped)" -ForegroundColor Yellow
    } else {
        Write-Host "  Frontend PID $frontendPid already gone" -ForegroundColor Yellow
    }
    Remove-Item $frontendPidFile -Force -ErrorAction SilentlyContinue
} else {
    Write-Host "  No frontend PID file" -ForegroundColor DarkGray
}

# --- Kill orphaned uvicorn on port 8001 (only python processes) ---
$orphans8001 = Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue
foreach ($conn in $orphans8001) {
    $orphanPid = $conn.OwningProcess
    if ($orphanPid -and $orphanPid -ne 0) {
        $proc = Get-Process -Id $orphanPid -ErrorAction SilentlyContinue
        if ($proc -and $proc.Path -like "*python*") {
            Stop-Process -Id $orphanPid -Force -ErrorAction SilentlyContinue
            Write-Host "  Killed orphaned backend process (PID $orphanPid)" -ForegroundColor Green
            $stoppedAny = $true
        }
    }
}

# --- Kill orphaned node on port 3000 (only node processes) ---
$orphans3000 = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
foreach ($conn in $orphans3000) {
    $orphanPid = $conn.OwningProcess
    if ($orphanPid -and $orphanPid -ne 0) {
        $proc = Get-Process -Id $orphanPid -ErrorAction SilentlyContinue
        if ($proc -and $proc.Path -like "*node*") {
            Stop-Process -Id $orphanPid -Force -ErrorAction SilentlyContinue
            Write-Host "  Killed orphaned frontend process (PID $orphanPid)" -ForegroundColor Green
            $stoppedAny = $true
        }
    }
}

# --- Clean up log files ---
$logFiles = @("backend.log", "backend_error.log", "frontend.log", "frontend_error.log")
foreach ($lf in $logFiles) {
    $logPath = Join-Path $Root $lf
    if (Test-Path $logPath) {
        Remove-Item $logPath -Force -ErrorAction SilentlyContinue
    }
}

Write-Host ""
if ($stoppedAny) {
    Write-Host "Application stopped." -ForegroundColor Green
} else {
    Write-Host "Application was not running." -ForegroundColor DarkGray
}
