"""Browser mutation boundary. This is not OS-user authentication."""

import re
import secrets

from fastapi import Request

WORKSPACE = re.compile(r"^/api/investigations(?:/[^/]+(?:/plan)?)?$")
MAX_BODY = 65536


def mutation_failure(
    request: Request, origins: list[str], token: str
) -> tuple[int, str, str] | None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return None
    if request.method not in {"POST", "PATCH", "PUT"} or not WORKSPACE.fullmatch(request.url.path):
        return 405, "method_not_allowed", "This operation is unavailable."
    if len(request.headers.getlist("origin")) != 1 or request.headers.get("origin") not in origins:
        return 403, "invalid_origin", "A trusted browser origin is required."
    supplied = request.headers.getlist("x-deeptrace-token")
    if len(supplied) != 1 or not secrets.compare_digest(
        supplied[0].encode("utf-8"), token.encode("ascii")
    ):
        return (
            403,
            "invalid_session",
            "Refresh the local session and retry. Your edits are not saved.",
        )
    content_types = request.headers.getlist("content-type")
    if (
        len(content_types) != 1
        or content_types[0].split(";")[0].strip().lower() != "application/json"
    ):
        return 415, "invalid_content_type", "JSON content is required."
    return None
