# Start backend + Flutter web (two windows). Run from repo root.
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent

$flutterBat = Join-Path $root "flutter\bin\flutter.bat"
if (-not (Test-Path $flutterBat)) {
    Write-Host "Installing Flutter first..." -ForegroundColor Yellow
    & (Join-Path $PSScriptRoot "install_flutter.ps1")
}

Write-Host "Opening backend in new window..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $root "backend\run_local.ps1")

Start-Sleep -Seconds 4

Write-Host "Opening Flutter web in new window..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "run_local_web.ps1")

Write-Host "Wait ~30s for Chrome to open. Menu -> Sales Engineer for agentic quote demo." -ForegroundColor Green
