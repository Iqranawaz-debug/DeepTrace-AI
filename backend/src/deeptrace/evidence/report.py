"""Deterministic, template-based Markdown reports. No model generates or edits text here.

Every user-authored or source-derived string is escaped so it cannot introduce
links, images, HTML, headings, lists or tables. URLs and hashes are emitted as
code spans, which Markdown renders literally.
"""

import re
from dataclasses import dataclass, field

REPORT_SCHEMA_VERSION = "manual-report-v1"
TEMPLATE_VERSION = "manual-template-v1"
MAX_REPORT_CHARS = 2_000_000

CLAIM_LABELS = {
    "finding": "Finding",
    "interpretation": "Interpretation",
    "conflict": "Conflicting evidence",
    "hypothesis": "Unsupported hypothesis",
    "gap": "Missing evidence",
    "conclusion": "User conclusion",
}
RELATION_LABELS = {
    "supports": "cited as support",
    "contradicts": "cited as contradicting",
    "context": "cited as context",
}
STANCE_LABELS = {
    "supports": "Supporting (user judgment)",
    "contradicts": "Contradicting (user judgment)",
    "context": "Context (user judgment)",
    "insufficient": "Insufficient (user judgment)",
    "unreviewed": "Not yet reviewed",
}

# Characters that can open emphasis, code, links/images, raw HTML, entities, tables or
# strikethrough anywhere in a line. Line-start markers are handled in escape_block.
_INLINE = re.compile(r"([\\`*_\[\]<>|~&])")
_LINE_START = re.compile(r"^(#|>|-|\+|=|\d+[.)])")


def escape(text: str) -> str:
    """Escape one line of untrusted text for CommonMark/GFM. Newlines become spaces."""
    return _INLINE.sub(r"\\\1", " ".join(text.split()))


def escape_block(text: str) -> list[str]:
    """Escape a multi-line field paragraph by paragraph; blank lines separate paragraphs."""
    paragraphs = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    lines: list[str] = []
    for paragraph in paragraphs:
        # A paragraph must not become a heading, quote, list, or setext/thematic break.
        marker = _LINE_START.sub(
            lambda m: m.group(1)[:-1] + "\\" + m.group(1)[-1], escape(paragraph)
        )
        lines.append(marker)
        lines.append("")
    return lines


def code(text: str) -> str:
    """Literal code span; the fence is longer than any backtick run inside."""
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    fence = "`" * (longest + 1)
    return f"{fence} {' '.join(text.split())} {fence}"


@dataclass(frozen=True)
class SourceRef:
    id: str
    title: str | None
    original_url: str
    canonical_url: str
    status: str
    origin: str
    fetched_at: str | None
    extracted_at: str | None
    extraction_version: str | None
    text_sha256: str | None
    limitation: str | None


@dataclass(frozen=True)
class CitationRef:
    display_id: str
    source_id: str
    relation: str
    start_offset: int
    end_offset: int
    quoted_text: str | None
    reference_valid: bool
    quote_valid: bool | None
    reason: str | None


@dataclass(frozen=True)
class ClaimRef:
    ordinal: int
    claim_type: str
    text: str
    evidence_state: str
    citations: list[CitationRef] = field(default_factory=list)


@dataclass(frozen=True)
class NoteRef:
    display_id: str
    source_id: str
    target_label: str
    stance: str
    note: str | None


@dataclass(frozen=True)
class ReportInput:
    title: str
    question: str
    scope: str | None
    methodology: str | None
    summary: str | None
    limitations: str | None
    next_steps: str | None
    mode: str
    version_no: int
    created_at: str
    answer_revision: int
    claims: list[ClaimRef]
    notes: list[NoteRef]
    sources: dict[str, SourceRef]
    saved_url_count: int
    run_count: int


def summary(report: ReportInput) -> dict[str, int]:
    citations = [c for claim in report.claims for c in claim.citations]
    return {
        "claims": len(report.claims),
        "claims_cited": sum(c.evidence_state == "cited" for c in report.claims),
        "claims_not_established": sum(c.evidence_state != "cited" for c in report.claims),
        "citations": len(citations),
        "citations_reference_valid": sum(c.reference_valid for c in citations),
        "quotations": sum(c.quoted_text is not None for c in citations),
        "quotations_matched": sum(c.quote_valid is True for c in citations),
        "evidence_notes": len(report.notes),
        "sources_referenced": len(report.sources),
    }


def _section(lines: list[str], heading: str, body: str | None, empty: str) -> None:
    lines += [f"## {heading}", ""]
    lines += escape_block(body) if body and body.strip() else [f"_{empty}_", ""]


def render(report: ReportInput) -> str:
    counts = summary(report)
    simulated = report.mode == "mock"
    lines = [f"# {escape(report.title)}", ""]
    lines += [
        "> **Research aid, not verified research.** Claims, classifications and conclusions "
        "below were written or selected by the user. DeepTrace AI checked only that each "
        "cited passage exists in this investigation and that quotations match the saved "
        "text. A valid citation does not show that a source supports a claim, and no "
        "automated semantic, factual or legal verification was performed. Verify important "
        "findings using original sources.",
        "",
    ]
    if simulated:
        lines += [
            "> **SIMULATED EVIDENCE.** Passages in this report come from application-owned "
            "synthetic fixtures. No live website, search provider or AI model was contacted. "
            "These passages support no conclusions about the world.",
            "",
        ]
    lines += [
        f"- Report version: {report.version_no} (immutable snapshot)",
        f"- Created (UTC): {code(report.created_at)}",
        f"- Draft revision: {report.answer_revision}",
        f"- Mode: {'mock (synthetic fixtures)' if simulated else escape(report.mode)}",
        f"- Template: {code(TEMPLATE_VERSION)}; no language model was used.",
        "",
        "## Question",
        "",
        *escape_block(report.question),
    ]
    _section(lines, "Scope", report.scope, "No scope notes recorded.")
    _section(lines, "Summary", report.summary, "No summary written.")

    lines += ["## Findings and claims", ""]
    if not report.claims:
        lines += ["_No claims recorded. Nothing in this report is presented as a finding._", ""]
    for claim in report.claims:
        state = (
            "Cited"
            if claim.evidence_state == "cited"
            else "Not established — no valid supporting citation"
        )
        label = CLAIM_LABELS.get(claim.claim_type, "Claim")
        lines += [f"### Claim {claim.ordinal}. {label} · {state}", "", *escape_block(claim.text)]
        for citation in claim.citations:
            source = report.sources.get(citation.source_id)
            name = escape(source.title) if source and source.title else "Untitled source"
            check = (
                "reference valid"
                if citation.reference_valid
                else f"REFERENCE INVALID ({escape(citation.reason or 'unknown')})"
            )
            lines.append(
                f"- {code(citation.display_id)} {RELATION_LABELS.get(citation.relation, '')}"
                f" — {name}; characters {citation.start_offset}–{citation.end_offset}; {check}"
            )
            if citation.quoted_text is not None:
                verdict = (
                    "quotation matches saved text"
                    if citation.quote_valid
                    else "QUOTATION DOES NOT MATCH saved text; not presented as a quote"
                )
                quote = escape(citation.quoted_text) if citation.quote_valid else "withheld"
                lines.append(f"  - Quoted: “{quote}” ({verdict})")
        if not claim.citations:
            lines.append("- No citations attached.")
        lines.append("")

    groups = {
        "Supporting Evidence": ["supports"],
        "Conflicting or Missing Evidence": ["contradicts", "insufficient"],
        "Contextual and Unreviewed Evidence": ["context", "unreviewed"],
    }
    for heading, stances in groups.items():
        lines += [f"## {heading}", ""]
        selected = [n for n in report.notes if n.stance in stances]
        if not selected:
            lines += ["_None recorded._", ""]
        for note in selected:
            source = report.sources.get(note.source_id)
            name = escape(source.title) if source and source.title else "Untitled source"
            lines.append(
                f"- {code(note.display_id)} — {name} — for: {escape(note.target_label)} — "
                f"{STANCE_LABELS[note.stance]}"
            )
            if note.note:
                lines.append(f"  - User note: {escape(note.note)}")
        lines.append("")

    _section(lines, "Limitations", report.limitations, "No limitations written by the user.")
    lines += [
        "Automatically recorded limitations:",
        "",
        f"- {counts['claims_not_established']} of {counts['claims']} claims are not "
        "established by a valid supporting citation.",
        "- Evidence classifications are user judgments and were not independently validated.",
        "- Extracted text may be incomplete; see each source's extraction limitation below.",
        "",
    ]
    _section(lines, "Unanswered Questions and Next Steps", report.next_steps, "None recorded.")
    _section(lines, "Methodology", report.methodology, "No methodology notes written.")
    lines += [
        "Recorded process:",
        "",
        f"- Collection runs recorded for this investigation: {report.run_count}.",
        f"- URLs saved but never retrieved (not evidence): {report.saved_url_count}.",
        "- No search queries were executed; live search and live fetching are disabled.",
        f"- Citations checked: {counts['citations_reference_valid']} of {counts['citations']} "
        f"references valid; {counts['quotations_matched']} of {counts['quotations']} "
        "quotations match saved text (NFC and whitespace-normalized, case-sensitive).",
        "",
        "## References",
        "",
    ]
    if not report.sources:
        lines += ["_No sources are cited or reviewed in this report._", ""]
    for source in sorted(report.sources.values(), key=lambda s: s.id):
        lines += [
            f"- {escape(source.title) if source.title else 'Untitled source'}",
            f"  - Source ID: {code(source.id)}",
            f"  - Original URL: {code(source.original_url)}",
            f"  - Canonical URL: {code(source.canonical_url)}",
            f"  - Status: {escape(source.status)}; origin: {escape(source.origin)}",
            "  - Retrieved (UTC): "
            + (code(source.fetched_at) if source.fetched_at else "not retrieved"),
            f"  - Extracted (UTC): {code(source.extracted_at) if source.extracted_at else 'none'}"
            f"; extraction version: {code(source.extraction_version or 'none')}",
            f"  - SHA-256 of saved text: {code(source.text_sha256 or 'none')}",
            "  - Author and publication date: unknown; not inferred.",
        ]
        if source.limitation:
            lines.append(f"  - Limitation: {escape(source.limitation)}")
    lines.append("")
    return "\n".join(lines)
