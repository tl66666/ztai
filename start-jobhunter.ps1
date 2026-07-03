<#
.SYNOPSIS
    职途AI (JobHunter AI) 一键启动脚本

.DESCRIPTION
    本脚本自动完成以下工作：
      1. 自动定位项目目录（基于脚本所在位置，无需手动配置）
      2. 优先使用虚拟环境，其次检测系统 Python（自动选择已装依赖的版本）
      3. 检测端口冲突并自动处理（终止占用进程）
      4. 检查并安装 Python 依赖
      5. 启动 Flask 服务（同时提供前端页面与后端 API）
      6. 等待服务就绪后自动打开默认浏览器
      7. 按 Ctrl+C 可优雅停止服务并释放端口

.NOTES
    本项目为 Flask 前后端一体化应用，启动 app.py 即同时启动前端与后端。
    本脚本可放在项目根目录下，任何人下载项目后双击 start.bat 即可运行。

.EXAMPLE
    方式一：双击同目录下的 start.bat
    方式二：在 PowerShell 中运行  .\start-jobhunter.ps1
    方式三：在 CMD 中运行  powershell -ExecutionPolicy Bypass -File start-jobhunter.ps1
#>

# ==================== 配置区（可按需修改） ====================
$Port    = 5000
$MaxWait = 60   # 等待服务就绪的最大秒数
# =============================================================

# 注意：不设置全局 $ErrorActionPreference="Stop"，否则原生命令(python/pip)的
# stderr 输出会被当作错误并中断脚本。各 cmdlet 按需使用 -ErrorAction SilentlyContinue。

# ---------- 辅助函数 ----------
function Write-Step($index, $total, $msg) {
    Write-Host "[$index/$total] $msg" -ForegroundColor Cyan
}
function Write-OK($msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn2($msg){ Write-Host "  [!]  $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "  [X]  $msg" -ForegroundColor Red }

# ---------- 0. 自动定位项目目录 ----------
# 优先使用 $PSScriptRoot（PS 3.0+），回退到 $MyInvocation
$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}
if (-not $ScriptDir) {
    # 极端情况：从交互式 shell 运行，用当前目录
    $ScriptDir = (Get-Location).Path
}
$ProjectPath = $ScriptDir

if (-not (Test-Path (Join-Path $ProjectPath "app.py"))) {
    Write-Err "在 $ProjectPath 下未找到 app.py"
    Write-Err "请确保本脚本位于项目根目录（与 app.py 同级）"
    Read-Host "按回车键退出"
    exit 1
}
Set-Location $ProjectPath
Write-Step 1 8 "工作目录: $ProjectPath"

# ---------- 1. 检测 Python ----------
# 优先级：项目内虚拟环境 > py launcher 列出的版本 > PATH 中的 python/python3
$candidates = @()

# 1a. 检查项目内虚拟环境
foreach ($venvName in @("venv", ".venv")) {
    $venvPython = Join-Path $ProjectPath "$venvName\Scripts\python.exe"
    if (Test-Path $venvPython) {
        Write-Host "  发现虚拟环境: $venvName" -ForegroundColor DarkGray
        $candidates += $venvPython
    }
}

# 1b. 通过 py launcher 收集已安装的 Python 版本
$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pyLauncher) {
    try {
        $pyList = & py -0p 2>$null
        foreach ($line in $pyList) {
            # py -0p 输出格式: " -V:3.12 *    C:\path\python.exe"，需用正则提取路径
            if ($line -match '([A-Z]:\\.+python\.exe)') {
                $exePath = $matches[1].Trim()
                if ((Test-Path $exePath) -and ($candidates -notcontains $exePath)) {
                    $candidates += $exePath
                }
            }
        }
    } catch {}
}

# 1c. 检查 PATH 中的 python / python3
foreach ($cmd in @("python", "python3")) {
    $g = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($g -and $g.Source -and ($candidates -notcontains $g.Source)) {
        $candidates += $g.Source
    }
}

if ($candidates.Count -eq 0) {
    Write-Err "未检测到 Python，请先安装 Python 3.8+ 并加入系统 PATH"
    Write-Err "下载地址: https://www.python.org/downloads/"
    Read-Host "按回车键退出"
    exit 1
}

# 优先选择已安装 flask 的 Python；同时验证版本 >= 3.8
$pythonExe = $null
$minVersion = [version]"3.8.0"
foreach ($cand in $candidates) {
    try {
        # 检查版本
        $verOutput = (& $cand -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>&1) -join ""
        $verStr = $verOutput.Trim()
        $pyVer = [version]$verStr
        if ($pyVer -lt $minVersion) {
            Write-Warn2 "跳过 $cand (版本 $verStr 低于 3.8.0)"
            continue
        }
        # 检查是否已装 flask
        $depCheck = (& $cand -c "import flask; print('ok')" 2>&1) -join ""
        if ($depCheck.Trim() -eq "ok") {
            $pythonExe = $cand
            break
        }
    } catch {
        # 版本解析失败，跳过
    }
}

# 如果没有找到已装 flask 的 Python，选第一个版本达标的
if (-not $pythonExe) {
    foreach ($cand in $candidates) {
        try {
            $verOutput = (& $cand -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>&1) -join ""
            $major, $minor = $verOutput.Trim().Split('.')
            if ([int]$major -ge 3 -and [int]$minor -ge 8) {
                $pythonExe = $cand
                break
            }
        } catch {}
    }
}

if (-not $pythonExe) {
    Write-Err "未找到 Python 3.8+ 版本，请安装 Python 3.8 或更高版本"
    Write-Err "下载地址: https://www.python.org/downloads/"
    Read-Host "按回车键退出"
    exit 1
}

$pyVerStr = & $pythonExe --version 2>&1
Write-Step 2 8 "Python 环境: $pyVerStr ($pythonExe)"

# ---------- 2. 检测端口冲突 ----------
Write-Step 3 8 "检测端口 $Port ..."
$listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listeners) {
    $conflictPids = $listeners | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($cpid in $conflictPids) {
        $p = Get-Process -Id $cpid -ErrorAction SilentlyContinue
        $pname = if ($p) { $p.ProcessName } else { "未知" }
        Write-Warn2 "端口 $Port 被占用: $pname (PID: $cpid)，正在终止..."
        taskkill /F /T /PID $cpid 2>$null | Out-Null
    }
    Start-Sleep -Seconds 2
    if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
        Write-Err "端口 $Port 仍被占用，无法自动释放，请手动处理后重试"
        Read-Host "按回车键退出"
        exit 1
    }
    Write-OK "端口已释放"
} else {
    Write-OK "端口 $Port 可用"
}

# ---------- 3. 检查 pip 可用性 ----------
Write-Step 4 8 "检查 pip ..."
$pipCheck = (& $pythonExe -m pip --version 2>&1) -join ""
if ($LASTEXITCODE -ne 0 -or -not $pipCheck) {
    Write-Err "pip 不可用，请重新安装 Python 时勾选 pip 选项"
    Write-Err "或运行: $pythonExe -m ensurepip --upgrade"
    Read-Host "按回车键退出"
    exit 1
}
Write-OK "pip 可用"

# ---------- 4. 检查并安装依赖 ----------
Write-Step 5 8 "检查 Python 依赖..."
$reqFile = Join-Path $ProjectPath "requirements.txt"
if (-not (Test-Path $reqFile)) {
    Write-Err "未找到 requirements.txt，请确保项目完整"
    Read-Host "按回车键退出"
    exit 1
}

$depResult = ""
try {
    $depResult = (& $pythonExe -c "import flask, flask_cors, requests, docx, reportlab, PyPDF2; print('ok')" 2>&1) -join "`n"
} catch {
    $depResult = "import_error"
}
if ("$depResult".Trim() -ne "ok") {
    Write-Warn2 "依赖缺失，正在安装 (pip install -r requirements.txt) ..."
    Write-Host "  首次安装可能需要 1-3 分钟，请耐心等待..." -ForegroundColor DarkGray
    & $pythonExe -m pip install -r $reqFile
    if ($LASTEXITCODE -ne 0) {
        Write-Err "依赖安装失败，请手动运行: pip install -r requirements.txt"
        Read-Host "按回车键退出"
        exit 1
    }
    # 再次验证
    $recheck = (& $pythonExe -c "import flask; print('ok')" 2>&1) -join ""
    if ($recheck.Trim() -ne "ok") {
        Write-Err "依赖安装后仍无法导入 flask，请检查 Python 环境"
        Read-Host "按回车键退出"
        exit 1
    }
    Write-OK "依赖安装完成"
} else {
    Write-OK "依赖完整，跳过安装"
}

# ---------- 5. 启动服务 ----------
Write-Step 6 8 "启动职途AI服务（前端页面 + 后端 API）..."
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = "1"
$flaskProcess = Start-Process -FilePath $pythonExe `
    -ArgumentList "app.py" `
    -PassThru -NoNewWindow `
    -WorkingDirectory $ProjectPath
Write-OK "后端进程已启动 (PID: $($flaskProcess.Id))"

# ---------- 6. 等待就绪 ----------
Write-Step 7 8 "等待服务就绪..."
$ready = $false
for ($i = 1; $i -le $MaxWait; $i++) {
    if ($flaskProcess.HasExited) {
        Write-Err "服务进程意外退出 (ExitCode: $($flaskProcess.ExitCode))"
        Write-Err "请检查 app.py 是否有错误，或尝试手动运行: $pythonExe app.py"
        Read-Host "按回车键退出"
        exit 1
    }
    Start-Sleep -Seconds 1
    # TCP 端口连接检测
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("127.0.0.1", $Port)
        $tcp.Close()
        $ready = $true
        break
    } catch {
        Write-Host "." -NoNewline -ForegroundColor DarkGray
    }
}
Write-Host ""

if ($ready) {
    Write-OK "服务已就绪！"
} else {
    Write-Warn2 "服务启动超时（${MaxWait}s），请稍后手动访问 http://localhost:$Port"
}

# ---------- 7. 打开浏览器 ----------
if ($ready) {
    Write-Step 8 8 "打开浏览器..."
    $ServiceUrl = "http://localhost:$Port"
    Start-Process $ServiceUrl
    Write-OK "已打开默认浏览器: $ServiceUrl"
}

# ---------- 保持运行，等待退出 ----------
Write-Host ""
Write-Host "================================================" -ForegroundColor DarkCyan
Write-Host "   职途AI 正在运行中   ->  http://localhost:$Port" -ForegroundColor Cyan
Write-Host "   按 Ctrl+C 停止服务并释放端口" -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor DarkCyan
Write-Host ""

$flaskPid = $flaskProcess.Id
try {
    while (-not $flaskProcess.HasExited) {
        Start-Sleep -Seconds 1
    }
    Write-Warn2 "服务进程已自行退出"
} finally {
    Write-Host ""
    Write-Host "正在停止服务并清理进程..." -ForegroundColor Yellow
    # 终止进程树（Flask debug 模式有 reloader 子进程）
    if ($flaskProcess -and -not $flaskProcess.HasExited) {
        taskkill /F /T /PID $flaskPid 2>$null | Out-Null
    }
    # 通过端口清理可能残留的进程
    $residual = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($residual) {
        $residualPids = $residual | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($rpid in $residualPids) {
            Write-Warn2 "清理残留进程 PID: $rpid"
            taskkill /F /T /PID $rpid 2>$null | Out-Null
        }
    }
    Write-OK "服务已停止，端口 $Port 已释放"
    Start-Sleep -Seconds 1
}
