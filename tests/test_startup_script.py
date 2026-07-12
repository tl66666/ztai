from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "start-jobhunter.ps1"
BATCH_LAUNCHER = ROOT / "start.bat"
SMOKE_SCRIPT = ROOT / "scripts" / "smoke-start.ps1"


class StartupScriptContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.launcher = LAUNCHER.read_text(encoding="utf-8-sig")
        cls.batch = BATCH_LAUNCHER.read_text(encoding="utf-8-sig")

    def test_launcher_is_portable_and_has_supported_switches(self):
        self.assertIn("$PSScriptRoot", self.launcher)
        for parameter in ("NoBrowser", "Port", "SkipInstall", "Diagnostics"):
            self.assertRegex(self.launcher, rf"(?i)\${parameter}\b")

        forbidden_paths = (
            r"C:\\Users\\",
            r"/Users/",
            r"/home/",
        )
        for forbidden in forbidden_paths:
            self.assertNotIn(forbidden, self.launcher)
        self.assertRegex(self.launcher, r"(?i)Mutex")
        self.assertIn("Local\\JobHunter-", self.launcher)
        blocked_ports = (
            1719, 1720, 1723, 2049, 3659, 4045, 5060, 5061, 6000,
            6566, 6665, 6666, 6667, 6668, 6669, 6697, 10080,
        )
        for port in blocked_ports:
            self.assertRegex(self.launcher, rf"\b{port}\b")
        self.assertIn("blocked by browsers", self.launcher)

    def test_launcher_never_kills_a_port_owner_or_process_tree(self):
        self.assertNotRegex(self.launcher, r"(?i)\btaskkill\b")
        self.assertNotRegex(self.launcher, r"(?i)Get-NetTCPConnection.+OwningProcess")
        self.assertNotRegex(self.launcher, r"(?i)Stop-Process.+(?:OwningProcess|port|listener)")
        self.assertIn("Stop-Process -Id $script:flaskProcess.Id", self.launcher)

    def test_pid_receipt_is_removed_only_with_a_matching_owned_handle(self):
        self.assertNotIn("-not $script:flaskProcess -or", self.launcher)
        self.assertRegex(
            self.launcher,
            r'if \(\$script:flaskProcess -and "\$recordedPid" -eq '
            r'"\$\(\$script:flaskProcess\.Id\)"\)',
        )
        self.assertIn("MutexAcquired", self.launcher)

    def test_launcher_uses_runtime_directory_for_logs_and_pid_receipt(self):
        self.assertRegex(self.launcher, r'Join-Path\s+\$ProjectPath\s+["\']output["\']')
        self.assertRegex(self.launcher, r'Join-Path\s+\$OutputPath\s+["\']runtime["\']')
        self.assertIn("launcher.log", self.launcher)
        self.assertIn("server.log", self.launcher)
        self.assertIn("server.pid", self.launcher)

    def test_launcher_checks_supported_python_pip_and_health_endpoint(self):
        self.assertRegex(self.launcher, r"(?i)Get-Command\s+py\b")
        self.assertRegex(self.launcher, r"(?i)Get-Command\s+python\b")
        self.assertIn("3.10", self.launcher)
        self.assertRegex(self.launcher, r'@\("-m",\s*"pip",\s*"--version"\)')
        self.assertIn("/api/config/ai-status", self.launcher)
        self.assertIn("JOBHUNTER_PORT", self.launcher)
        self.assertIn("use_reloader=False", self.launcher)
        self.assertIn("ValidateRange(1024, 65535)", self.launcher)

    def test_port_selection_wraps_safely_after_65535(self):
        self.assertIn("65535", self.launcher)
        self.assertRegex(self.launcher, r"(?i)wrap|回绕")
        self.assertRegex(self.launcher, r"(?i)1024")
        self.assertIn("BoundaryPort", SMOKE_SCRIPT.read_text(encoding="utf-8-sig"))
        self.assertIn("BlockedPort", SMOKE_SCRIPT.read_text(encoding="utf-8-sig"))

    def test_batch_launcher_forwards_arguments_and_exit_code(self):
        self.assertIn('%~dp0start-jobhunter.ps1', self.batch)
        self.assertRegex(self.batch, r"(?i)-ExecutionPolicy\s+Bypass")
        self.assertIn("%*", self.batch)
        self.assertRegex(self.batch, r"(?i)exit\s+/b\s+%errorlevel%")
        self.assertNotRegex(self.batch, r"(?im)^\s*pause\s*$")

    def test_clean_path_smoke_script_is_present_and_safety_bounded(self):
        smoke = SMOKE_SCRIPT.read_text(encoding="utf-8-sig")
        self.assertIn("[char]0x4E2D", smoke)
        self.assertIn("[char]0x5192", smoke)
        self.assertIn("git ls-files", smoke)
        self.assertIn("-NoBrowser", smoke)
        self.assertIn("-SkipInstall", smoke)
        self.assertIn("/api/config/ai-status", smoke)
        self.assertRegex(smoke, r"(?i)Stop-Process\s+-Id\s+\$[A-Za-z][A-Za-z0-9]*")
        self.assertNotRegex(smoke, r"(?i)\btaskkill\b")
        self.assertIn("$sentinelListener", smoke)
        self.assertIn("Preferred port owner was disturbed", smoke)
        self.assertRegex(smoke, r"(?i)strict|match.*\^\\d\+|\^\\d\+\$")
        self.assertIn("Get-Process", smoke)
        self.assertIn("WaitForExit(5000)", smoke)
        self.assertIn("-Force", smoke)


@unittest.skipUnless(os.name == "nt" and shutil.which("powershell"), "requires Windows PowerShell")
class StartupScriptExecutionTests(unittest.TestCase):
    def test_launcher_parses_in_windows_powershell(self):
        path = str(LAUNCHER).replace("'", "''")
        command = (
            "$errors=$null; "
            "[System.Management.Automation.Language.Parser]::ParseFile("
            f"  '{path}', [ref]$null, [ref]$errors) > $null; "
            "if ($errors.Count) { $errors | ForEach-Object { Write-Error $_ }; exit 1 }"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_diagnostics_mode_succeeds_without_starting_server(self):
        pid_file = ROOT / "output" / "runtime" / "server.pid"
        previous_pid_receipt = pid_file.read_bytes() if pid_file.exists() else None
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(LAUNCHER),
                "-Diagnostics",
                "-NoBrowser",
                "-SkipInstall",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("DIAGNOSTICS_OK", result.stdout)
        current_pid_receipt = pid_file.read_bytes() if pid_file.exists() else None
        self.assertEqual(current_pid_receipt, previous_pid_receipt)


if __name__ == "__main__":
    unittest.main()
