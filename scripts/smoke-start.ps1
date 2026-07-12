[CmdletBinding()]
param([switch]$BoundaryPort)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$TempParent = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
$UnicodePathLabel = "JobHunter " + [char]0x4E2D + [char]0x6587 + " " + [char]0x5192 + [char]0x70DF + " "
$TempRoot = Join-Path $TempParent ($UnicodePathLabel + [guid]::NewGuid().ToString("N"))
$launcherProcess = $null
$serverPid = $null
$sentinelListener = $null

try {
    New-Item -ItemType Directory -Path $TempRoot | Out-Null

    $trackedFiles = & git -C $Root -c core.quotepath=false ls-files
    if ($LASTEXITCODE -ne 0 -or -not $trackedFiles) {
        throw "git ls-files failed; run this smoke test from a Git checkout."
    }

    foreach ($relativePath in $trackedFiles) {
        if ($relativePath -match '^(?:output|uploads|exports)(?:/|$)' -or
            $relativePath -match '(^|/)(?:\.env|jobhunter\.db)$') {
            continue
        }
        $source = Join-Path $Root ($relativePath -replace '/', '\')
        if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
            continue
        }
        $destination = Join-Path $TempRoot ($relativePath -replace '/', '\')
        $destinationParent = Split-Path -Parent $destination
        New-Item -ItemType Directory -Path $destinationParent -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination
    }

    $sentinelCandidate = if ($BoundaryPort) { 65535 } else { 0 }
    $sentinelListener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $sentinelCandidate)
    $sentinelListener.Start()
    $preferredPort = ([System.Net.IPEndPoint]$sentinelListener.LocalEndpoint).Port
    $launcher = Join-Path $TempRoot "start-jobhunter.ps1"
    $launcherArguments = @(
        "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", ('"' + $launcher + '"'),
        "-Port", "$preferredPort", "-NoBrowser", "-SkipInstall"
    )
    $launcherProcess = Start-Process -FilePath "powershell.exe" `
        -ArgumentList $launcherArguments `
        -WorkingDirectory $TempRoot `
        -NoNewWindow `
        -PassThru

    $pidFile = Join-Path $TempRoot "output\runtime\server.pid"
    $deadline = (Get-Date).AddSeconds(75)
    while ((Get-Date) -lt $deadline) {
        if ($launcherProcess.HasExited) {
            throw "Launcher exited before writing its owned server PID (exit $($launcherProcess.ExitCode))."
        }
        $receipt = $null
        if (Test-Path -LiteralPath $pidFile) {
            try {
                $receipt = (Get-Content -LiteralPath $pidFile -Raw -ErrorAction Stop).Trim()
                if ($receipt -notmatch '^\d+$' -or [int64]$receipt -le 0) {
                    $receipt = $null
                }
            } catch {
                $receipt = $null
            }
            if ($receipt) {
                $candidateProcess = Get-Process -Id ([int]$receipt) -ErrorAction SilentlyContinue
                $candidateInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $receipt" -ErrorAction SilentlyContinue
                if ($candidateProcess -and $candidateInfo -and $candidateInfo.CommandLine -match "import app" -and $candidateInfo.CommandLine -match "JOBHUNTER_PORT") {
                    $serverPid = [int]$receipt
                    break
                }
            }
        }
        Start-Sleep -Milliseconds 250
    }
    if (-not $serverPid) {
        throw "Timed out waiting for the launcher PID receipt."
    }

    $launcherLog = Get-Content -LiteralPath (Join-Path $TempRoot "output\runtime\launcher.log") -Raw
    if ($launcherLog -notmatch 'safely selected port ([0-9]+) instead') {
        throw "Launcher did not move away from the occupied preferred port $preferredPort."
    }
    $selectedPort = [int]$matches[1]
    if ($selectedPort -eq $preferredPort) {
        throw "Launcher reused an occupied preferred port."
    }

    $sentinelProbe = New-Object System.Net.Sockets.TcpClient
    try {
        $sentinelProbe.Connect("127.0.0.1", $preferredPort)
    } catch {
        throw "Preferred port owner was disturbed by the launcher."
    } finally {
        $sentinelProbe.Close()
    }

    $healthUrl = "http://127.0.0.1:$selectedPort/api/config/ai-status"
    $healthy = $false
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                $healthy = $true
                break
            }
        } catch {
            Start-Sleep -Milliseconds 250
        }
    }
    if (-not $healthy) {
        throw "Clean-path service did not pass $healthUrl."
    }

    Write-Host "SMOKE_OK $healthUrl (PID $serverPid; occupied port $preferredPort preserved)" -ForegroundColor Green
} finally {
    if ($launcherProcess -and -not $launcherProcess.HasExited) {
        Stop-Process -Id $launcherProcess.Id -ErrorAction SilentlyContinue
        try { $launcherProcess.WaitForExit(5000) | Out-Null } catch {}
    }
    if ($serverPid) {
        $ownedProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $serverPid" -ErrorAction SilentlyContinue
        if ($ownedProcess -and $ownedProcess.CommandLine -match "import app" -and $ownedProcess.CommandLine -match "JOBHUNTER_PORT") {
            Stop-Process -Id $serverPid -ErrorAction SilentlyContinue
        }
    }
    if ($sentinelListener) {
        $sentinelListener.Stop()
    }

    if (Test-Path -LiteralPath $TempRoot) {
        $resolvedTemp = [System.IO.Path]::GetFullPath($TempRoot)
        if ($resolvedTemp.StartsWith($TempParent, [System.StringComparison]::OrdinalIgnoreCase) -and
            (Split-Path -Leaf $resolvedTemp).StartsWith($UnicodePathLabel)) {
            Remove-Item -LiteralPath $resolvedTemp -Recurse -Force
        } else {
            throw "Refusing to clean an unexpected path: $resolvedTemp"
        }
    }
}
