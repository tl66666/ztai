[CmdletBinding()]
param(
    [switch]$NoBrowser,
    [ValidateRange(1024, 65535)]
    [int]$Port = 5000,
    [switch]$SkipInstall,
    [switch]$Diagnostics
)

$ErrorActionPreference = "Stop"
$ProjectPath = $PSScriptRoot
$OutputPath = Join-Path $ProjectPath "output"
$RuntimePath = Join-Path $OutputPath "runtime"
$LauncherLog = Join-Path $RuntimePath "launcher.log"
$ServerLog = Join-Path $RuntimePath "server.log"
$ServerErrorLog = Join-Path $RuntimePath "server-error.log"
$PidFile = Join-Path $RuntimePath "server.pid"
$ServerUrlFile = Join-Path $RuntimePath "server.url"
$HealthTimeoutSeconds = 60
$flaskProcess = $null
$script:LaunchMutex = $null
$script:MutexAcquired = $false
$BrowserBlockedPorts = @(
    1719, 1720, 1723, 2049, 3659, 4045, 5060, 5061, 6000,
    6566, 6665, 6666, 6667, 6668, 6669, 6697, 10080
)

function Write-LauncherMessage {
    param(
        [Parameter(Mandatory = $true)][string]$Message,
        [ConsoleColor]$Color = [ConsoleColor]::Gray
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host $Message -ForegroundColor $Color
    "[$timestamp] $Message" | Out-File -FilePath $LauncherLog -Append -Encoding utf8
}

function Invoke-Python {
    param(
        [Parameter(Mandatory = $true)]$Python,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    & $Python.Command @($Python.Prefix + $Arguments)
}

function Find-Python {
    $candidates = @()
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        $candidates += [pscustomobject]@{ Command = $py.Source; Prefix = @("-3"); Label = "py -3" }
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        $candidates += [pscustomobject]@{ Command = $python.Source; Prefix = @(); Label = "python" }
    }

    foreach ($candidate in $candidates) {
        try {
            $versionText = (Invoke-Python $candidate @("-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))") 2>$null | Select-Object -Last 1).Trim()
            if ($LASTEXITCODE -eq 0 -and [version]$versionText -ge [version]"3.10.0") {
                $encodedExecutable = (Invoke-Python $candidate @("-c", "import sys, base64; print(base64.b64encode(sys.executable.encode('utf-8')).decode('ascii'))") 2>$null | Select-Object -Last 1).Trim()
                $executablePath = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($encodedExecutable))
                if ($LASTEXITCODE -ne 0 -or -not $executablePath -or -not (Test-Path -LiteralPath $executablePath -PathType Leaf)) {
                    throw "Python executable is unavailable: $executablePath"
                }
                return [pscustomobject]@{
                    Command = $executablePath; Prefix = @(); Label = $candidate.Label; Version = $versionText
                }
            }
        } catch {
            continue
        }
    }

    throw "Python 3.10 or newer was not found. Install it from https://www.python.org/downloads/ and enable the py launcher or PATH option."
}

function Test-PortFree {
    param([Parameter(Mandatory = $true)][int]$CandidatePort)

    if ($BrowserBlockedPorts -contains $CandidatePort) {
        return $false
    }
    $listener = $null
    try {
        $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $CandidatePort)
        $listener.Start()
        return $true
    } catch {
        return $false
    } finally {
        if ($listener) {
            try { $listener.Stop() } catch {}
        }
    }
}

function Find-FreePort {
    param([Parameter(Mandatory = $true)][int]$PreferredPort)

    # Probe the requested port upward, then wrap through the unprivileged range.
    # Binding is the source of truth; no process lookup or termination is used.
    for ($candidate = $PreferredPort; $candidate -le 65535; $candidate++) {
        if (Test-PortFree $candidate) {
            return $candidate
        }
    }
    $wrapStart = 1024
    if ($PreferredPort -gt $wrapStart) {
        for ($candidate = $wrapStart; $candidate -lt $PreferredPort; $candidate++) {
            if (Test-PortFree $candidate) {
                return $candidate
            }
        }
    }
    throw "Port $PreferredPort and every safe fallback port are busy. Other programs will not be stopped; choose another -Port."
}

function Test-Dependencies {
    param([Parameter(Mandatory = $true)]$Python)

    $importCheck = "import flask, flask_cors, requests, docx, reportlab, pdf2docx, PyPDF2"
    Invoke-Python $Python @("-c", $importCheck) 2>$null
    return ($LASTEXITCODE -eq 0)
}

function Open-RunningProjectServer {
    if (-not (Test-Path -LiteralPath $ServerUrlFile)) {
        return $false
    }

    $runningUrl = (Get-Content -LiteralPath $ServerUrlFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if (-not $runningUrl -or $runningUrl -notmatch '^http://127\.0\.0\.1:(\d{4,5})$') {
        return $false
    }
    $runningPort = [int]$Matches[1]
    if ($runningPort -lt 1024 -or $runningPort -gt 65535) {
        return $false
    }

    try {
        $response = Invoke-WebRequest -Uri "$runningUrl/api/config/ai-status" -UseBasicParsing -TimeoutSec 3
        if ($response.StatusCode -ne 200) {
            return $false
        }
    } catch {
        return $false
    }

    Write-Host "JobHunter is already ready: $runningUrl" -ForegroundColor Green
    if (-not $NoBrowser) {
        Start-Process $runningUrl
        Write-Host "Opened the existing JobHunter page." -ForegroundColor Green
    }
    return $true
}

function Acquire-LauncherMutex {
    $canonical = [System.IO.Path]::GetFullPath($ProjectPath).TrimEnd('\').ToUpperInvariant()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($canonical)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $digest = $sha.ComputeHash($bytes)
    } finally {
        $sha.Dispose()
    }
    $hash = (-join ($digest | ForEach-Object { $_.ToString('x2') }))
    $created = $false
    $script:LaunchMutex = New-Object System.Threading.Mutex($false, "Local\JobHunter-$hash", [ref]$created)
    try {
        $script:MutexAcquired = $script:LaunchMutex.WaitOne(5000)
    } catch [System.Threading.AbandonedMutexException] {
        $script:MutexAcquired = $true
    }
    if (-not $script:MutexAcquired) {
        throw "JobHunter is already running from this project directory. Close the existing launcher or use another copy."
    }
}

function Release-LauncherMutex {
    if ($script:LaunchMutex) {
        if ($script:MutexAcquired) {
            try { $script:LaunchMutex.ReleaseMutex() } catch {}
        }
        $script:LaunchMutex.Dispose()
        $script:LaunchMutex = $null
        $script:MutexAcquired = $false
    }
}

function Stop-OwnedServer {
    if ($script:flaskProcess -and -not $script:flaskProcess.HasExited) {
        Write-LauncherMessage "Stopping the server owned by this launcher (PID $($script:flaskProcess.Id))..." Yellow
        Stop-Process -Id $script:flaskProcess.Id -ErrorAction SilentlyContinue
        try { $script:flaskProcess.WaitForExit(5000) | Out-Null } catch {}
    }

    if (Test-Path -LiteralPath $PidFile) {
        $recordedPid = (Get-Content -LiteralPath $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
        if ($script:flaskProcess -and "$recordedPid" -eq "$($script:flaskProcess.Id)") {
            Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
            Remove-Item -LiteralPath $ServerUrlFile -Force -ErrorAction SilentlyContinue
        }
    }
}

try {
    if (-not $ProjectPath -or -not (Test-Path -LiteralPath (Join-Path $ProjectPath "app.py"))) {
        throw "This launcher must be in the same project directory as app.py."
    }

    New-Item -ItemType Directory -Path $RuntimePath -Force | Out-Null
    if (-not $Diagnostics -and (Open-RunningProjectServer)) {
        exit 0
    }
    if (-not $Diagnostics) {
        Acquire-LauncherMutex
    }
    Write-LauncherMessage "JobHunter project: $ProjectPath" Cyan

    $pythonRuntime = Find-Python
    Write-LauncherMessage "Python $($pythonRuntime.Version) ($($pythonRuntime.Label))" Green

    $pipOutput = Invoke-Python $pythonRuntime @("-m", "pip", "--version") 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "pip is unavailable for the selected Python. Run '$($pythonRuntime.Label) -m ensurepip --upgrade' and retry."
    }
    Write-LauncherMessage "pip is available." Green

    $requirements = Join-Path $ProjectPath "requirements.txt"
    if (-not (Test-Path -LiteralPath $requirements)) {
        throw "requirements.txt is missing; the project copy is incomplete."
    }

    $dependenciesReady = Test-Dependencies $pythonRuntime
    if (-not $dependenciesReady) {
        if ($SkipInstall) {
            throw "Dependencies are missing and -SkipInstall was set. Retry without it or run Python -m pip install -r requirements.txt."
        }

        Write-LauncherMessage "Installing missing dependencies from requirements.txt..." Yellow
        Invoke-Python $pythonRuntime @("-m", "pip", "install", "-r", $requirements)
        if ($LASTEXITCODE -ne 0 -or -not (Test-Dependencies $pythonRuntime)) {
            throw "Dependency installation failed. Check the network, proxy, and directory permissions, then run Python -m pip install -r requirements.txt."
        }
        Write-LauncherMessage "Dependencies installed." Green
    } else {
        Write-LauncherMessage "Dependencies are already satisfied; installation was skipped." Green
    }

    if ($Diagnostics) {
        Write-LauncherMessage "DIAGNOSTICS_OK" Green
        exit 0
    }

    $selectedPort = Find-FreePort $Port
    if ($BrowserBlockedPorts -contains $Port) {
        Write-LauncherMessage "Port $Port is blocked by browsers; safely selected port $selectedPort instead." Yellow
    } elseif ($selectedPort -ne $Port) {
        Write-LauncherMessage "Port $Port is in use; safely selected port $selectedPort instead." Yellow
    } else {
        Write-LauncherMessage "Port $selectedPort is available." Green
    }

    $env:JOBHUNTER_PORT = "$selectedPort"
    $env:JOBHUNTER_HOST = "127.0.0.1"
    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUNBUFFERED = "1"
    $serviceUrl = "http://127.0.0.1:$selectedPort"
    $serverCode = "import app; app.init_db(); app.app.run(host='127.0.0.1', port=int(__import__('os').environ['JOBHUNTER_PORT']), debug=False, use_reloader=False, threaded=True)"
    $quotedCode = '"' + ($serverCode -replace '"', '\"') + '"'
    $serverArguments = @($pythonRuntime.Prefix + @("-c", $quotedCode))

    Remove-Item -LiteralPath $ServerLog -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $ServerErrorLog -Force -ErrorAction SilentlyContinue
    $flaskProcess = Start-Process -FilePath $pythonRuntime.Command `
        -ArgumentList $serverArguments `
        -WorkingDirectory $ProjectPath `
        -RedirectStandardOutput $ServerLog `
        -RedirectStandardError $ServerErrorLog `
        -NoNewWindow `
        -PassThru
    "$($flaskProcess.Id)" | Out-File -FilePath $PidFile -Encoding ascii
    Write-LauncherMessage "Server process started with PID $($flaskProcess.Id)." Cyan

    $healthy = $false
    $deadline = (Get-Date).AddSeconds($HealthTimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if ($flaskProcess.HasExited) {
            throw "The server exited early with code $($flaskProcess.ExitCode). See $ServerErrorLog."
        }
        try {
            $response = Invoke-WebRequest -Uri "$serviceUrl/api/config/ai-status" -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                $healthy = $true
                break
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }

    if (-not $healthy) {
        throw "The server did not pass its health check within $HealthTimeoutSeconds seconds. Logs remain in $RuntimePath."
    }

    Write-LauncherMessage "JobHunter is ready: $serviceUrl" Green
    $serviceUrl | Out-File -FilePath $ServerUrlFile -Encoding ascii
    if (-not $NoBrowser) {
        Start-Process $serviceUrl
        Write-LauncherMessage "Opened the system default browser." Green
    }

    Write-LauncherMessage "Press Ctrl+C to stop the server started by this launcher." Cyan
    while (-not $flaskProcess.HasExited) {
        Start-Sleep -Seconds 1
    }

    if ($flaskProcess.ExitCode -ne 0) {
        throw "The server exited with code $($flaskProcess.ExitCode). See $ServerErrorLog."
    }
} catch {
    if ($script:MutexAcquired -and (Test-Path -LiteralPath $RuntimePath)) {
        Write-LauncherMessage "Startup failed: $($_.Exception.Message)" Red
        Write-LauncherMessage "Diagnostic log: $LauncherLog" Yellow
    } else {
        Write-Error $_.Exception.Message
    }
    Stop-OwnedServer
    exit 1
} finally {
    Stop-OwnedServer
    Release-LauncherMutex
}
