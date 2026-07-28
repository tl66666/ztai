@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
title 职途AI - 一键管理工具
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0zhitu.ps1" menu
if %ERRORLEVEL% neq 0 (
    echo.
    echo [错误] 脚本执行失败，请检查 PowerShell 环境
    pause
)
