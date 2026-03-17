$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================"
Write-Host "  Red Alert Wizard Release Builder"
Write-Host "============================================"
Write-Host ""

$python = "python"
$makensisCandidates = @(
    "C:\Program Files (x86)\NSIS\makensis.exe",
    "C:\Program Files\NSIS\makensis.exe"
)

if (-not (Get-Command $python -ErrorAction SilentlyContinue)) {
    throw "Python is not installed or not in PATH"
}

$makensis = $makensisCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $makensis) {
    throw "NSIS (makensis.exe) not found. Install NSIS and rerun."
}

$initFile = Join-Path (Get-Location) "oref_alert\__init__.py"
if (-not (Test-Path $initFile)) {
    throw "Could not find oref_alert\\__init__.py"
}

$initText = Get-Content -Raw -Encoding UTF8 $initFile
$match = [regex]::Match($initText, '__version__\s*=\s*"([^"]+)"')
if ($match.Success) {
    $version = $match.Groups[1].Value.Trim()
} else {
    $version = "0.0.0"
}

if (-not $version) {
    throw "Could not read __version__ from oref_alert/__init__.py"
}

$releaseRoot = Join-Path (Get-Location) "releases\wizard"
$releaseDir = Join-Path $releaseRoot ("v" + $version)
if (Test-Path $releaseDir) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $releaseDir = Join-Path $releaseRoot ("v" + $version + "_" + $stamp)
}

New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null

Write-Host "Version: $version"
Write-Host "Output folder: $releaseDir"
Write-Host ""

Write-Host "Installing dependencies..."
& $python -m pip install -q pyinstaller
& $python -m pip install -q -r requirements.txt

Write-Host "Cleaning old build folders..."
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
New-Item -ItemType Directory -Path "build" | Out-Null
New-Item -ItemType Directory -Path "dist" | Out-Null

Write-Host "Building EXE with PyInstaller..."
if (Test-Path "icon.ico") {
    & $python -m PyInstaller --name "Red Alert" --onefile --windowed --icon=icon.ico --add-data "oref_alert;oref_alert" main.py
} else {
    & $python -m PyInstaller --name "Red Alert" --onefile --windowed --add-data "oref_alert;oref_alert" main.py
}

$exeSource = Join-Path (Get-Location) "dist\Red Alert.exe"
if (-not (Test-Path $exeSource)) {
    throw "Build succeeded but dist\Red Alert.exe was not found"
}

Copy-Item -Force $exeSource (Join-Path $releaseDir "Red Alert.exe")

Write-Host "Building installer wizard..."
& $makensis "/DPRODUCT_VERSION=$version" "/DOUTPUT_DIR=$releaseDir" "RedAlert_Installer.nsi"

$installerPath = Join-Path $releaseDir ("RedAlert_Setup_" + $version + ".exe")

Write-Host ""
Write-Host "============================================"
Write-Host "  Release Build Completed"
Write-Host "============================================"
Write-Host "EXE:       $releaseDir\Red Alert.exe"
Write-Host "Installer: $installerPath"
Write-Host ""
Write-Host "NOTE: This script is manual-only. No automatic release is created on code fixes."
Write-Host ""
