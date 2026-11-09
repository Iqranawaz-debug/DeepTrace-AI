"""Strict URL/DNS policy, separate from the permanently closed live gate."""

import ipaddress
import re
import socket
from collections.abc import Callable
from urllib.parse import urlsplit, urlunsplit


class CollectionError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def normalize_url(value: str) -> str:
    if len(value) > 2048 or any(ord(c) < 33 or ord(c) == 127 for c in value) or "\\" in value:
        raise CollectionError("invalid_url")
    try:
        url = urlsplit(value)
        host = url.hostname or ""
        if (
            url.scheme not in {"http", "https"}
            or not host
            or url.username is not None
            or url.password is not None
        ):
            raise ValueError
        if (
            "%" in host
            or host.endswith(".")
            or url.port not in {None, 80 if url.scheme == "http" else 443}
        ):
            raise ValueError
        host = host.encode("idna").decode("ascii").lower()
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            raise CollectionError("blocked_destination")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            # WHATWG parsers treat a numeric or 0x-hex final label as an IPv4 address
            # (e.g. 0x7f.1, 1.2.3.4.5); reject such ambiguous hosts. Letter-only labels
            # such as bad.cafe are ordinary names.
            if "." not in host or re.fullmatch(r"0x[0-9a-f]*|[0-9]+", host.rsplit(".", 1)[1]):
                raise ValueError from None
        else:
            public_address(str(address))
            host = f"[{host}]" if address.version == 6 else host
        return urlunsplit((url.scheme, host, url.path or "/", url.query, ""))
    except ValueError, UnicodeError:
        raise CollectionError("invalid_url") from None


def public_address(value: str) -> str:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        raise CollectionError("blocked_destination") from None
    if (
        not address.is_global
        or address.is_multicast
        or address.is_reserved
        or getattr(address, "ipv4_mapped", None)
        or getattr(address, "sixtofour", None)
        or getattr(address, "teredo", None)
    ):
        raise CollectionError("blocked_destination")
    # Translation prefixes must not tunnel a prohibited IPv4 destination.
    if address.version == 6 and address in ipaddress.ip_network("64:ff9b::/96"):
        raise CollectionError("blocked_destination")
    return str(address)


def resolve(host: str) -> list[str]:
    return list(
        {str(item[4][0]) for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)}
    )


def destinations(url: str, resolver: Callable[[str], list[str]]) -> tuple[str, list[str]]:
    host = urlsplit(normalize_url(url)).hostname
    assert host is not None
    try:
        answers = resolver(host)
    except Exception:
        raise CollectionError("dns_failed") from None
    if not answers:
        raise CollectionError("dns_failed")
    return host, [public_address(answer) for answer in answers]


def require_live_permission() -> None:
    # No environment flag, setting, consent record or key can open this gate.
    raise CollectionError("live_network_disabled")
