"""Reference and quote checks (ADR-A04, ADR-A14). Validity never implies semantic support."""

import hashlib
import unicodedata
from dataclasses import dataclass

VALIDATION_VERSION = "nfc-whitespace-v1"


def sha256(text: str) -> str:
    """SHA-256 of the exact UTF-8 bytes of the text; documents identity, not authenticity."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_quote(text: str) -> str:
    """NFC plus whitespace collapse. Case-sensitive; no paraphrase or fuzzy matching."""
    return " ".join(unicodedata.normalize("NFC", text).split())


def quote_matches(quote: str, passage_text: str) -> bool:
    normalized = normalize_quote(quote)
    return bool(normalized) and normalized in normalize_quote(passage_text)


@dataclass(frozen=True)
class PassageRecord:
    id: str
    investigation_id: str
    text: str
    removed: bool = False


@dataclass(frozen=True)
class CitationCheck:
    reference_valid: bool
    quote_valid: bool | None
    reason: str | None


def check_citation(
    investigation_id: str,
    passage: PassageRecord | None,
    quote: str | None,
    expected_passage_sha256: str | None = None,
) -> CitationCheck:
    """Reference validity: exists, active, same investigation and unchanged text."""
    if passage is None:
        return CitationCheck(False, None, "passage_not_found")
    if passage.investigation_id != investigation_id:
        # Callers must not reveal whether another investigation's passage exists.
        return CitationCheck(False, None, "passage_not_found")
    if passage.removed:
        return CitationCheck(False, None, "passage_removed")
    if expected_passage_sha256 is not None and sha256(passage.text) != expected_passage_sha256:
        return CitationCheck(False, None, "passage_changed")
    if quote is None:
        return CitationCheck(True, None, None)
    if not quote_matches(quote, passage.text):
        return CitationCheck(True, False, "quote_mismatch")
    return CitationCheck(True, True, None)
