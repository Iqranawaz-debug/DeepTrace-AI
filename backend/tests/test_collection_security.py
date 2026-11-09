import gzip
import hashlib
import time

import pytest

from deeptrace.collection.extractor import extract
from deeptrace.collection.fetcher import Fetcher
from deeptrace.collection.parser_process import parse
from deeptrace.collection.passages import slices
from deeptrace.collection.policy import CollectionError, destinations, normalize_url
from deeptrace.collection.transport import DisabledTransport, PinnedTransport, Reply


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/a",
        "http://localhost/a",
        "http://127.0.0.1",
        "http://169.254.169.254",
        "http://10.0.0.1",
        "http://172.16.0.1",
        "http://192.168.1.1",
        "http://[::1]",
        "http://[::ffff:127.0.0.1]",
        "http://[64:ff9b::7f00:1]",
        "http://2130706433",
        "http://0x7f000001",
        "http://127.1",
        "https://user:secret@example.com",
        "https://example.com:8443",
        "https://example.com./",
        "https://foo.local",
        "https://foo.internal",
        "https://example.com\\@127.0.0.1",
        "https://example.com/\nsecret",
    ],
)
def test_rejected_urls(url):
    with pytest.raises(CollectionError):
        normalize_url(url)


def test_mixed_dns_and_rebinding_fail_before_connection():
    called = []
    transport = PinnedTransport(
        lambda _: ["93.184.216.34", "127.0.0.1"], lambda *args: called.append(args)
    )
    with pytest.raises(CollectionError):
        transport.get("https://fixture.example/article", 1)
    assert called == []
    with pytest.raises(CollectionError):
        destinations("https://fixture.example/", lambda _: [])


def test_pinned_contract_and_proxy_isolation(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://user:secret@localhost:9")
    calls = []

    def connector(*args):
        calls.append(args)
        return Reply(200, {"content-type": "text/plain"}, [b"synthetic"])

    PinnedTransport(lambda _: ["93.184.216.34"], connector).get("https://fixture.example/a", 1)
    _, address, host, port, timeout, headers = calls[0]
    assert (address, host, port, timeout) == ("93.184.216.34", "fixture.example", 443, 1)
    assert set(headers) == {"Host", "User-Agent", "Accept", "Accept-Encoding"}
    with pytest.raises(CollectionError, match="live_network_disabled"):
        DisabledTransport().get("https://fixture.example/a", 1)


class Responses:
    def __init__(self, replies):
        self.replies = replies
        self.calls = []

    def get(self, url, timeout):
        self.calls.append(url)
        return self.replies[url]


def test_redirect_robots_checked_before_target():
    origin = "https://fixture.example"
    transport = Responses(
        {
            origin + "/robots.txt": Reply(
                200, {"content-type": "text/plain"}, [b"User-agent: *\nDisallow: /private"]
            ),
            origin + "/a": Reply(302, {"location": "/private"}, []),
        }
    )
    with pytest.raises(CollectionError, match="robots_blocked"):
        Fetcher(transport, lambda: True).fetch(origin + "/a")
    assert transport.calls == [origin + "/robots.txt", origin + "/a"]


@pytest.mark.parametrize(
    "target", ["https://other.example/a", "http://fixture.example/a", "http://127.0.0.1/a"]
)
def test_redirect_never_connects_to_unapproved_target(target):
    transport = Responses({"https://fixture.example/a": Reply(302, {"location": target}, [])})
    with pytest.raises(CollectionError):
        Fetcher(transport, lambda: True).request("https://fixture.example/a", time.monotonic() + 2)
    assert len(transport.calls) == 1


@pytest.mark.parametrize(
    "reply,code",
    [
        (Reply(200, {"content-type": "text/plain"}, [b"a" * 101]), "response_too_large"),
        (
            Reply(
                200,
                {"content-type": "text/html", "content-encoding": "gzip"},
                [gzip.compress(b"a" * 10000)],
            ),
            "response_too_large",
        ),
        (
            Reply(200, {"content-type": "text/html", "content-encoding": "gzip"}, [b"bad"]),
            "invalid_compression",
        ),
        (Reply(200, {"content-type": "application/pdf"}, [b"pdf"]), "unsupported"),
        (Reply(403, {}, []), "blocked"),
    ],
)
def test_fetch_limits(reply, code):
    transport = Responses({"https://fixture.example/a": reply})
    with pytest.raises(CollectionError, match=code):
        Fetcher(transport, lambda: True).request(
            "https://fixture.example/a", time.monotonic() + 2, 100
        )


def test_timeout_and_revocation_between_chunks():
    transport = Responses(
        {"https://fixture.example/a": Reply(200, {"content-type": "text/plain"}, [b"ok"])}
    )
    with pytest.raises(CollectionError, match="timeout"):
        Fetcher(transport, lambda: True).request("https://fixture.example/a", time.monotonic() - 1)
    decisions = iter([True, False])
    with pytest.raises(CollectionError, match="consent_revoked"):
        Fetcher(transport, lambda: next(decisions)).request(
            "https://fixture.example/a", time.monotonic() + 2
        )


@pytest.mark.parametrize(
    "tag",
    ["script", "style", "nav", "footer", "header", "aside", "form", "svg", "template", "noscript"],
)
def test_extraction_excludes_noncontent(tag):
    html = (
        f"<title>Synthetic</title><main><{tag}>SECRET</{tag}>"
        "<p>Evidence &amp; <b>inline</b> text.</p></main>"
    )
    result = extract(html.encode(), "text/html")
    assert result.text == "Evidence & inline text."
    assert result.title == "Synthetic"
    assert result.text_sha256 == hashlib.sha256(result.text.encode()).hexdigest()


@pytest.mark.parametrize(
    "body,code",
    [
        (b"x" * 1_000_001, "extraction_input_limit"),
        (b"<div>" * 129, "structure_limit"),
        (b"<br>" * 25001, "structure_limit"),
        (b"<main>" + b"x" * 200001 + b"</main>", "extraction_output_limit"),
        (b"<script>x</script>", "empty_content"),
        (b"\xff", "unsupported_encoding"),
    ],
    ids=["input", "depth", "nodes", "output", "empty", "encoding"],
)
def test_parser_limits(body, code):
    with pytest.raises(CollectionError, match=code):
        extract(body, "text/html")


def test_unicode_passage_offsets_and_killable_parser():
    text = ("Synthetic café 🧪 evidence. " * 300).strip()
    result = parse(f"<main>{text}</main>".encode(), "text/html")
    chunks = list(slices(result.text))
    assert "".join(part for _, _, part in chunks) == result.text
    for start, end, part in chunks:
        assert result.text[start:end] == part
    with pytest.raises(CollectionError, match="parser_timeout"):
        parse(b"<main>synthetic</main>", "text/html", timeout=0.000001)


def test_ambiguous_and_hidden_content_are_honest():
    result = extract(
        b"<body><div hidden><span hidden>HIDDEN</span></div><p>Visible</p></body>", "text/html"
    )
    assert result.text == "Visible"
    assert result.status == "partial"
