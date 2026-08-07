@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
title JobHunter Launcher

REM ========== Verify zhitu.ps1 exists ==========
if not exist "%~dp0zhitu.ps1" (
    echo.
    echo [ERROR] zhitu.ps1 not found in current directory
    echo         Current dir: %~dp0
    echo.
    pause
    exit /b 1
)

REM ========== Find PowerShell (Windows PowerShell 5.x is always here) ==========
set "PS_EXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS_EXE%" set "PS_EXE=%SystemRoot%\SysWOW64\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS_EXE%" (
    echo.
    echo [ERROR] PowerShell not found
    echo         Tried: %SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe
    echo         Tried: %SystemRoot%\SysWOW64\WindowsPowerShell\v1.0\powershell.exe
    echo         Please install Windows Management Framework 5.0+
    echo.
    pause
    exit /b 1
)

REM ========== Launch zhitu.ps1 ==========
"%PS_EXE%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0zhitu.ps1" menu
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] zhitu.ps1 exited with code %ERRORLEVEL%
    echo         PowerShell: %PS_EXE%
    echo.
    pause
)
