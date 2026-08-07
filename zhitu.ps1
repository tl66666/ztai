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
    if (Test-Command 'uv') {
        Write-Info '使用 uv 安装依赖...'
        Push-Location $Root
        uv sync --frozen 2>&1 | Out-Null
        Pop-Location
        Write-Ok 'Python 依赖就绪 (uv)'
    } else {
        Write-Info '使用 pip 安装依赖...'
        Push-Location $Root
        & $script:PyCmd -m pip install -r requirements.txt --quiet 2>&1 | Out-Null
        Pop-Location
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
        return
    }

    Write-Info '启动后端服务 (FastAPI + Uvicorn)...'

    # 确定启动命令
    $useUv = Test-Command 'uv'
    if ($useUv) {
        $runCmd = 'uv run python -m backend.cli'
    } else {
        $runCmd = "$($script:PyCmd) -m backend.cli"
    }

    # 在新 PowerShell 窗口中启动后端
    $innerScript = @"
Set-Location -LiteralPath '$Root'
`$Host.UI.RawUI.WindowTitle = '职途AI - 后端 :$BackendPort'
Write-Host ''
Write-Host '  ===== 职途 AI 后端服务 =====' -ForegroundColor Cyan
Write-Host '  FastAPI + Uvicorn + SQLAlchemy' -ForegroundColor DarkGray
Write-Host '  端口: $BackendPort' -ForegroundColor DarkGray
Write-Host ''
Write-Host '  重要提示:' -ForegroundColor Yellow
Write-Host '  - 按 Ctrl+C 可优雅停止服务' -ForegroundColor Gray
Write-Host '  - 直接关闭本窗口可能导致子进程残留' -ForegroundColor Gray
Write-Host '  - 推荐使用主脚本的 stop 命令关闭' -ForegroundColor Gray
Write-Host ''
$runCmd
Write-Host ''
Write-Host '  后端服务已停止' -ForegroundColor Yellow
Read-Host '  按回车键关闭窗口'
"@

    $proc = Start-Process $PowerShellExe -ArgumentList '-NoExit', '-NoProfile', '-Command', $innerScript -PassThru
    $proc.Id | Out-File -FilePath $BackendPidFile -Encoding utf8 -Force

    # 等待端口就绪
    Write-Info '等待后端启动...'
    $maxWait = 20
    for ($i = 1; $i -le $maxWait; $i++) {
        Start-Sleep -Seconds 1
        $running = Get-PortProcess $BackendPort
        if ($running) {
            Write-Ok "后端已启动  ->  http://localhost:$BackendPort"
            return
        }
        Write-Host "`r  进度: $i / $maxWait s" -NoNewline -ForegroundColor DarkGray
    }
    Write-Host ''
    Write-Warn '后端可能仍在启动，请查看后端窗口'
}

# ========== 启动前端 ==========
function Start-Frontend {
    $existing = Get-PortProcess $FrontendPort
    if ($existing) {
        Write-Warn "前端已在运行 (PID: $($existing.Id))"
        return
    }

    Write-Info '启动前端服务 (React 19 + Vite)...'

    $innerScript = @"
Set-Location -LiteralPath '$Root'
`$Host.UI.RawUI.WindowTitle = '职途AI - 前端 :$FrontendPort'
Write-Host ''
Write-Host '  ===== 职途 AI 前端服务 =====' -ForegroundColor Cyan
Write-Host '  React 19 + TypeScript + Vite' -ForegroundColor DarkGray
Write-Host '  端口: $FrontendPort' -ForegroundColor DarkGray
Write-Host ''
Write-Host '  重要提示:' -ForegroundColor Yellow
Write-Host '  - 按 Ctrl+C 可优雅停止服务' -ForegroundColor Gray
Write-Host '  - 直接关闭本窗口可能导致子进程残留' -ForegroundColor Gray
Write-Host '  - 推荐使用主脚本的 stop 命令关闭' -ForegroundColor Gray
Write-Host ''
npm run dev
Write-Host ''
Write-Host '  前端服务已停止' -ForegroundColor Yellow
Read-Host '  按回车键关闭窗口'
"@

    $proc = Start-Process $PowerShellExe -ArgumentList '-NoExit', '-NoProfile', '-Command', $innerScript -PassThru
    $proc.Id | Out-File -FilePath $FrontendPidFile -Encoding utf8 -Force

    # 等待端口就绪
    Write-Info '等待前端启动...'
    $maxWait = 20
    for ($i = 1; $i -le $maxWait; $i++) {
        Start-Sleep -Seconds 1
        $running = Get-PortProcess $FrontendPort
        if ($running) {
            Write-Ok "前端已启动  ->  http://localhost:$FrontendPort"
            return
        }
        Write-Host "`r  进度: $i / $maxWait s" -NoNewline -ForegroundColor DarkGray
    }
    Write-Host ''
    Write-Warn '前端可能仍在启动，请查看前端窗口'
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
    Start-Backend
    Write-Host ''
    Start-Frontend
    Write-Host ''
    Write-Host '  ------------------------------------------' -ForegroundColor DarkGray
    Write-Host ''
    Write-Ok '所有服务已启动！'
    Write-Host ''
    Write-Host "  前端页面:  " -NoNewline; Write-Host "http://localhost:$FrontendPort" -ForegroundColor White
    Write-Host "  后端 API:  " -NoNewline; Write-Host "http://localhost:$BackendPort" -ForegroundColor White
    Write-Host "  API 文档:  " -NoNewline; Write-Host "http://localhost:$BackendPort/docs" -ForegroundColor White
    Write-Host ''
    Write-Host '  提示: 在浏览器中访问前端页面即可使用' -ForegroundColor DarkGray
    Write-Host '  停止服务: 运行 zhitu.ps1 stop 或在菜单中选择 [2]' -ForegroundColor DarkGray
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
