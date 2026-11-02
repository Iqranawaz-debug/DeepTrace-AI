"""Killable parser subprocess; bounded payloads, no downloader or script execution."""

import json
import subprocess
import sys

from deeptrace.collection.extractor import MAX_INPUT, Extraction, extract
from deeptrace.collection.policy import CollectionError


def parse(body: bytes, mime: str, timeout: float = 5) -> Extraction:
    if len(body) > MAX_INPUT:
        raise CollectionError("extraction_input_limit")
    try:
        payload = json.dumps(
            {"body": body.decode("utf-8-sig", errors="strict"), "mime": mime}
        ).encode()
    except UnicodeError:
        raise CollectionError("unsupported_encoding") from None
    try:
        result = subprocess.run(
            [sys.executable, "-m", "deeptrace.collection.parser_process"],
            input=payload,
            capture_output=True,
            timeout=timeout,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired:
        raise CollectionError("parser_timeout") from None
    if result.returncode or len(result.stdout) > 2_000_000:
        raise CollectionError("extraction_failed")
    data = json.loads(result.stdout)
    if "error" in data:
        raise CollectionError(data["error"])
    return Extraction(**data)


def child() -> None:
    try:
        raw = sys.stdin.buffer.read(6 * MAX_INPUT + 1000)
        data = json.loads(raw)
        result = extract(data["body"].encode(), data["mime"]).json()
    except CollectionError as exc:
        result = {"error": exc.code}
    except Exception:
        result = {"error": "extraction_failed"}
    sys.stdout.write(json.dumps(result))


if __name__ == "__main__":
    child()
