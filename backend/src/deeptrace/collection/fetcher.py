"""Bounded, redirect-aware, fail-closed robots retrieval over injected transport."""

import time
import zlib
from collections.abc import Callable
from typing import Protocol
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

from deeptrace.collection.policy import CollectionError, normalize_url
from deeptrace.collection.transport import Reply

LIMIT = 5_000_000
ROBOTS_MISSING = frozenset({404, 410})
# Failures whose real cause is reported as-is; anything else about robots.txt is "unavailable".
PASS_THROUGH = frozenset(
    {"consent_revoked", "timeout", "dns_failed", "blocked_destination", "tls_failed", "blocked"}
)


class Transport(Protocol):
    def get(self, url: str, timeout: float) -> Reply: ...


class Fetcher:
    def __init__(self, transport: Transport, allowed: Callable[[], bool] = lambda: False):
        self.transport, self.allowed = transport, allowed

    def request(
        self,
        url: str,
        deadline: float,
        limit: int = LIMIT,
        permitted: Callable[[str], bool] = lambda _: True,
        missing_ok: bool = False,
    ) -> tuple[str, bytes, str]:
        for redirect in range(6):
            if not self.allowed():
                raise CollectionError("consent_revoked")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise CollectionError("timeout")
            url = normalize_url(url)
            if not permitted(url):
                raise CollectionError("robots_blocked")
            try:
                response = self.transport.get(url, remaining)
            except TimeoutError:
                raise CollectionError("timeout") from None
            if response.status in {301, 302, 303, 307, 308}:
                if redirect == 5 or not response.headers.get("location"):
                    raise CollectionError("redirect_limit")
                target = normalize_url(urljoin(url, response.headers["location"]))
                if (urlsplit(url).scheme, urlsplit(url).netloc) != (
                    urlsplit(target).scheme,
                    urlsplit(target).netloc,
                ):
                    raise CollectionError("unsafe_redirect")
                url = target
                continue
            if missing_ok and response.status in ROBOTS_MISSING:
                return url, b"", "text/plain"
            if response.status != 200:
                raise CollectionError(
                    "blocked" if response.status in {401, 403, 429} else "fetch_failed"
                )
            mime = response.headers.get("content-type", "").split(";")[0].strip().lower()
            if mime not in {"text/html", "text/plain"}:
                raise CollectionError("unsupported")
            encoding = response.headers.get("content-encoding", "identity").lower()
            if encoding not in {"identity", "gzip"}:
                raise CollectionError("unsupported_encoding")
            decoder = zlib.decompressobj(16 + zlib.MAX_WBITS) if encoding == "gzip" else None
            result = bytearray()
            received = 0
            try:
                for chunk in response.chunks:
                    if not self.allowed():
                        raise CollectionError("consent_revoked")
                    if time.monotonic() >= deadline:
                        raise CollectionError("timeout")
                    received += len(chunk)
                    if received > limit:
                        raise CollectionError("response_too_large")
                    part = decoder.decompress(chunk, limit + 1 - len(result)) if decoder else chunk
                    result.extend(part)
                    if len(result) > limit or (decoder and decoder.unconsumed_tail):
                        raise CollectionError("response_too_large")
                if decoder and (not decoder.eof or decoder.unused_data):
                    raise CollectionError("invalid_compression")
            except zlib.error:
                raise CollectionError("invalid_compression") from None
            return url, bytes(result), mime
        raise CollectionError("redirect_limit")

    def fetch(self, url: str) -> tuple[str, bytes, str]:
        url = normalize_url(url)
        deadline = time.monotonic() + 15
        origin = urlsplit(url)
        robots_url = f"{origin.scheme}://{origin.netloc}/robots.txt"
        # ADR-A13 as clarified 2026-11-09, following RFC 9309: a disallow is always honoured;
        # a missing or empty robots.txt means no restrictions; if it cannot be read, the page
        # is skipped and the real reason is kept, so a DNS failure is never reported as a refusal.
        try:
            _, body, _ = self.request(robots_url, deadline, 100_000, missing_ok=True)
        except CollectionError as exc:
            if exc.code in PASS_THROUGH:
                raise
            raise CollectionError("robots_unavailable") from None
        robots = RobotFileParser()
        try:
            robots.parse(body.decode("utf-8", errors="strict").splitlines())
        except UnicodeError:
            raise CollectionError("robots_unavailable") from None
        if not robots.can_fetch("DeepTraceAI", url):
            raise CollectionError("robots_blocked")
        return self.request(
            url, deadline, permitted=lambda target: robots.can_fetch("DeepTraceAI", target)
        )
