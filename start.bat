@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-jobhunter.ps1" %*
set "EXIT_CODE=%errorlevel%"
if not "%EXIT_CODE%"=="0" (
  echo.
  echo Startup failed. See output\runtime\launcher.log for details.
  if "%~1"=="" pause
)
exit /b %EXIT_CODE%
