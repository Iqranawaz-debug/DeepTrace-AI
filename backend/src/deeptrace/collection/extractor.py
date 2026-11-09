"""Conservative text extraction. Does not fetch, execute HTML, or infer metadata."""

import hashlib
from dataclasses import asdict, dataclass
from html.parser import HTMLParser

from bs4 import BeautifulSoup

from deeptrace.collection.policy import CollectionError

# v2: separators for tables, h5/h6, quotes, definition lists and figures; <head> title only.
# v3: source-declared author and publication date from <meta>, when present.
VERSION = "bs4-4.15.0-html.parser-v3"
MAX_INPUT = 1_000_000
MAX_TEXT = 200_000
BLOCKS = [
    "p", "div", "section", "article", "main", "h1", "h2", "h3", "h4", "h5", "h6", "li",
    "ul", "ol", "dl", "dt", "dd", "tr", "table", "caption", "blockquote", "pre",
    "figure", "figcaption", "address", "details", "summary", "hr", "br",
]  # fmt: skip


class StructureLimit(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.nodes = 0
        self.depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.nodes += 1
        if tag not in {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        }:
            self.depth += 1
        if self.nodes > 25000 or self.depth > 128:
            raise CollectionError("structure_limit")

    def handle_endtag(self, tag: str) -> None:
        self.depth = max(0, self.depth - 1)


@dataclass
class Extraction:
    text: str
    title: str | None
    status: str
    limitation: str
    text_sha256: str
    extraction_version: str = VERSION
    normalization_version: str = "whitespace-v1"
    author: str | None = None
    published_at: str | None = None

    def json(self) -> dict[str, str | None]:
        return asdict(self)


def declared_meta(soup: BeautifulSoup, names: tuple[str, ...]) -> str | None:
    for node in soup.find_all("meta"):
        key = str(node.get("name") or node.get("property") or "").lower()
        content = " ".join(str(node.get("content") or "").split())
        if key in names and content:
            return content[:300]
    return None


def extract(body: bytes, mime: str) -> Extraction:
    if len(body) > MAX_INPUT:
        raise CollectionError("extraction_input_limit")
    try:
        html = body.decode("utf-8-sig", errors="strict")
    except UnicodeError:
        raise CollectionError("unsupported_encoding") from None
    title = author = published = None
    status = "fetched"
    limitation = "Extracted text is not verification of accuracy or completeness."
    if mime == "text/html":
        guard = StructureLimit()
        guard.feed(html)
        soup = BeautifulSoup(html, "html.parser")
        # Only a document-level <title> is source-declared; an <svg><title> is an icon label.
        declared = soup.head.title if soup.head else None
        if declared is None:
            declared = next((t for t in soup.find_all("title") if not t.find_parent("svg")), None)
        if declared:
            title = " ".join(declared.get_text(" ", strip=True).split())[:300] or None
        # Only what the page itself declares; absent values stay unknown (FR-W8).
        author = declared_meta(soup, ("author", "article:author"))
        published = declared_meta(
            soup, ("article:published_time", "date", "datepublished", "dc.date")
        )
        for node in soup.find_all(
            [
                "script",
                "style",
                "noscript",
                "template",
                "nav",
                "footer",
                "header",
                "aside",
                "form",
                "svg",
            ]
        ):
            node.decompose()
        for node in soup.select('[hidden], [aria-hidden="true"]'):
            node.decompose()
        regions = soup.find_all("main") or soup.find_all("article")
        if len(regions) == 1:
            root = regions[0]
        else:
            root = soup.body or soup
            status = "partial"
            limitation = (
                "Main content was ambiguous; conservative body extraction may include "
                "boilerplate or omit content."
            )
        # Only block boundaries get line separators: inline words must not be reordered.
        for node in root.find_all(BLOCKS):
            node.insert_before("\n")
            node.insert_after("\n")
        # Adjacent cells must not merge words ("alpha" + "beta" -> "alphabeta").
        for node in root.find_all(["td", "th"]):
            node.insert_before(" ")
            node.insert_after(" ")
        text = root.get_text()
    elif mime == "text/plain":
        text = html
    else:
        raise CollectionError("unsupported")
    text = "\n\n".join(" ".join(line.split()) for line in text.splitlines() if line.strip())
    if not text:
        raise CollectionError("empty_content")
    if len(text) > MAX_TEXT:
        raise CollectionError("extraction_output_limit")
    if len(text) < 80:
        status = "partial"
        limitation = (
            "Very little readable text; the page may require scripts or contain incomplete content."
        )
    return Extraction(
        text,
        title,
        status,
        limitation,
        hashlib.sha256(text.encode()).hexdigest(),
        author=author,
        published_at=published,
    )
