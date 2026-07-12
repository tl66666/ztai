import re
import subprocess
import unittest
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    "",
    ".bat",
    ".css",
    ".example",
    ".html",
    ".js",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".txt",
    ".yml",
    ".yaml",
}


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


class RepositoryHygieneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tracked = tracked_files()

    def test_runtime_and_private_user_files_are_not_tracked(self):
        forbidden = []
        runtime_roots = {"uploads", ".uploads", "exports", "output"}
        private_suffixes = {".db", ".sqlite", ".sqlite3", ".wav", ".webm", ".m4a", ".mp3"}
        resume_suffixes = {".pdf", ".doc", ".docx"}

        for name in self.tracked:
            path = PurePosixPath(name)
            lowered_parts = {part.lower() for part in path.parts}
            lowered_name = path.name.lower()
            if lowered_name == ".env" or lowered_name.startswith(".env.") and lowered_name != ".env.example":
                forbidden.append(name)
            elif runtime_roots & lowered_parts:
                forbidden.append(name)
            elif path.suffix.lower() in private_suffixes:
                forbidden.append(name)
            elif path.suffix.lower() in resume_suffixes and "resume" in lowered_name:
                forbidden.append(name)

        self.assertEqual(forbidden, [], f"tracked runtime/private files: {forbidden}")

    def test_tracked_text_has_no_high_confidence_secret_or_private_key(self):
        patterns = {
            "OpenAI-style key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
            "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
            "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
            "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
            "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        }
        findings = []
        for name in self.tracked:
            path = ROOT / name
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            content = path.read_text(encoding="utf-8", errors="replace")
            for label, pattern in patterns.items():
                if pattern.search(content):
                    findings.append(f"{name}: {label}")
        self.assertEqual(findings, [], f"possible tracked secrets: {findings}")

    def test_tracked_text_has_no_developer_home_path(self):
        windows_home = re.compile(r"[A-Za-z]:\\Users\\(?!<|your-name|username)[^\\\s\"']+\\", re.IGNORECASE)
        unix_home = re.compile(r"/(?:Users|home)/(?!<|your-name|username)[^/\s\"']+/")
        findings = []
        for name in self.tracked:
            path = ROOT / name
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            content = path.read_text(encoding="utf-8", errors="replace")
            if windows_home.search(content) or unix_home.search(content):
                findings.append(name)
        self.assertEqual(findings, [], f"developer home paths found in: {findings}")

    def test_readme_local_links_exist(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        missing = []
        for raw_target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", readme):
            target = raw_target.strip().strip("<>")
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            relative = target.split("#", 1)[0].split("?", 1)[0]
            if relative and not (ROOT / relative).exists():
                missing.append(target)
        self.assertEqual(missing, [], f"missing README links: {missing}")

    def test_release_documentation_set_exists(self):
        required = {
            "README.md",
            "CHANGELOG.md",
            "docs/ARCHITECTURE.md",
            "docs/USER_GUIDE.md",
            "docs/TESTING.md",
        }
        missing = sorted(name for name in required if not (ROOT / name).is_file())
        self.assertEqual(missing, [])

    def test_gitignore_covers_local_release_artifacts(self):
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for rule in (
            ".env",
            "*.db",
            "*.db.backup-v*",
            "uploads/",
            "exports/",
            "output/",
            "*.log",
        ):
            with self.subTest(rule=rule):
                self.assertIn(rule, ignore)


if __name__ == "__main__":
    unittest.main()
