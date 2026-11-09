"""Opt-in Tavily and Gemini adapters. Fixed hosts only; no base URL can be configured.

Request shapes follow the providers' published APIs and are contract-tested with fakes.
They have not been exercised against the real services until an owner runs the opt-in
live smoke procedure. Failures expose fixed categories, never bodies or keys.
"""

import http.client
import json
import ssl
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote

from deeptrace.collection.live_transport import bounded_resolve, open_pinned
from deeptrace.collection.policy import CollectionError, destinations
from deeptrace.research.contracts import LLMText, ProviderError, SearchLead

MAX_RESPONSE = 4_000_000
Reply = tuple[int, bytes, dict[str, str]]
Poster = Callable[[str, str, dict[str, str], bytes, float], Reply]


def post_json(
    host: str, target: str, headers: dict[str, str], body: bytes, timeout: float
) -> Reply:
    """POST to a fixed provider host over the same policy-checked pinned connection."""
    try:
        _, addresses = destinations(f"https://{host}/", bounded_resolve)
        connection, response = open_pinned(
            "POST",
            "https",
            addresses[0],
            host,
            443,
            target,
            timeout,
            {**headers, "Host": host, "Content-Type": "application/json"},
            body,
        )
        try:
            data = response.read(MAX_RESPONSE + 1)
        finally:
            connection.close()
    except TimeoutError:
        raise ProviderError("timeout") from None
    except CollectionError, OSError, ssl.SSLError, http.client.HTTPException:
        raise ProviderError("unavailable") from None
    if len(data) > MAX_RESPONSE:
        raise ProviderError("malformed_response")
    return response.status, data, {k.lower(): v for k, v in response.getheaders()}


def retry_after(headers: dict[str, str]) -> float | None:
    """NFR-R2: seconds or an HTTP date. Anything unparseable is simply ignored."""
    value = headers.get("retry-after", "").strip()
    if not value:
        return None
    try:
        return max(0.0, float(int(value)))
    except ValueError:
        pass
    try:
        return max(0.0, (parsedate_to_datetime(value) - datetime.now(UTC)).total_seconds())
    except ValueError, TypeError:
        return None


def classify(
    status: int, headers: dict[str, str], quota_statuses: frozenset[int] = frozenset()
) -> None:
    if status == 200:
        return
    if status in quota_statuses:
        raise ProviderError("quota_exhausted")
    if status in {401, 403}:
        raise ProviderError("auth_rejected")
    if status == 429:
        raise ProviderError("rate_limited", retry_after(headers))
    raise ProviderError("unavailable", retry_after(headers))


def decode(data: bytes) -> Any:
    try:
        return json.loads(data)
    except ValueError:
        raise ProviderError("malformed_response") from None


class TavilySearch:
    id = "tavily"
    host = "api.tavily.com"

    def __init__(self, key: Callable[[], str | None], poster: Poster = post_json):
        self.key, self.poster = key, poster

    def search(self, query: str, limit: int, timeout: float) -> list[SearchLead]:
        key = self.key()
        if not key:
            raise ProviderError("not_configured")
        # Least-cost option only; premium search depths are never enabled implicitly.
        body = json.dumps({"query": query, "max_results": limit, "search_depth": "basic"})
        status, data, headers = self.poster(
            self.host, "/search", {"Authorization": f"Bearer {key}"}, body.encode(), timeout
        )
        classify(status, headers, frozenset({432, 433}))
        results = decode(data)
        if not isinstance(results, dict) or not isinstance(results.get("results"), list):
            raise ProviderError("malformed_response")
        leads = []
        for rank, item in enumerate(results["results"][:limit], 1):
            if isinstance(item, dict) and isinstance(item.get("url"), str):
                title = item.get("title")
                leads.append(
                    SearchLead(item["url"], title if isinstance(title, str) else None, rank)
                )
        return leads


class GeminiLLM:
    id = "gemini"
    host = "generativelanguage.googleapis.com"

    def __init__(self, model: str, key: Callable[[], str | None], poster: Poster = post_json):
        self.model, self.key, self.poster = model, key, poster

    def generate(self, prompt: str, max_tokens: int, timeout: float) -> LLMText:
        key = self.key()
        if not key:
            raise ProviderError("not_configured")
        body = json.dumps(
            {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "responseMimeType": "application/json",
                },
            }
        )
        target = f"/v1beta/models/{quote(self.model, safe='')}:generateContent"
        # The key travels in a header so it can never appear in a URL or a log of one.
        status, data, reply_headers = self.poster(
            self.host, target, {"x-goog-api-key": key}, body.encode(), timeout
        )
        classify(status, reply_headers)
        payload = decode(data)
        try:
            parts = payload["candidates"][0]["content"]["parts"]
            text = "".join(part["text"] for part in parts)
        except KeyError, IndexError, TypeError:
            raise ProviderError("malformed_response") from None
        usage = payload.get("usageMetadata") if isinstance(payload, dict) else None
        usage = usage if isinstance(usage, dict) else {}
        return LLMText(text, usage.get("promptTokenCount"), usage.get("candidatesTokenCount"))
