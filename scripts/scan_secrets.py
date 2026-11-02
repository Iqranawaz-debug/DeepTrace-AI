"""Offline secret scan (SEC-09, AC-15). Reports file, line and rule, never the matched value.

A pattern scan only finds known key shapes; it cannot prove a repository holds no secrets.
Use --history to also scan every line ever added in any commit.
"""

import argparse
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES = {
    "tavily-key": re.compile(r"\btvly-[A-Za-z0-9_]{20,}"),
    "google-api-key": re.compile(r"\bAIza[A-Za-z0-9_-]{30,}"),
    "anthropic-or-openai-key": re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}"),
    "github-token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})"),
    "aws-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "slack-token": re.compile(r"\bxox[abpr]-[A-Za-z0-9-]{20,}"),
    "private-key": re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----"),
    "assigned-provider-key": re.compile(
        r"\b(?:TAVILY|GEMINI|GOOGLE|ANTHROPIC|OPENAI)_API_KEY\s*[:=]\s*[\"']?[A-Za-z0-9_-]{16,}"
    ),
}


def scan_lines(lines: Iterable[str]) -> list[tuple[int, str]]:
    return [
        (number, rule)
        for number, line in enumerate(lines, 1)
        for rule, pattern in RULES.items()
        if pattern.search(line)
    ]


def scan_file(path: Path) -> list[tuple[int, str]]:
    data = path.read_bytes()
    if b"\0" in data:  # Fonts and other binary assets.
        return []
    return scan_lines(data.decode("utf-8", errors="replace").splitlines())


def tracked_files(root: Path) -> list[Path]:
    """Everything Git would see: tracked and new files, but not ignored ones like .env."""
    listing = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        capture_output=True,
        check=True,
    ).stdout
    return [root / name.decode() for name in listing.split(b"\0") if name]


def scan_history(root: Path) -> list[str]:
    """Rules matched by any line ever added. A removed secret still needs rotating."""
    process = subprocess.Popen(
        ["git", "log", "--all", "-p", "--format=", "--no-color", "--text"],
        cwd=root,
        stdout=subprocess.PIPE,
    )
    assert process.stdout is not None
    found: set[str] = set()
    for raw in process.stdout:
        if raw.startswith(b"+") and not raw.startswith(b"+++"):
            line = raw.decode("utf-8", errors="replace")
            found.update(rule for rule, pattern in RULES.items() if pattern.search(line))
    if process.wait():
        raise RuntimeError("git log failed")
    return sorted(found)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", action="store_true", help="also scan all Git history")
    options = parser.parse_args()
    failures = 0
    files = [path for path in tracked_files(ROOT) if path.is_file()]
    for path in files:
        for number, rule in scan_file(path):
            print(f"{path.relative_to(ROOT).as_posix()}:{number}: {rule}")
            failures += 1
    if options.history:
        for rule in scan_history(ROOT):
            print(f"git history: {rule}")
            failures += 1
    scope = f"{len(files)} files" + (" and Git history" if options.history else "")
    if failures:
        print(f"Secret scan FAILED: {failures} finding(s) in {scope}. Rotate any real key.")
        return 1
    print(f"Secret scan passed: {scope}. Known key patterns only; not a proof of absence.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
