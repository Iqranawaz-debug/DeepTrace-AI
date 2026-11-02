"""Production-install smoke test: run the real app with runtime dependencies only.

Drives the app over raw ASGI because httpx (and so TestClient) must be absent here. Uses mock
providers and a temporary data directory, and makes no network requests. Run it with the
interpreter of an environment created by `uv sync --frozen --no-dev`.
"""

import asyncio
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

for forbidden in ("httpx", "httpcore", "certifi", "pytest"):
    if importlib.util.find_spec(forbidden):
        sys.exit(f"{forbidden} is installed: this is not a production-only environment.")

from deeptrace.config import Settings  # noqa: E402
from deeptrace.main import create_app  # noqa: E402

ORIGIN = b"http://127.0.0.1:5173"


async def call(
    app: Any, method: str, path: str, body: dict[str, Any] | None = None, token: str = ""
) -> dict[str, Any]:
    headers = [(b"host", b"127.0.0.1:8000")]
    raw = b""
    if body is not None:
        raw = json.dumps(body).encode()
        headers += [
            (b"content-type", b"application/json"),
            (b"origin", ORIGIN),
            (b"x-deeptrace-token", token.encode()),
        ]
    route, _, query = path.partition("?")
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": route,
        "raw_path": route.encode(),
        "query_string": query.encode(),
        "headers": headers,
        "client": ("127.0.0.1", 50000),
        "server": ("127.0.0.1", 8000),
    }
    sent = False
    reply: dict[str, Any] = {"body": b""}

    async def receive() -> dict[str, Any]:
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": raw, "more_body": False}
        await asyncio.sleep(3600)
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        if message["type"] == "http.response.start":
            reply["status"] = message["status"]
        elif message["type"] == "http.response.body":
            reply["body"] += message.get("body", b"")

    await app(scope, receive, send)
    return reply


def expect(reply: dict[str, Any], status: int) -> Any:
    if reply["status"] != status:
        sys.exit(f"Expected {status}, got {reply['status']}: {reply['body'][:300]!r}")
    return json.loads(reply["body"]) if reply["body"][:1] in {b"{", b"["} else reply["body"]


async def finish(app: Any, investigation: str, run: str) -> dict[str, Any]:
    for _ in range(600):
        path = f"/api/runs/{run}?investigation_id={investigation}"
        state = expect(await call(app, "GET", path), 200)
        if state["status"] not in {"queued", "running"}:
            return state  # type: ignore[no-any-return]
        await asyncio.sleep(0.1)
    sys.exit("The run did not finish in time.")


async def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        app = create_app(Settings(data_dir=Path(directory), _env_file=None))
        async with app.router.lifespan_context(app):
            expect(await call(app, "GET", "/api/ready"), 200)
            token = expect(await call(app, "GET", "/api/session"), 200)["token"]
            inv = str(uuid4())
            base = f"/api/investigations/{inv}"
            question = "How do synthetic fixtures behave in a production install?"
            created = {"id": inv, "title": "Production smoke", "question": question}
            expect(await call(app, "POST", "/api/investigations", created, token), 201)
            expect(await call(app, "POST", "/api/web-consent", {"accepted": True}, token), 200)

            request = {"expected_revision": 0}
            run = expect(await call(app, "POST", f"{base}/plan/generate", request, token), 202)
            if (await finish(app, inv, run["id"]))["status"] != "completed":
                sys.exit("Plan generation did not complete.")

            revision = expect(await call(app, "GET", f"{base}/plan"), 200)["revision_no"]
            request = {"expected_revision": revision}
            run = expect(await call(app, "POST", f"{base}/research", request, token), 202)
            state = await finish(app, inv, run["id"])
            if state["status"] != "completed" or not state["sources"]:
                sys.exit(f"Research did not complete: {state['status']}")

            report = expect(await call(app, "GET", f"{base}/generated-reports/1"), 200)
            download = await call(app, "GET", f"{base}/generated-reports/1/download")
            if download["body"] != report["markdown_text"].encode():
                sys.exit("The download does not match the saved report.")
            if b"AI-generated research aid" not in download["body"]:
                sys.exit("The report is missing its required disclaimer.")
            print(f"Production smoke passed: {len(state['sources'])} sources, report saved.")


asyncio.run(main())
