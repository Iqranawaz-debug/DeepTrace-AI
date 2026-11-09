"""FR-07 report for generated answers. Model and source text are untrusted and escaped."""

from dataclasses import dataclass
from typing import Any

from deeptrace.evidence.report import code, escape, escape_block
from deeptrace.storage.research_repository import ValidatedClaim

GENERATED_SCHEMA_VERSION = "generated-report-v1"
DISCLAIMER = "AI-generated research aid. Verify important findings using original sources."


@dataclass(frozen=True)
class GeneratedInput:
    title: str
    question: str
    summary: str
    limitations: str | None
    needed: str | None
    claims: list[ValidatedClaim]
    sources: list[dict[str, Any]]
    queries: list[dict[str, Any]]
    omissions: list[str]
    provider: str
    model: str
    prompt_version: str
    search_provider: str
    mode: str
    version_no: int
    created_at: str
    stopped: str | None = None


def counts(report: GeneratedInput) -> dict[str, int]:
    citations = [cite for claim in report.claims for cite in claim.citations]
    return {
        "claims": len(report.claims),
        "claims_cited": sum(c.state == "cited" for c in report.claims),
        "claims_not_established": sum(c.state != "cited" for c in report.claims),
        "citations": len(citations),
        "quotations_matched": sum(c.quote is not None for c in citations),
        "citations_suppressed": sum(c.suppressed for c in report.claims),
        "sources_considered": len(report.sources),
        "sources_with_text": sum(s["status"] in {"fetched", "partial"} for s in report.sources),
        "search_queries": len(report.queries),
    }


def render(report: GeneratedInput) -> str:
    totals = counts(report)
    simulated = report.mode == "mock"
    names = {s["id"]: s for s in report.sources}
    lines = [f"# {escape(report.title)}", "", f"> **{DISCLAIMER}**", ""]
    if simulated:
        lines += [
            "> **SIMULATED RESEARCH.** This report was produced by mock providers from "
            "application-owned synthetic fixtures. It contains no real research and supports "
            "no conclusions about the world.",
            "",
        ]
    if report.stopped:
        lines += [
            f"> **PARTIAL REPORT.** Stopped: {escape(report.stopped)} reached. No answer was "
            "drafted and no language model was used for this report. Partial results are shown "
            "and may be incomplete.",
            "",
        ]
    lines += [
        "> A citation shows that a passage exists in this investigation and that any quotation "
        "matches it. It does not show that the passage supports the claim. No semantic support "
        "assessment was performed in this version.",
        "",
        f"- Report version: {report.version_no} (immutable snapshot)",
        f"- Created (UTC): {code(report.created_at)}",
        "",
        "## Question",
        "",
        *escape_block(report.question),
        "## Summary",
        "",
        *(escape_block(report.summary) or ["_No summary was produced._", ""]),
        "## Findings",
        "",
    ]
    if not report.claims:
        lines += ["_No findings were produced. Evidence was insufficient._", ""]
    for number, claim in enumerate(report.claims, 1):
        state = "Cited" if claim.state == "cited" else "Not established"
        lines += [f"### Finding {number} · {state}", "", *escape_block(claim.text)]
        if claim.explanation:
            lines += [f"_{escape(claim.explanation)}_", ""]
    lines += ["## Supporting Evidence", ""]
    cited = [(n, c) for n, claim in enumerate(report.claims, 1) for c in claim.citations]
    if not cited:
        lines.append("_No validated citations._")
    for number, cite in cited:
        source = names.get(cite.source_id)
        title = escape(source["title"]) if source and source.get("title") else "Untitled source"
        lines.append(f"- Finding {number}: {code(cite.display_id)} — {title}")
        if cite.quote is not None:
            lines.append(f"  - Quotation matching saved text: “{escape(cite.quote)}”")
    lines += ["", "## Conflicting or Missing Evidence", ""]
    unestablished = [n for n, c in enumerate(report.claims, 1) if c.state != "cited"]
    if unestablished:
        joined = ", ".join(str(n) for n in unestablished)
        lines += [f"Findings not established by a validated citation: {joined}.", ""]
    lines += (
        escape_block(report.needed)
        if report.needed
        else [
            "_No missing evidence was recorded. Conflicts are not detected automatically in "
            "this version._",
            "",
        ]
    )
    lines += ["## Limitations", ""]
    lines += escape_block(report.limitations) if report.limitations else []
    lines += [
        f"- {totals['citations_suppressed']} citation(s) failed validation and were suppressed.",
        "- Extracted text may be incomplete; JavaScript was not executed.",
        "- Evidence independence is not established: different sites may share an original.",
        "",
        "## Methodology",
        "",
        f"- Mode: {'mock (simulated providers)' if simulated else 'live free tier'}",
        f"- Search provider: {code(report.search_provider)}",
        f"- Language model: {code(report.provider)} / {code(report.model)}",
        f"- Prompt version: {code(report.prompt_version)}",
        f"- Sources considered: {totals['sources_considered']}; with saved text: "
        f"{totals['sources_with_text']}.",
        f"- Validated citations: {totals['citations']}; matched quotations: "
        f"{totals['quotations_matched']} (NFC and whitespace-normalized, case-sensitive).",
        "",
        "Search queries:",
        "",
    ]
    if not report.queries:
        lines.append("- None executed.")
    for query in report.queries:
        count = query["results_count"] if query["results_count"] is not None else "unknown"
        lines.append(f"- {code(query['query_text'])} — {escape(query['status'])}; results: {count}")
    lines += ["", "Important omissions:", ""]
    lines += [f"- {escape(item)}" for item in report.omissions] or ["- None recorded."]
    lines += ["", "## References", ""]
    if not report.sources:
        lines.append("_No sources were considered._")
    for source in report.sources:
        lines += [
            f"- {escape(source['title']) if source.get('title') else 'Untitled source'}",
            f"  - Source ID: {code(source['id'])}",
            f"  - Original URL: {code(source['original_url'])}",
            f"  - Canonical URL: {code(source['canonical_url'])}",
            f"  - Status: {escape(source['status'])}; origin: {escape(source['origin'])}",
            "  - Retrieved (UTC): "
            + (code(source["fetched_at"]) if source["fetched_at"] else "not retrieved"),
            "  - Author: " + (escape(source["author"]) if source.get("author") else "Unknown"),
            "  - Published: "
            + (escape(source["published_at"]) if source.get("published_at") else "Unknown"),
            f"  - Extraction version: {code(source['extraction_version'] or 'none')}",
            f"  - SHA-256 of saved text: {code(source['text_sha256'] or 'none')}",
        ]
        if source.get("limitation"):
            lines.append(f"  - Limitation: {escape(source['limitation'])}")
    lines.append("")
    return "\n".join(lines)
