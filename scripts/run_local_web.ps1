# Run Flutter web locally against local API (http://127.0.0.1:8000)
# Prerequisite: backend running — cd backend && .\run_local.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$flutterBat = Join-Path $root "flutter\bin\flutter.bat"
if (-not (Test-Path $flutterBat)) {
    Write-Host "Flutter not found. Run first: .\scripts\install_flutter.ps1" -ForegroundColor Yellow
    exit 1
}

$mobile = Join-Path $root "mobile_app"
Set-Location $mobile

Write-Host "API: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "Starting Flutter web in Chrome..." -ForegroundColor Cyan
& $flutterBat pub get
& $flutterBat run -d chrome --dart-define=API_BASE=http://localhost:8000
