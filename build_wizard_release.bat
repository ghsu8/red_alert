@echo off
REM Manual release builder wrapper.
REM Runs only when explicitly executed.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_wizard_release.ps1"
exit /b %errorlevel%
