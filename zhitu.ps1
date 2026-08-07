#Requires -Version 5.0
<#
.SYNOPSIS
    职途 AI (JobHunter) 一键管理工具
.DESCRIPTION
    启动 / 停止 / 重启 / 状态查看，支持后端(FastAPI) + 前端(Vite) 统一管理
.NOTES
    双击 start.bat 即可使用，或命令行:
    powershell -ExecutionPolicy Bypass -File zhitu.ps1 start
    powershell -ExecutionPolicy Bypass -File zhitu.ps1 stop
    powershell -ExecutionPolicy Bypass -File zhitu.ps1 status
#>

param(
    [Parameter(Position = 0)]
    [ValidateSet('start', 'stop', 'restart', 'status', 'menu', 'open')]
    [string]$Action = 'menu'
)

# ========== 路径配置（全部使用相对路径） ==========
$Root        = $PSScriptRoot
$RunDir      = Join-Path $Root '.run'

# ========== PowerShell 可执行文件路径 ==========
$PowerShellExe = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
if (-not (Test-Path $PowerShellExe)) {
    $PowerShellExe = "$env:SystemRoot\SysWOW64\WindowsPowerShell\v1.0\powershell.exe"
}

# ========== 端口配置 ==========
$BackendPort  = 5000
$FrontendPort = 5173

# ========== PID 文件 ==========
$BackendPidFile  = Join-Path $RunDir 'backend.pid'
$FrontendPidFile = Join-Path $RunDir 'frontend.pid'

# ========== 初始化 ==========
if (-not (Test-Path $RunDir)) {
    New-Item -ItemType Directory -Path $RunDir -Force | Out-Null
}

# ========== 输出工具函数 ==========
function Write-Info($msg) { Write-Host "  [INFO] " -ForegroundColor DarkGray -NoNewline; Write-Host $msg -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "  [ OK ] " -ForegroundColor DarkGray -NoNewline; Write-Host $msg -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  [WARN] " -ForegroundColor DarkGray -NoNewline; Write-Host $msg -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "  [ERR ] " -ForegroundColor DarkGray -NoNewline; Write-Host $msg -ForegroundColor Red }

# ========== 环境检测 ==========
function Test-Command($cmd) {
    return [bool](Get-Command $cmd -ErrorAction SilentlyContinue)
}

function Get-PortProcess($port) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
        return Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
    }
    return $null
}

# 查找 Python 3.11+
function Find-Python {
    # 优先使用 py launcher
    if (Test-Command 'py') {
        $pyVer = py -0p 2>$null
        if ($pyVer -match '3\.(1[1-9]|[2-9]\d)') {
            return 'py'
        }
    }
    # 尝试 python3.12 / python3.13
    foreach ($cmd in @('python3.12', 'python3.13', 'python3.11')) {
        if (Test-Command $cmd) {
            return $cmd
        }
    }
    # 检查默认 python 版本
    if (Test-Command 'python') {
        $ver = python --version 2>&1
        if ($ver -match '3\.(1[1-9]|[2-9]\d)') {
            return 'python'
        }
    }
    # 检查常见 Windows 安装路径
    $userLocal = [Environment]::GetFolderPath('LocalApplicationData')
    $searchPaths = @(
        "$userLocal\Programs\Python\Python313\python.exe",
        "$userLocal\Programs\Python\Python312\python.exe",
        "$userLocal\Programs\Python\Python311\python.exe",
        'C:\Python313\python.exe',
        'C:\Python312\python.exe',
        'C:\Python311\python.exe'
    )
    foreach ($p in $searchPaths) {
        if (Test-Path $p) {
            $ver = & $p --version 2>&1
            if ($ver -match '3\.(1[1-9]|[2-9]\d)') {
                return $p
            }
        }
    }
    return $null
}

function Test-Environment {
    $ok = $true

    # Python 3.11+
    $script:PyCmd = Find-Python
    if (-not $script:PyCmd) {
        Write-Err '未检测到 Python 3.11+，请先安装 (https://www.python.org/downloads/)'
        $ok = $false
    } else {
        $ver = & $script:PyCmd --version 2>&1
        Write-Ok "Python $ver  -  $Root"
    }

    # Node.js
    if (-not (Test-Command 'node')) {
        Write-Err '未检测到 Node.js，请先安装 Node.js 22+ (https://nodejs.org/)'
        $ok = $false
    } else {
        $nodeVer = node -v 2>$null
        Write-Ok "Node.js $nodeVer  -  $Root"
    }

    # npm
    if (-not (Test-Command 'npm')) {
        Write-Err '未检测到 npm'
        $ok = $false
    }

    # 目录检查
    if (-not (Test-Path (Join-Path $Root 'backend\cli.py'))) {
        Write-Err "后端入口不存在: $Root\backend\cli.py"
        $ok = $false
    }
    if (-not (Test-Path (Join-Path $Root 'package.json'))) {
        Write-Err "前端 package.json 不存在: $Root\package.json"
        $ok = $false
    }

    return $ok
}

# ========== 依赖检查 ==========
function Test-Dependencies {
    # Python 依赖
    Write-Info '同步 Python 依赖...'
    $pyOk = $true
    if (Test-Command 'uv') {
        Write-Info '使用 uv 安装依赖...'
        Push-Location $Root
        $uvOutput = uv sync 2>&1
        $uvExit = $LASTEXITCODE
        Pop-Location
        if ($uvExit -ne 0) {
            Write-Warn 'uv sync 有警告，尝试 pip 回退...'
            Push-Location $Root
            & $script:PyCmd -m pip install -r requirements.txt --quiet 2>&1 | Out-Null
            Pop-Location
        }
        Write-Ok 'Python 依赖就绪'
    } else {
        Write-Info '使用 pip 安装依赖...'
        Push-Location $Root
        $pipOutput = & $script:PyCmd -m pip install -r requirements.txt --quiet 2>&1
        $pipExit = $LASTEXITCODE
        Pop-Location
        if ($pipExit -ne 0) {
            Write-Warn 'pip 安装可能有警告，继续尝试启动...'
        }
        Write-Ok 'Python 依赖就绪 (pip)'
    }

    # 前端依赖
    $nodeModules = Join-Path $Root 'node_modules'
    if (-not (Test-Path $nodeModules)) {
        Write-Info '安装前端依赖 (首次较慢，请耐心等待)...'
        Push-Location $Root
        npm install 2>&1 | Out-Null
        Pop-Location
        Write-Ok '前端依赖安装完成'
    } else {
        Write-Ok '前端依赖已存在'
    }
}

# ========== 启动后端 ==========
function Start-Backend {
    $existing = Get-PortProcess $BackendPort
    if ($existing) {
        Write-Warn "后端已在运行 (PID: $($existing.Id))"
        return $true
    }

    Write-Info '启动后端服务 (FastAPI + Uvicorn)...'

    # 确定启动命令
    $useUv = Test-Command 'uv'
    if ($useUv) {
        $pyCommand = 'uv run python -m backend.cli'
    } else {
        $pyCommand = "`"$($script:PyCmd)`" -m backend.cli"
    }

    # 创建临时 batch 文件（比 PowerShell inner script 更可靠）
    $batPath = Join-Path $RunDir '_run_backend.bat'
    $batContent = "@echo off`r`n"
    $batContent += "title JobHunter Backend :$BackendPort`r`n"
    $batContent += "cd /d `"$Root`"`r`n"
    $batContent += "echo.`r`n"
    $batContent += "echo   ===== JobHunter Backend (FastAPI) =====`r`n"
    $batContent += "echo   Port: $BackendPort`r`n"
    $batContent += "echo   Press Ctrl+C to stop`r`n"
    $batContent += "echo.`r`n"
    $batContent += "$pyCommand`r`n"
    $batContent += "echo.`r`n"
    $batContent += "echo   Backend stopped. Press any key to close.`r`n"
    $batContent += "pause >nul`r`n"
    [System.IO.File]::WriteAllText($batPath, $batContent, [System.Text.Encoding]::Default)

    $proc = Start-Process -FilePath $batPath -PassThru
    $proc.Id | Out-File -FilePath $BackendPidFile -Encoding utf8 -Force

    # 等待端口就绪
    Write-Info '等待后端启动...'
    $maxWait = 40
    for ($i = 1; $i -le $maxWait; $i++) {
        Start-Sleep -Seconds 1
        $running = Get-PortProcess $BackendPort
        if ($running) {
            # 端口已监听，再等 1 秒让 uvicorn 完全就绪
            Start-Sleep -Seconds 1
            Write-Ok "后端已启动  ->  http://localhost:$BackendPort"
            Write-Host "  API 文档:  http://localhost:$BackendPort/api/v1/docs" -ForegroundColor DarkGray
            return $true
        }
        Write-Host "`r  进度: $i / $maxWait s" -NoNewline -ForegroundColor DarkGray
    }
    Write-Host ''
    Write-Warn '后端可能启动失败，请查看后端窗口的错误信息'
    Write-Host '  常见原因:' -ForegroundColor DarkGray
    Write-Host '    - Python 依赖未安装完整' -ForegroundColor DarkGray
    Write-Host '    - 数据库迁移失败 (尝试删除 jobhunter.db 后重启)' -ForegroundColor DarkGray
    Write-Host '    - 端口 5000 被其他程序占用' -ForegroundColor DarkGray
    return $false
}

# ========== 启动前端 ==========
function Start-Frontend {
    $existing = Get-PortProcess $FrontendPort
    if ($existing) {
        Write-Warn "前端已在运行 (PID: $($existing.Id))"
        return $true
    }

    Write-Info '启动前端服务 (React 19 + Vite)...'

    # 创建临时 batch 文件
    $batPath = Join-Path $RunDir '_run_frontend.bat'
    $batContent = "@echo off`r`n"
    $batContent += "title JobHunter Frontend :$FrontendPort`r`n"
    $batContent += "cd /d `"$Root`"`r`n"
    $batContent += "echo.`r`n"
    $batContent += "echo   ===== JobHunter Frontend (React + Vite) =====`r`n"
    $batContent += "echo   Port: $FrontendPort`r`n"
    $batContent += "echo   API Proxy -> http://localhost:$BackendPort`r`n"
    $batContent += "echo   Press Ctrl+C to stop`r`n"
    $batContent += "echo.`r`n"
    $batContent += "call npm run dev`r`n"
    $batContent += "echo.`r`n"
    $batContent += "echo   Frontend stopped. Press any key to close.`r`n"
    $batContent += "pause >nul`r`n"
    [System.IO.File]::WriteAllText($batPath, $batContent, [System.Text.Encoding]::Default)

    $proc = Start-Process -FilePath $batPath -PassThru
    $proc.Id | Out-File -FilePath $FrontendPidFile -Encoding utf8 -Force

    # 等待端口就绪
    Write-Info '等待前端启动...'
    $maxWait = 30
    for ($i = 1; $i -le $maxWait; $i++) {
        Start-Sleep -Seconds 1
        $running = Get-PortProcess $FrontendPort
        if ($running) {
            Write-Ok "前端已启动  ->  http://localhost:$FrontendPort"
            return $true
        }
        Write-Host "`r  进度: $i / $maxWait s" -NoNewline -ForegroundColor DarkGray
    }
    Write-Host ''
    Write-Warn '前端可能启动失败，请查看前端窗口的错误信息'
    return $false
}

# ========== 停止单个服务（杀进程树） ==========
function Stop-ProcessTree($parentId) {
    $children = Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $parentId }
    foreach ($child in $children) {
        Stop-ProcessTree $child.ProcessId
    }
    Stop-Process -Id $parentId -Force -ErrorAction SilentlyContinue
}

function Stop-OneService($port, $name, $pidFile) {
    $stopped = $false

    # 方式1: 通过端口查找
    $proc = Get-PortProcess $port
    if ($proc) {
        Write-Info "停止$name (PID: $($proc.Id), 端口: $port)..."
        # 杀掉整个进程树，避免子进程残留
        Stop-ProcessTree $proc.Id
        Start-Sleep -Milliseconds 500
        $stopped = $true
    }

    # 方式2: 通过 PID 文件查找
    if ((Test-Path $pidFile)) {
        $savedPid = Get-Content $pidFile -ErrorAction SilentlyContinue
        if ($savedPid) {
            $p = Get-Process -Id $savedPid -ErrorAction SilentlyContinue
            if ($p) {
                Stop-ProcessTree $savedPid
                $stopped = $true
            }
        }
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    }

    if ($stopped) {
        # 二次确认
        Start-Sleep -Milliseconds 500
        $stillAlive = Get-PortProcess $port
        if ($stillAlive) {
            Stop-ProcessTree $stillAlive.Id
        }
        Write-Ok "$name 已停止"
    } else {
        Write-Warn "$name 未在运行"
    }
}

# ========== 停止所有 ==========
function Stop-All {
    Write-Host ''
    Write-Info '停止所有服务...'
    Stop-OneService $BackendPort  '后端' $BackendPidFile
    Stop-OneService $FrontendPort '前端' $FrontendPidFile

    # 清理可能残留的 python/uvicorn 和 node/vite 进程
    # 注意: Get-Process 在 PowerShell 5.0 没有 CommandLine 属性，需用 Get-CimInstance
    try {
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
            ($_.Name -match 'python|uvicorn|node') -and
            ($_.CommandLine -match 'backend\.cli|uvicorn|vite|npm')
        } | ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
    } catch {
        # 如果 CIM 查询失败，回退到按进程名清理
        Get-Process -Name "uvicorn*","python*","node*" -ErrorAction SilentlyContinue | ForEach-Object {
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        }
    }

    Write-Ok '所有服务已停止'
}

# ========== 启动所有 ==========
function Start-All {
    Write-Host ''
    if (-not (Test-Environment)) {
        Write-Err '环境检查未通过，请先安装所需工具'
        return
    }
    Write-Host ''
    Test-Dependencies
    Write-Host ''
    Write-Host '  ------------------------------------------' -ForegroundColor DarkGray
    Write-Host ''

    # 先启动后端
    $backendOk = Start-Backend
    if (-not $backendOk) {
        Write-Host ''
        Write-Err '后端启动失败，前端无法正常工作。请修复后端问题后重试。'
        Write-Host '  提示: 可以先选菜单 [6] 仅启动前端查看页面' -ForegroundColor DarkGray
        return
    }

    Write-Host ''
    # 再启动前端（前端启动时会自动打开浏览器）
    Start-Frontend
    Write-Host ''
    Write-Host '  ------------------------------------------' -ForegroundColor DarkGray
    Write-Host ''
    Write-Ok '所有服务已启动！'
    Write-Host ''
    Write-Host "  前端页面:  " -NoNewline; Write-Host "http://localhost:$FrontendPort" -ForegroundColor White
    Write-Host "  后端 API:  " -NoNewline; Write-Host "http://localhost:$BackendPort" -ForegroundColor White
    Write-Host "  API 文档:  " -NoNewline; Write-Host "http://localhost:$BackendPort/api/v1/docs" -ForegroundColor White
    Write-Host ''

    # 兜底打开浏览器（Vite 也会自动打开，这里做双保险）
    Start-Sleep -Seconds 2
    $frontendRunning = Get-PortProcess $FrontendPort
    if ($frontendRunning) {
        Write-Info '确认浏览器已打开...'
        Start-Process "http://localhost:$FrontendPort"
    }

    Write-Host ''
    Write-Host '  提示: 关闭后端/前端窗口或使用菜单 [2] 停止服务' -ForegroundColor DarkGray
    Write-Host '  提示: 前端已配置 API 代理，所有 /api 请求自动转发到后端' -ForegroundColor DarkGray
    Write-Host ''
}

# ========== 重启所有 ==========
function Restart-All {
    Stop-All
    Write-Host ''
    Start-Sleep -Seconds 2
    Start-All
}

# ========== 查看状态 ==========
function Show-Status {
    Write-Host ''
    Write-Host '  ==========================================' -ForegroundColor Cyan
    Write-Host '            职途 AI 服务运行状态' -ForegroundColor Cyan
    Write-Host '  ==========================================' -ForegroundColor Cyan
    Write-Host ''

    # 后端
    $backend = Get-PortProcess $BackendPort
    if ($backend) {
        Write-Host '  后端  ' -NoNewline
        Write-Host '[运行中]' -ForegroundColor Green -NoNewline
        Write-Host "  PID: $($backend.Id)  端口: $BackendPort" -ForegroundColor DarkGray
        Write-Host "  -> http://localhost:$BackendPort" -ForegroundColor DarkGray
    } else {
        Write-Host '  后端  ' -NoNewline
        Write-Host '[未运行]' -ForegroundColor DarkGray -NoNewline
        Write-Host "  端口: $BackendPort" -ForegroundColor DarkGray
    }
    Write-Host ''

    # 前端
    $frontend = Get-PortProcess $FrontendPort
    if ($frontend) {
        Write-Host '  前端  ' -NoNewline
        Write-Host '[运行中]' -ForegroundColor Green -NoNewline
        Write-Host "  PID: $($frontend.Id)  端口: $FrontendPort" -ForegroundColor DarkGray
        Write-Host "  -> http://localhost:$FrontendPort" -ForegroundColor DarkGray
    } else {
        Write-Host '  前端  ' -NoNewline
        Write-Host '[未运行]' -ForegroundColor DarkGray -NoNewline
        Write-Host "  端口: $FrontendPort" -ForegroundColor DarkGray
    }
    Write-Host ''
    Write-Host '  ==========================================' -ForegroundColor Cyan
    Write-Host ''
}

# ========== 打开浏览器 ==========
function Open-Browser {
    $frontend = Get-PortProcess $FrontendPort
    if ($frontend) {
        Write-Info "打开浏览器 -> http://localhost:$FrontendPort"
        Start-Process "http://localhost:$FrontendPort"
    } else {
        $backend = Get-PortProcess $BackendPort
        if ($backend) {
            Write-Info "前端未运行，打开后端 -> http://localhost:$BackendPort"
            Start-Process "http://localhost:$BackendPort"
        } else {
            Write-Warn '所有服务均未运行，请先启动服务'
        }
    }
}

# ========== 交互菜单 ==========
function Show-Menu {
    $script:loop = $true

    while ($script:loop) {
        Write-Host ''
        Write-Host '  ==========================================' -ForegroundColor Cyan
        Write-Host '        职途 AI - 一键管理工具 v1.0' -ForegroundColor Cyan
        Write-Host '  ==========================================' -ForegroundColor Cyan
        Write-Host ''

        # 动态状态显示
        $b = Get-PortProcess $BackendPort
        $f = Get-PortProcess $FrontendPort
        $bStatus = if ($b) { '[运行中]' } else { '[未运行]' }
        $fStatus = if ($f) { '[运行中]' } else { '[未运行]' }
        $bColor  = if ($b) { 'Green' } else { 'DarkGray' }
        $fColor  = if ($f) { 'Green' } else { 'DarkGray' }

        Write-Host '  [1] 启动所有服务          [2] 停止所有服务' -ForegroundColor White
        Write-Host '  [3] 重启所有服务          [4] 查看运行状态' -ForegroundColor White
        Write-Host '  [5] 仅启动后端            [6] 仅启动前端' -ForegroundColor White
        Write-Host '  [7] 打开浏览器            [Q] 退出' -ForegroundColor Gray
        Write-Host ''
        Write-Host "  后端:$BackendPort " -NoNewline
        Write-Host $bStatus -ForegroundColor $bColor -NoNewline
        Write-Host "  |  前端:$FrontendPort " -NoNewline
        Write-Host $fStatus -ForegroundColor $fColor
        Write-Host ''
        Write-Host '  ==========================================' -ForegroundColor Cyan
        Write-Host ''

        $choice = Read-Host '  请选择操作'

        switch ($choice) {
            '1' { Start-All }
            '2' { Stop-All }
            '3' { Restart-All }
            '4' { Show-Status }
            '5' {
                if (Test-Environment) { Test-Dependencies; Start-Backend }
            }
            '6' {
                if (Test-Environment) { Test-Dependencies; Start-Frontend }
            }
            '7' { Open-Browser }
            { $_ -eq 'q' -or $_ -eq 'Q' } {
                $script:loop = $false
            }
            default {
                Write-Warn '无效选择，请重新输入'
            }
        }

        if ($script:loop) {
            Write-Host ''
            Read-Host '  按回车键返回菜单' | Out-Null
        }
    }
}

# ========== 主入口 ==========
try {
    switch ($Action) {
        'start'   { Start-All }
        'stop'    { Stop-All }
        'restart' { Restart-All }
        'status'  { Show-Status }
        'open'    { Open-Browser }
        'menu'    { Show-Menu }
    }
} catch {
    Write-Host ''
    Write-Err "脚本执行出错: $($_.Exception.Message)"
    Write-Host ''
    Write-Host '  请截图此错误并反馈' -ForegroundColor Yellow
    Write-Host ''
    if (-not $script:loop) {
        # 非菜单模式下暂停，让用户看到错误
        Read-Host '  按回车键退出' | Out-Null
    }
    exit 1
}
