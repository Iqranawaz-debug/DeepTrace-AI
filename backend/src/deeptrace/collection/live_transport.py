"""Connect-time pinned HTTP(S) using only the standard library.

The socket connects to the numeric address that passed policy; TLS still verifies the
certificate and SNI against the original hostname. http.client never reads proxy
settings, never follows redirects and never re-resolves the host.
"""

import http.client
import socket
import ssl
import threading
import time
from collections.abc import Callable, Iterator
from urllib.parse import urlsplit

from deeptrace.collection.policy import CollectionError, resolve
from deeptrace.collection.transport import PinnedTransport, Reply


def bounded_resolve(host: str, timeout: float = 5.0) -> list[str]:
    """getaddrinfo has no deadline of its own, so it runs in a disposable daemon thread."""
    result: list[list[str]] = []

    def work() -> None:
        try:
            result.append(resolve(host))
        except OSError:
            result.append([])

    thread = threading.Thread(target=work, name="dns-resolve", daemon=True)
    thread.start()
    thread.join(timeout)
    if not result or not result[0]:
        raise CollectionError("dns_failed")
    return result[0]


class PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, address: str, host: str, port: int, timeout: float):
        super().__init__(host, port, timeout=timeout)
        self.pinned_address = address

    def connect(self) -> None:
        self.sock = socket.create_connection((self.pinned_address, self.port), self.timeout)


class PinnedHTTPSConnection(PinnedHTTPConnection):
    def connect(self) -> None:
        context = tls_context()
        raw = socket.create_connection((self.pinned_address, self.port), self.timeout)
        try:
            self.sock = context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


def tls_context() -> ssl.SSLContext:
    """CERT_REQUIRED and hostname checking against the OS trust store."""
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    return context


def open_pinned(
    method: str,
    scheme: str,
    address: str,
    host: str,
    port: int,
    target: str,
    timeout: float,
    headers: dict[str, str],
    body: bytes | None = None,
) -> tuple[http.client.HTTPConnection, http.client.HTTPResponse]:
    kind = PinnedHTTPSConnection if scheme == "https" else PinnedHTTPConnection
    connection = kind(address, host, port, timeout)
    try:
        connection.request(method, target, body=body, headers=headers)
        return connection, connection.getresponse()
    except ssl.SSLError:
        connection.close()
        raise CollectionError("tls_failed") from None
    except TimeoutError:
        connection.close()
        raise
    except OSError, http.client.HTTPException:
        connection.close()
        raise CollectionError("fetch_failed") from None


def connect_pinned(
    url: str, address: str, host: str, port: int, timeout: float, headers: dict[str, str]
) -> Reply:
    parts = urlsplit(url)
    target = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
    connection, response = open_pinned(
        "GET", parts.scheme, address, host, port, target, timeout, headers
    )

    def chunks() -> Iterator[bytes]:
        try:
            while chunk := response.read(65536):
                yield chunk
        except TimeoutError:
            raise
        except OSError, http.client.HTTPException:
            raise CollectionError("fetch_failed") from None
        finally:
            connection.close()

    return Reply(response.status, {k.lower(): v for k, v in response.getheaders()}, chunks())


class LiveTransport:
    """Public-web retrieval: policy-checked DNS, pinned connect, per-host pacing."""

    def __init__(
        self,
        resolver: Callable[[str], list[str]] = bounded_resolve,
        connector: Callable[..., Reply] = connect_pinned,
        interval: float = 1.0,
    ):
        self.pinned = PinnedTransport(resolver, connector)
        self.interval = interval
        self.last: dict[str, float] = {}

    def get(self, url: str, timeout: float) -> Reply:
        host = urlsplit(url).hostname or ""
        wait = self.last.get(host, 0.0) + self.interval - time.monotonic()
        if wait > 0:
            time.sleep(min(wait, self.interval))
        self.last[host] = time.monotonic()
        return self.pinned.get(url, timeout)
