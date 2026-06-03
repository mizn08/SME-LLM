# Download Flutter SDK into repo root (scripts/../flutter) - matches GitHub Actions 3.24.5
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
$zipPath = Join-Path $env:TEMP "flutter_windows_3.24.5-stable-$PID.zip"

# Remove stale partial downloads from earlier attempts (ignore if locked)
Get-ChildItem "$env:TEMP\flutter_windows_3.24.5-stable*.zip" -ErrorAction SilentlyContinue | ForEach-Object {
    try { Remove-Item $_.FullName -Force -ErrorAction Stop } catch { }
}

Write-Host "Downloading Flutter 3.24.5 (~1 GB). This may take 10-20 minutes..." -ForegroundColor Cyan
Write-Host "Saving to: $zipPath" -ForegroundColor DarkGray

$ProgressPreference = 'SilentlyContinue'
try {
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing
} catch {
    throw "Download failed: $($_.Exception.Message). Close other PowerShell windows and run this script again."
}

if (-not (Test-Path $zipPath)) {
    throw "Download failed - zip file not created."
}

$sizeMb = [math]::Round((Get-Item $zipPath).Length / 1MB, 1)
Write-Host "Downloaded $sizeMb MB. Extracting to $root ..." -ForegroundColor Cyan
Expand-Archive -Path $zipPath -DestinationPath $root -Force
Remove-Item $zipPath -Force -ErrorAction SilentlyContinue

if (-not (Test-Path $flutterBat)) {
    throw "Flutter install failed - flutter.bat not found at $flutterBat"
}

Write-Host "Running flutter doctor (first run may download Dart SDK)..." -ForegroundColor Cyan
& $flutterBat doctor
Write-Host ""
Write-Host "Done. Next: .\scripts\run_local_all.ps1" -ForegroundColor Green
