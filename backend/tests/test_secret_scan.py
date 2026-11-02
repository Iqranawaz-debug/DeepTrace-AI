"""AC-15: the scanner must detect a seeded secret and never print its value."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "scan_secrets.py"
spec = importlib.util.spec_from_file_location("scan_secrets", SCRIPT)
assert spec and spec.loader
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)

# Built by concatenation so this test file does not itself contain a matching value.
SEEDED = {
    "tavily-key": "tvly-" + "a1B2c3D4" * 4,
    "google-api-key": "AIza" + "SyA1b2C3" * 5,
    "anthropic-or-openai-key": "sk-" + "ant-" + "a1B2c3D4" * 4,
    "github-token": "ghp_" + "a1B2c3D4" * 5,
    "aws-access-key": "AKIA" + "ABCDEFGH" * 2,
    "slack-token": "xoxb-" + "12345678" * 4,
    "private-key": "-----BEGIN " + "RSA PRIVATE KEY-----",
    "assigned-provider-key": "TAVILY_API_KEY" + "=" + "plainvalue" * 3,
}


@pytest.mark.parametrize(("rule", "value"), SEEDED.items())
def test_each_rule_detects_its_seeded_secret(tmp_path, rule, value):
    path = tmp_path / "file.txt"
    path.write_text(f"first line\nsomething {value} more\n", encoding="utf-8")
    assert (2, rule) in scanner.scan_file(path)


@pytest.mark.parametrize(
    "line",
    [
        "tvly-SEEDED-SECRET-0123456789",  # The application test fixture; deliberately fake.
        'sha256 = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"',
        "TAVILY_API_KEY: str | None = None",
        "GEMINI_API_KEY=",
        "Bearer {key}",
        "task-runner-for-documentation-pages-long-name",
    ],
)
def test_ordinary_text_is_not_flagged(line):
    assert scanner.scan_lines([line]) == []


def test_binary_files_are_skipped(tmp_path):
    path = tmp_path / "font.woff2"
    path.write_bytes(b"\0\1\2" + SEEDED["tavily-key"].encode())
    assert scanner.scan_file(path) == []


def run_scanner(root, *args):
    # A copy of the script resolves its own root, so it scans only this temporary repository.
    target = root / "scripts" / "scan_secrets.py"
    target.parent.mkdir(exist_ok=True)
    target.write_bytes(SCRIPT.read_bytes())
    return subprocess.run(
        [sys.executable, str(target), *args], capture_output=True, text=True, check=False
    )


def git(root, *args):
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


def test_cli_fails_without_printing_the_secret_and_ignores_gitignored_files(tmp_path):
    secret = SEEDED["tavily-key"]
    git(tmp_path, "init", "-q")
    (tmp_path / ".gitignore").write_text(".env\n", encoding="utf-8")
    (tmp_path / ".env").write_text(secret, encoding="utf-8")
    assert run_scanner(tmp_path).returncode == 0  # A local, ignored .env is not a finding.
    (tmp_path / "config.txt").write_text(secret, encoding="utf-8")
    result = run_scanner(tmp_path)
    assert result.returncode == 1
    assert "config.txt:1: tavily-key" in result.stdout
    assert secret not in result.stdout + result.stderr


def test_history_mode_finds_a_secret_that_was_later_removed(tmp_path):
    secret = SEEDED["github-token"]
    git(tmp_path, "init", "-q")
    path = tmp_path / "config.txt"
    path.write_text(secret, encoding="utf-8")
    git(tmp_path, "add", "config.txt")
    git(tmp_path, "commit", "-q", "-m", "add")
    path.write_text("removed", encoding="utf-8")
    git(tmp_path, "add", "config.txt")
    git(tmp_path, "commit", "-q", "-m", "remove")
    assert run_scanner(tmp_path).returncode == 0
    history = run_scanner(tmp_path, "--history")
    assert history.returncode == 1 and "git history: github-token" in history.stdout
    assert secret not in history.stdout


def test_this_repository_is_clean():
    root = SCRIPT.parents[1]
    findings = [
        (path.name, line, rule)
        for path in scanner.tracked_files(root)
        if path.is_file()
        for line, rule in scanner.scan_file(path)
    ]
    assert findings == []
