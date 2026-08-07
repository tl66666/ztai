@echo off
cd /d "%~dp0"
title JobHunter Launcher

echo.
echo  ============================================
echo    JobHunter Launcher
echo  ============================================
echo.

REM ========== Check zhitu.ps1 ==========
if not exist "%~dp0zhitu.ps1" (
    echo  [ERROR] zhitu.ps1 not found
    echo          Location: %~dp0
    echo.
    pause
    exit /b 1
)

REM ========== Find PowerShell ==========
set "PS_EXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS_EXE%" set "PS_EXE=%SystemRoot%\SysWOW64\WindowsPowerShell\v1.0\powershell.exe"

if not exist "%PS_EXE%" (
    echo  [ERROR] PowerShell not found
    echo          Please install Windows PowerShell 5.0+
    echo.
    pause
    exit /b 1
)

echo  PowerShell: %PS_EXE%
echo  Script:     %~dp0zhitu.ps1
echo.

REM ========== Run zhitu.ps1 ==========
"%PS_EXE%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0zhitu.ps1" menu

echo.
echo  ============================================
echo  Script finished. Press any key to close.
echo  ============================================
pause >nul
