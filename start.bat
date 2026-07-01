@echo off
REM ============================================================
REM  JobHunter AI - One-Click Launcher
REM  Double-click this file to start the application.
REM  Press Ctrl+C in the window to stop the service.
REM ============================================================
chcp 65001 >nul 2>&1
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-jobhunter.ps1"
pause
