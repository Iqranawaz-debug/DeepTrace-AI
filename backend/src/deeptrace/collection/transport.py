"""Transport contract carries pinned destination separately from TLS hostname.

No production socket connector is supplied in this phase. Fake connectors must
assert the numeric address and the original host/SNI independently.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from urllib.parse import urlsplit

from deeptrace.collection.policy import destinations, require_live_permission


@dataclass(frozen=True)
class Reply:
    status: int
    headers: dict[str, str]
    chunks: Iterable[bytes]


Connector = Callable[[str, str, str, int, float, dict[str, str]], Reply]


class PinnedTransport:
    def __init__(self, resolver: Callable[[str], list[str]], connector: Connector):
        self.resolver, self.connector = resolver, connector

    def get(self, url: str, timeout: float) -> Reply:
        host, addresses = destinations(url, self.resolver)
        parsed = urlsplit(url)
        # Never pass cookies, authorization, proxy settings or browser headers.
        headers = {
            "Host": host,
            "User-Agent": "DeepTraceAI/0.1 evidence-collection",
            "Accept-Encoding": "gzip",
            "Accept": "text/html,text/plain",
        }
        return self.connector(
            url, addresses[0], host, 443 if parsed.scheme == "https" else 80, timeout, headers
        )


class DisabledTransport:
    def get(self, url: str, timeout: float) -> Reply:
        require_live_permission()
        raise AssertionError("unreachable")
