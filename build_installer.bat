@echo off
REM Build script for Red Alert installer
REM This script creates a standalone executable and installer

setlocal enabledelayedexpansion

echo.
echo ============================================
echo   Red Alert Application Builder
echo ============================================
echo.

REM Check if Python is available
python --version > nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org
    echo.
    pause
    exit /b 1
)

echo Python found. Installing dependencies...
echo.

REM Install PyInstaller if not already installed
python -m pip install pyinstaller -q
if errorlevel 1 (
    echo ERROR: Failed to install PyInstaller
    pause
    exit /b 1
)

REM Install project requirements
echo Installing application dependencies...
python -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo ERROR: Failed to install project dependencies
    echo Make sure requirements.txt exists
    pause
    exit /b 1
)

REM Clean previous builds
if exist build (
    echo Cleaning previous build...
    rmdir /s /q build > nul 2>&1
)
if exist dist (
    echo Cleaning previous dist...
    rmdir /s /q dist > nul 2>&1
)

mkdir build > nul 2>&1
mkdir dist > nul 2>&1

echo.
echo Running PyInstaller...
echo This may take a minute...
echo.

REM Run PyInstaller with or without icon
if exist icon.ico (
    echo Using icon.ico...
    python -m PyInstaller --name "Red Alert" --onefile --windowed --icon=icon.ico --add-data "oref_alert;oref_alert" main.py
) else (
    echo No icon.ico found, building without icon...
    python -m PyInstaller --name "Red Alert" --onefile --windowed --add-data "oref_alert;oref_alert" main.py
)

if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed!
    echo Please check the error messages above
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Build Successful!
echo ============================================
echo.
echo Executable created at:
echo   dist\Red Alert.exe
echo.
echo Next steps to create the installer:
echo.
echo   1. Download NSIS from: https://nsis.sourceforge.io
echo   2. Install NSIS
echo   3. Open NSIS
echo   4. Click "Compile NSI Scripts"
echo   5. Select: RedAlert_Installer.nsi
echo   6. Click "Compile"
echo.
echo The installer will be created at:
echo   dist\RedAlert_Setup_1.0.0.exe
echo.
pause
