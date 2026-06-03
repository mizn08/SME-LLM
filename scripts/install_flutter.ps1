# Download Flutter SDK into repo root (scripts/../flutter) — matches GitHub Actions 3.24.5
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$flutterDir = Join-Path $root "flutter"
$flutterBat = Join-Path $flutterDir "bin\flutter.bat"

if (Test-Path $flutterBat) {
    Write-Host "Flutter already installed at $flutterDir" -ForegroundColor Green
    & $flutterBat --version
    exit 0
}

$zipUrl = "https://storage.googleapis.com/flutter_infra_release/releases/stable/windows/flutter_windows_3.24.5-stable.zip"
$zipPath = Join-Path $env:TEMP "flutter_windows_3.24.5-stable.zip"

Write-Host "Downloading Flutter 3.24.5 (~1 GB). This may take several minutes..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing

Write-Host "Extracting to $root ..." -ForegroundColor Cyan
Expand-Archive -Path $zipPath -DestinationPath $root -Force
Remove-Item $zipPath -Force -ErrorAction SilentlyContinue

if (-not (Test-Path $flutterBat)) {
    throw "Flutter install failed - flutter.bat not found at $flutterBat"
}

Write-Host "Running flutter doctor (first run may download Dart SDK)..." -ForegroundColor Cyan
& $flutterBat doctor
Write-Host "`nDone. Use: .\scripts\run_local_web.ps1" -ForegroundColor Green
