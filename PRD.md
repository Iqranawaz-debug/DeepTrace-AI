# DeepTrace AI — Product Requirements Document

| Field | Value |
|---|---|
| Document | `PRD.md` |
| Version | 1.1.0 — proposed final baseline |
| Owner | Iqra Nawaz |
| Status | Ready for owner approval |
| Date | 2026-10-23 |
| Tagline | **Research you can trace.** |

> **Document rules.** `Must`, `Should`, `Could`, and `Won't` describe release priority, not current implementation status. Numerical targets are proposed acceptance targets, not achieved results. `FR` = functional, `NFR` = non-functional, `SEC` = security, `UX` = user experience, `EV` = evaluation, `AC` = acceptance. Maintain stable requirement IDs and record material changes in the changelog. This document specifies intended behavior; it does not assert that DeepTrace AI has already been built.

## Change log

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-10-23 | Initial 15-section proposal |
| 1.0.0 | 2026-10-23 | Expanded draft with traceability, evaluation, lifecycle, and security |
| 1.1.0 | 2026-10-23 | Focused delivery stages; clarified semantic grounding and confidence; reconciled priorities; hardened local/server and fetching security; scoped evaluation and benchmark targets |

## Contents

1. Executive Summary
2. Glossary
3. Problem Statement
4. Vision, Goals and Success Measures
5. Target Users
6. Market Position and Differentiation
7. Scope and Prioritization
8. Risks
9. User Journeys
10. Functional Requirements
11. Research Workflow and Lifecycle
12. Web Source Handling
13. PDF Handling
14. Screens, Experience and Accessibility
15. Non-Functional Requirements
16. Privacy, Safety and Security
17. Error Handling
18. Evaluation Plan
19. Acceptance Criteria
20. Dependencies, Constraints and Assumptions
21. Decisions and Open Questions
22. Milestones and Release Roadmap
23. Documentation and Change Control
24. Traceability Seed Matrix

---

## 1. Executive Summary

**DeepTrace AI** is a local-first, single-user AI research application for students, researchers, and professional analysts. Users investigate a question using online sources and text-based PDFs, inspect retrieved passages, identify uncertainty, and prepare a Markdown research report with traceable references.

The initial deliverable is a narrow end-to-end **web research slice**: question → bounded search → fetched source passages → cited answer → Markdown report. PDF/RAG support and structured conflict comparison are added in subsequent MVP milestones, not required before the first working demonstration.

**Trust promise:** DeepTrace validates that cited references exist and that quotations match their stored passages. It separately *assesses* whether passages semantically support claims; that assessment is fallible and must not be represented as proof. It cannot certify the truth, independence, or impartiality of external sources. Unsupported conclusions must be labeled or omitted.

**Local-first** means investigation data is primarily stored on the user's machine; it is **not fully offline**. Search queries, fetched website requests, and selected context may leave the device for configured providers after clear disclosure.

## 2. Glossary

| Term | Meaning |
|---|---|
| Investigation | Saved research question, plan, retrieval events, evidence, answers and reports |
| Source | Fetched web page or user-uploaded document |
| Passage | Stored source excerpt with stable ID and source/page/offset metadata |
| Claim | A distinct factual proposition in an answer or report |
| Citation | Reference from claim to one or more stored passages |
| Reference validity | Referenced passage exists, is accessible, and belongs to the investigation |
| Quote fidelity | Quoted text appears accurately in the referenced passage |
| Semantic grounding | Cited evidence actually supports the claim; subject to evaluation error |
| Stance | Evidence relation to a claim: supports, contradicts, neutral, or uncertain |
| Contested claim | Claim with materially conflicting evidence, subject to review |
| RAG | Retrieval-Augmented Generation: retrieve passages before synthesizing an answer |
| Golden set | Fixed, labeled evaluation scenarios with expected references and outcomes |
| Run budget | Limits on search calls, pages, model usage, time and steps |
| Thin slice | Smallest end-to-end usable research workflow |
| MVP | First cohesive release after the phased implementation milestones pass |

## 3. Problem Statement

Research material is fragmented across websites and PDFs. Manually comparing sources takes time; AI answers can cite nonexistent or irrelevant material; and reports often obscure what evidence actually justifies each conclusion. Researchers need a usable workflow that organizes sources and makes evidence, conflicts and uncertainty visible, without requiring a cloud account.

## 4. Vision, Goals and Success Measures

**Vision:** Make research easier to inspect, reproduce and challenge.

| ID | Objective | Proposed MVP measure |
|---|---|---|
| OBJ-1 | Traceable citations | 100% of displayed citation IDs resolve to stored passages; zero known fabricated quotes reach reports |
| OBJ-2 | Supported synthesis | ≥ 85% of sampled factual claims judged supported by cited evidence, with human review of disagreements |
| OBJ-3 | Honest uncertainty | ≥ 90% correct insufficient-evidence response on ten fixed unanswerable questions |
| OBJ-4 | Useful performance | Report measured median and p90 completion time on fixed fixtures; set an enforceable target after baseline profiling |
| OBJ-5 | Reproducibility | Saved search/query/model/prompt metadata and report versions |
| OBJ-6 | Local reliability | Persist completed steps; restart restores data without corruption |
| OBJ-7 | Usability | At least four of five novice testers complete a report without assistance |

No telemetry is collected by default. Evaluation results are local; any diagnostic export is explicitly initiated by the user. These goals do not imply that any scores have been achieved.

## 5. Target Users

| Persona | Priority | Primary job |
|---|---|---|
| Sara — university student | Primary | Investigate a topic and produce an understandable, cited report |
| Dr. Malik — researcher | Secondary | Explore papers/PDFs, inspect page references and disagreements |
| Ayesha — professional analyst | Secondary | Prepare quick, transparent evidence summaries |

The MVP is optimized for a guided student workflow but does not prevent professional or academic use. It is **not** a substitute for specialist or legal/medical/financial verification.

## 6. Market Position and Differentiation

DeepTrace's design emphasis is **passage-level traceability, explicit uncertainty, user-visible evidence, local session storage and bring-your-own provider credentials**. Competing research tools may offer overlapping capabilities. Specific feature comparisons with ChatGPT Deep Research, Perplexity, NotebookLM, Elicit and Consensus are **not included as verified facts** until independently checked at release time. Do not make unsupported superiority claims in marketing.

## 7. Scope and Prioritization

### 7.1 First working vertical slice (Milestone 1)

1. Enter a research question and configure a bounded run.
2. Generate a basic research plan and perform search through one configured provider.
3. Fetch and extract a limited set of permissible web pages.
4. Produce an answer with resolvable source/passage citations, visibly marking unsupported claims.
5. Download a Markdown report; preserve investigation data locally.

This is a **development checkpoint**, not the complete MVP release.

### 7.2 Feature priorities

| ID | Capability | Priority | Delivery |
|---|---|---|---|
| FR-01 | Local investigation sessions and history | Must | M0–M1 |
| FR-02 | Bounded research-plan generation | Must | M1 |
| FR-02b | Plan editing and approval mode | Should | M2–M3 |
| FR-03 | Web search, fetch, extract and provenance | Must | M1 |
| FR-04 | Text-based PDF upload and extraction | Must | M2 |
| FR-05 | Investigation-scoped PDF/web RAG | Must | M2 |
| FR-06 | Reference/quote checks, evidence-linked answers and uncertainty | Must | M1; semantics strengthened M3 |
| FR-07 | Versioned Markdown research reports | Must | M1 |
| FR-08 | Minimal dashboard, history and status | Must | M1; filtering/library Should M3 |
| FR-09 | Structured stance labels and conflict comparison | Should | M3; advanced V1 |
| FR-10 | Source metadata and credibility *signals* (not truth ratings) | Should | M3 |
| FR-11 | Run limits, cancellation and usage visibility | Must | M1 |
| FR-12 | APA/MLA/IEEE rendering | Could | V1 |
| FR-13 | PDF/DOCX export | Could | V1 |
| FR-14 | BibTeX and archive export | Could | V1 |
| FR-15 | Scanned-PDF OCR | Could | Future |
| FR-16 | Fully local LLM option | Could | Future |
| FR-17 | Multi-user login/collaboration | Won't | MVP |

**MVP exit** requires all Must requirements and associated release gates. Should features are stretch goals and cannot block the MVP unless specifically promoted by an approved change. Effort estimates are planning estimates, not delivery promises.

### 7.3 Explicit MVP non-goals

Multi-user authentication, collaboration, payments, mobile apps, voice research, JS browser automation, OCR of scanned PDFs, unrestricted autonomous agents, cloud hosting and guarantees of factual truth.

## 8. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Invented or misleading citations | High | Deterministic ID/quote checks plus measured semantic-grounding review |
| Inaccessible, blocked, paywalled or stale web pages | High | Clear per-source statuses; continue with other sources; no bypass |
| Provider costs, limits or outages | High | Budgets, caps, retries, save partial data, swappable adapters |
| Prompt injection from retrieved sources | High | Untrusted-content separation, no model-driven arbitrary tool access, adversarial tests |
| PDF page/reading-order errors | Medium | Page-preserving extraction, warning indicators and test fixtures |
| Scope expansion | High | Milestone gates, explicit Must/Should distinction |
| Misunderstanding local-first privacy | High | First-run and per-provider outbound-data disclosure |
| Misleading source-count confidence | High | Present evidence coverage and limitations, not a numerical truth guarantee |

## 9. User Journeys

**UJ-1 — Web investigation:** create a question → review plan (if approval mode enabled) → search and fetch → inspect source statuses → read cited answer → inspect a passage → download report.

**UJ-2 — PDF analysis (M2):** upload text-based PDF → validate and extract per page → index passages → ask questions → click file/page references; show clear OCR-unavailable message for scans.

**UJ-3 — Evidence review (M3, Should):** view per-claim support and contradiction excerpts → correct or exclude a stance → regenerate report with provenance of changes.

**UJ-4 — Resume:** reopen history after restart; completed steps and sources remain. Where resumable execution is implemented, continue only unfinished steps.

**UJ-5 — Report:** inspect report sections and citations → download immutable versioned Markdown file.

## 10. Functional Requirements

### FR-01 — Investigations (Must)

- **FR-01.1:** Create an investigation with title and a question of 10–1,000 characters.
- **FR-01.2:** Persist plans, states, sources, passages, answers and reports locally and restore on restart.
- **FR-01.3:** Rename, archive and delete investigations, with explicit confirmation for deletion.
- **FR-01.4:** Deletion removes associated database rows, files and vector entries under application ownership; report failures honestly and verify completion. Backups outside application control are disclosed separately.
- **FR-01.5:** Display the investigation's current lifecycle state.

### FR-02 — Planning (Must); FR-02b — Editing (Should)

- **FR-02.1:** Generate a validated bounded plan with 3–8 sub-questions and up to three queries each, or a shorter plan with a reason when the question is narrow.
- **FR-02.2:** Show source types and search/time/token budgets before running.
- **FR-02b.1:** Edit, add, remove and reorder sub-questions (Should).
- **FR-02b.2:** Optional human approval checkpoint, default enabled when implemented (Should); simpler M1 runs can use explicit Start confirmation.

### FR-03 — Web research (Must)

- **FR-03.1:** Use one explicitly configured search-provider adapter; handle provider failures.
- **FR-03.2:** Extract title, readable body, URL, retrieval time, and author/publication date when available.
- **FR-03.3:** Respect fetching restrictions and security requirements in §12 and §16.
- **FR-03.4:** Display `fetched`, `partial`, `blocked`, `paywalled`, `failed`, `duplicate` or `unsupported` accurately.
- **FR-03.5:** Preserve original URL, canonical URL where trustworthy, retrieval timestamp and passage offsets.

### FR-04 — PDF documents (Must, M2)

- **FR-04.1:** Accept valid text-based PDFs within configured file/page/count limits.
- **FR-04.2:** Extract and index by PDF page; preserve page reference and stable excerpt ID.
- **FR-04.3:** Detect likely scanned/image-only pages and explain that OCR is not available in MVP.
- **FR-04.4:** Display extraction-quality status (`good`, `degraded`, `unusable`) with a reason when possible.
- **FR-04.5:** Reject encrypted, corrupt, unsupported and oversized files safely.

### FR-05 — Retrieval (Must, M2)

- **FR-05.1:** Chunk retrieved text into configurable passages, initially about 200–500 tokens with overlap; never cross a PDF page boundary.
- **FR-05.2:** Support top-k semantic retrieval (default k = 8), with a later option for hybrid keyword ranking.
- **FR-05.3:** Keep source ID, page/URL locator, excerpt, offsets and ingestion version.
- **FR-05.4:** Scope retrieval to the current investigation; library-wide retrieval requires user opt-in.

### FR-06 — Evidence-backed answers (Must)

- **FR-06.1:** Factual claims in final answers and reports must cite one or more retrieved passage IDs, or be explicitly labeled `Unsupported`/`Not established`.
- **FR-06.2:** **Deterministic reference check:** verify cited passage exists, belongs to that investigation, was not removed and resolves to a stored source.
- **FR-06.3:** **Quote-fidelity check:** normalize only documented whitespace/Unicode differences and verify any presented quotation against passage text. Never invent exact quotes.
- **FR-06.4:** **Semantic-support assessment:** separately evaluate whether evidence entails each claim. Label as `Supported`, `Uncertain`, `Contested` or `Unsupported`; store the method/model and acknowledge that an automated judgment may be wrong. A syntactically valid citation alone never implies support.
- **FR-06.5:** Suppress fabricated references and label unsupported claims; when evidence is insufficient, state what additional evidence is needed. Do not quietly convert an uncertain judgment into a fact.
- **FR-06.6:** Citation click opens the actual source/passage with page or URL context and excerpt highlighting where supported.
- **FR-06.7:** Present evidence status, coverage, independence caveats, and conflicts rather than a simplistic `High/Moderate/Low` truth score. Do not infer independence merely from different domains; syndication and shared original sources may count as one.

### FR-07 — Reports (Must)

- **FR-07.1:** Markdown report sections: Title; Question; Summary; Findings; Supporting Evidence; Conflicting or Missing Evidence; Limitations; Methodology; References.
- **FR-07.2:** Validate IDs and quotes again at export; explicitly label claims with uncertain/unsupported semantics.
- **FR-07.3:** Include search queries, provider/model identifier, prompt version, retrieval dates, source counts and important omissions without exposing secrets.
- **FR-07.4:** Preview and download `.md`.
- **FR-07.5:** Store immutable report versions rather than silently overwrite.

### FR-08 — Dashboard (Must baseline; Should enhancements)

- **FR-08.1:** List investigations with title, status, last update and source count (Must).
- **FR-08.2:** Open, delete and where supported resume sessions (Must for completed-session reopen; recovery per FR-L) .
- **FR-08.3:** Cross-investigation document library (Should).
- **FR-08.4:** History filters by title/date/status (Should).

### FR-09 — Evidence comparison (Should, M3)

- **FR-09.1:** Label evidence stance `supports`, `contradicts`, `neutral` or `uncertain`, with provenance and the ability to contest an automated label.
- **FR-09.2:** Surface materially conflicting passages as `Contested`; include both sides and limitations.
- **FR-09.3:** Show side-by-side comparison when screen size allows and equivalent sequential reading on mobile.
- **FR-09.4:** Save user corrections distinctly from original model labels; reflect reviewed overrides in later reports.

### FR-10 — Source indicators (Should)

- **FR-10.1:** Display domain, publication date, author and source type if derivable; mark absent values unknown.
- **FR-10.2:** Any source classification is a heuristic, **not** a factual reliability or truth score.
- **FR-10.3:** Show a configurable age warning (suggested default three years), interpreted according to research context.

### FR-11 — Run budgets (Must)

- **FR-11.1:** Initial configurable defaults: at most 25 workflow steps, 20 search calls, 15 fetched pages, 400,000 total estimated tokens and 20 minutes; enforce safe hard maximums. These are ceilings, not targets.
- **FR-11.2:** Display tracked usage and mark estimates (tokens and monetary cost may be approximate).
- **FR-11.3:** Stop safely on any limit and retain partial evidence with `Budget reached` status, not a normal-completion claim.
- **FR-11.4:** Support user-initiated cancellation and prevent uncontrolled recursive retries.
- **FR-11.5:** Before paid external calls, clearly show provider selection and usage implications; show estimated cost only when trustworthy pricing/configuration is available.

## 11. Research Workflow and Lifecycle

### 11.1 Bounded pipeline

**Plan → Discover → Fetch → Extract → Retrieve/Rank → Draft → Validate References/Quotes → Assess Claim Support → Present → Report.** Each stage has typed input/output, error status, provenance and cost accounting. Not every stage requires an LLM call.

### 11.2 Investigation states

`Draft → Planning → Awaiting approval (optional) → Running → Completed`

From `Running`, the system can become `Paused`, `Interrupted`, `Failed`, `Cancelled` or `Budget reached`. Only `Completed` signifies successful normal completion. `Archived` and `Deleted` are user actions. State transitions must be validated, persisted and auditable.

- **FR-L1:** Persist stage result and state transactionally before starting the next stage.
- **FR-L2:** After restart, mark an in-progress run `Interrupted`; show an actionable Resume or Restart choice. Resumable stage execution is required by MVP hardening (M3–M4), not by the first M1 slice.
- **FR-L3:** Resume completed local steps without duplicating stored sources/passages. Because provider calls may already have incurred charges, never promise zero duplicate external billing after a crash; use checkpoints and idempotency keys where providers support them.
- **FR-L4:** Pause/Cancel retain existing evidence; no implicit deletion.
- **FR-L5:** All loops and retries honor hard budgets.
- **FR-P1:** Version structured prompts in source-controlled prompt files; keep raw retrieved content outside trusted instructions.
- **FR-P2:** Save model ID, prompt version, run configuration and retrieval time in report metadata.
- **FR-P3:** Validate structured model output against schemas, retry in a bounded fashion, then show recoverable error.

## 12. Web Source Handling

- **FR-W1:** Respect `robots.txt`, site terms and rate limits; use a clear application user agent. Do not circumvent paywalls or access controls.
- **FR-W2:** Initial limits per page: 15-second timeout, 5 MB response, five redirects; all limits configurable within safe ceilings.
- **FR-W3:** Accept HTML and plain text; web PDFs use the PDF pathway where permitted. Mark other types unsupported.
- **FR-W4:** Extract readable text while preserving useful headings and excerpt anchors. Store original extraction version.
- **FR-W5:** No JavaScript execution in MVP; label low-content/JS-dependent pages partial when appropriate.
- **FR-W6:** Mark known blocked/paywalled responses and preserve status; never attempt a bypass.
- **FR-W7:** Deduplicate canonical URLs and near-identical text (initial similarity threshold is a tunable heuristic, not universal truth).
- **FR-W8:** Publication date is optional; display `Unknown` when unavailable.
- **FR-W9:** User-configurable allowed/denied domains are a Should enhancement; security deny rules always apply.
- **FR-W10:** One failed source must not discard successfully fetched sources.

## 13. PDF Handling

- **FR-D1:** Text-based PDFs are supported; no scanned PDF OCR in MVP.
- **FR-D2:** Chunk by PDF page and preserve a source fingerprint, page index and offsets.
- **FR-D3:** Show physical PDF page index and printed page label when reliably available; distinguish the two.
- **FR-D4:** Mark potentially unreliable extraction from tables, columns or footnotes as `degraded`; never claim exact text extraction without evidence.
- **FR-D5:** Reject password-protected PDFs with a specific message.
- **FR-D6:** Reject corrupt files and roll back partial indexing.
- **FR-D7:** Apply SEC-15 resource limits.
- **FR-D8:** Identical uploads may reuse indexed content by hash, while preserving investigation-specific access control.
- **FR-D9:** Removing a document deletes its active passages and embeddings; historical reports show `Source removed` instead of pretending their old links still work.

## 14. Screens, Experience and Accessibility

| Screen | MVP responsibilities |
|---|---|
| Dashboard | New research; list and reopen investigations; status/history |
| Research workspace | Question, plan, source progress, cited answer, budget/status |
| Sources | Fetch status, metadata, excerpt preview and links |
| Evidence drawer | Source passage and page/URL locator |
| PDF library (M2) | Validate/upload/list/remove documents, quality status |
| Report viewer | Preview, version selector, Markdown download |
| Settings | Provider credentials/setup, budget, data disclosure |
| Evidence compare (Should, M3) | Supporting/contradicting passages and override history |

- **UX-01:** Premium dark theme by default. Detailed tokens, typography and spacing belong in `DESIGN.md`; optional light theme is V1.
- **UX-02:** Responsive, collapsible navigation and clear information hierarchy.
- **UX-03:** Show current run stage, source count and budget updates promptly; measure update latency under defined fixture load.
- **UX-04:** Source and evidence cards show traceable excerpt, provenance and status (plus stance when implemented).
- **UX-05:** Unsupported, uncertain and contested states require text/icon indicators, never color alone.
- **UX-06:** Clicking a citation shows the original saved passage context; external link opens clearly as an external destination.
- **UX-07:** Design empty, loading, paused, failed, budget-reached and partial-results states.
- **UX-08:** First-run wizard discloses external data flow and helps configure API credentials.
- **UX-09:** Confirm deletion and other destructive changes.
- **UX-10:** Responsive browser UI from 360 px viewport width; no document-level horizontal overflow in primary views.
- **UX-11:** Full keyboard access, visible focus, labeled controls and reduced-motion support.
- **NFR-A1:** Target WCAG 2.2 AA for core flows; audit automated and manual coverage.
- **NFR-A2:** At least 4.5:1 text contrast for normal text; 3:1 for large text and applicable interface component boundaries.
- **NFR-A3:** Programmatic labels, semantic headings and accessible modal/drawer focus management.
- **NFR-A4:** Never rely on color alone.
- **NFR-A5:** Honor `prefers-reduced-motion`.

## 15. Non-Functional Requirements

| ID | Requirement | Proposed verification |
|---|---|---|
| NFR-P1 | Dashboard remains responsive with 200 investigations | Benchmark on documented reference hardware; proposed target ≤ 1.5 s local p90 |
| NFR-P2 | Retrieval over 500 indexed PDF pages | Benchmark after index warm-up; proposed target ≤ 2 s p90 |
| NFR-P3 | Indexing a 100-page text PDF | Baseline hardware + fixture; proposed target ≤ 60 s |
| NFR-P4 | First progress update | Proposed ≤ 3 s on local reference machine |
| NFR-R1 | Completed local stage data remains recoverable after controlled crash | Kill/restart integration tests; no corruption in test cases |
| NFR-R2 | External transient failures use bounded backoff | Default at most three retries when safe; honor `Retry-After` |
| NFR-R3 | Interrupted investigation is surfaced and can be resumed/restarted | Recovery integration tests; note limits on exactly-once billing |
| NFR-M1 | Modular adapters for LLM, search, embeddings, persistence | Replace one adapter without rewriting domain logic |
| NFR-M2 | Core logic is tested | Target ≥ 80% core-module line coverage; exercise all reference-validator failure branches |
| NFR-M3 | Format, lint, typecheck, unit and integration tests | CI passes on PRs |
| NFR-C1 | Windows is primary development platform | Verify on Iqra's Windows machine; macOS/Linux support targets only after tested |
| NFR-C2 | Modern evergreen browsers | Chrome and Edge initially; Firefox/Safari after browser QA |
| NFR-S1 | Setup is clear and repeatable | Scripted fresh-machine test; aspirational ≤ 15 minutes, not release gate until dependencies fixed |
| NFR-X1 | Storage warning | Warn at configurable ~500 MB per investigation |
| NFR-X2 | Concurrent runs | One active research run in MVP |
| NFR-O1 | Diagnostics | Structured local logging with redaction, rotation and maximum size |
| NFR-D1 | Portable investigation export | Should, V1; include provenance metadata |

**Benchmark policy:** Before making numeric performance goals binding, record CPU, RAM, OS, Python/Node versions, corpus/fixture size, warm/cold cache, provider mock/live mode and measurement percentile. Do not fail releases on uncalibrated machine-independent timing targets.

## 16. Privacy, Safety and Security

### 16.1 Data boundaries

| Data | Local by default | May leave device |
|---|---|---|
| Investigation, report, source metadata | Yes | Only via user-triggered export or provider request context |
| Uploaded original PDF | Yes | No automatic upload of original; extracted excerpts may be sent to configured LLM |
| Embeddings | Locally stored | Only if user explicitly selects a hosted embedding provider |
| Search queries | Locally logged | Sent to configured search provider |
| Website retrieval | Source text saved locally | Outbound request sent to public source site |
| API secrets | Local secret storage | Sent to intended provider only for authentication |
| Telemetry | None by default | None without explicit opt-in |

- **SEC-01:** Bring-your-own credentials; never bundle working production keys.
- **SEC-02:** No default telemetry or external analytics.
- **SEC-03:** Disclose provider-specific outbound data before initial use and in Settings; consent is meaningful and revocable.
- **SEC-04:** User deletion removes active app-managed copies, index entries and reports; clearly disclose limits involving prior exports, OS backups and provider retention.
- **SEC-05:** Sensitive-document mode (Should) prevents transmitting its content to external models; if no local model can process it, disable those operations rather than silently transmitting data.
- **SEC-06:** Store API keys in OS keychain, protected local configuration or untracked `.env`; prefer keychain where practical.
- **SEC-07:** Never expose secrets in Git, analytics, database content, reports, tracebacks or logs.
- **SEC-08:** Mask secrets in UI; Settings must not echo them in API responses.
- **SEC-09:** Enable secret detection in development/CI and maintain a documented key-rotation procedure.

### 16.2 Untrusted content and model boundaries

- **SEC-10:** All web/PDF passages are untrusted input, separately delimited with provenance. Delimiting alone is not a complete defense.
- **SEC-11:** Trusted instructions explicitly prohibit following instructions embedded in retrieved material.
- **SEC-12:** The LLM cannot execute arbitrary code, read unrestricted local files or initiate arbitrary network calls. Only narrowly scoped application operations may fetch validated user/search-derived URLs.
- **SEC-13:** Validate structured outputs. Never blindly follow URLs or tool instructions generated by the model.
- **SEC-14:** Run an adversarial fixture suite of at least 20 prompt-injection cases; report failures and prevent known successful exfiltration/tool misuse before release. A perfect test-set result is not a universal security guarantee.

### 16.3 Upload, fetch and local-server security

- **SEC-15:** Defaults: at most 25 MB per PDF, 300 pages per PDF, ten PDFs per investigation; also enforce extraction time, decompression and memory ceilings.
- **SEC-16:** Check header signature, parser validity and allowed MIME/extension; never trust names alone.
- **SEC-17:** Store uploads under generated IDs in a controlled data directory; block path traversal, symlink traversal and unsafe cleanup targets.
- **SEC-18:** Escape untrusted text; Markdown renderer disables raw HTML and sanitizes links; enforce safe downloads and content types.
- **SEC-19:** Local backend binds `127.0.0.1` by default, restricts CORS origins, validates Host/Origin on sensitive endpoints and uses CSRF-resistant request patterns. Treat other local processes/browser pages as possible adversaries; no unauthenticated exposure on LAN by default.
- **SEC-20:** Pin dependencies and scan known vulnerabilities; review updates rather than silently applying breaking upgrades.
- **SEC-21:** SSRF protection blocks loopback/private/link-local/metadata addresses, dangerous schemes and credentials in URLs; revalidate DNS-resolved addresses at connection time and on *every redirect* to mitigate DNS rebinding and redirect bypass. Apply egress/proxy rules where feasible.
- **SEC-22:** Provider timeouts, rate limits and budgets guard denial-of-service and cost abuse.
- **SEC-23:** Deletion and retention policies are tested against DB records, disk files and vector entries, including partial-failure recovery.

All reports include: **“AI-generated research aid. Verify important findings using original sources.”**

## 17. Error Handling

| ID | Situation | Required result |
|---|---|---|
| ERR-01 | Search service 429/5xx | Bounded backoff, preserve run, actionable retry; respect rate limit |
| ERR-02 | LLM timeout/outage | Preserve checkpoint; retry if safe; explain status |
| ERR-03 | Invalid API key | Stop calls; open Settings guidance; never retry authentication endlessly |
| ERR-04 | Broken DNS or URL | Mark source failed; continue other sources |
| ERR-05 | Blocked/paywalled source | Show status; no bypass or fabricated passage |
| ERR-06 | Conflicting passages | Surface dispute and attribution; do not silently choose a winner |
| ERR-07 | Insufficient evidence | Explicitly mark limits, do not hallucinate a source |
| ERR-08 | Scanned PDF | Explain OCR unavailable |
| ERR-09 | Corrupt/encrypted/oversized PDF | Reject clearly and clean up temporary content |
| ERR-10 | Malformed model output | Validate schema, bounded retry, recoverable failure |
| ERR-11 | Invalid citation | Suppress citation; mark claim unsupported pending revision |
| ERR-12 | Shutdown/crash mid-run | Recover completed steps; mark Interrupted |
| ERR-13 | Budget reached | Preserve partial output; status Budget reached |
| ERR-14 | Disk full/DB lock | Fail safely with no partial uncommitted writes |
| ERR-15 | Offline | Browse saved research; explain blocked network tasks |
| ERR-16 | Non-English materials | Process cautiously where model supports them; label possible quality limitations |
| ERR-17 | Long input/context | Bound input; notify if truncated or omitted |

Every error should tell the user what failed, what was saved, and how to proceed.

## 18. Evaluation Plan

Detailed fixture construction and scoring instructions belong in `EVALUATION.md`.

### 18.1 Fixed evaluation corpus

| ID | Fixture |
|---|---|
| EV-01 | 20 answerable questions over ≥ 5 fixed PDFs with gold passages/pages |
| EV-02 | 10 unanswerable questions whose evidence is absent |
| EV-03 | Five conflicting-evidence scenarios (M3 Should gate only) |
| EV-04 | At least 20 hostile HTML/PDF prompt-injection fixtures |
| EV-05 | Five mocked search/fetch scenarios, including failures and duplicate sources |

### 18.2 Distinct metrics

| Metric | Definition | Proposed gate |
|---|---|---|
| Reference validity | Displayed citations whose passage ID resolves correctly | 100% (deterministic output gate) |
| Quote fidelity | Quotes present faithfully in the referenced passage | 100% for verbatim quotes |
| Semantic groundedness | Sampled claims genuinely supported by their cited passage | ≥ 85%; human-reviewed sample |
| Citation page accuracy | Cited PDF page equals gold supporting page | ≥ 90% |
| Retrieval recall | Gold supporting passages surfaced among top-k | ≥ 70% |
| Insufficient-evidence accuracy | Unanswerable prompts honestly declined/flagged | ≥ 90% |
| Conflict detection | Contested fixtures correctly flagged | ≥ 80%; M3 Should feature only |
| Injection resistance | No defined unsafe action or exfiltration in fixed attack set | Zero known successes in release suite, without claiming universal immunity |

**Crucial:** `Reference validity` and `Quote fidelity` are programmatic checks; `Semantic groundedness` requires human judgment or calibrated fallible evaluation. Report them separately. A fabricated citation caught and suppressed is a validator success; do not count it as a visible hallucinated citation.

- **EV-10:** Run deterministic tests on every applicable code change; run model-backed evaluation on prompt/model/retrieval changes and before releases.
- **EV-11:** Version evaluation results with model, prompt, fixture version, date, and configuration.
- **EV-12:** Block MVP release if Must-feature gates fail; compare regressions against an approved baseline. Do not gate on incomplete Should features.
- **EV-13:** Calibrate LLM-judge outputs against a human-labeled subset (target ≥ 30 labeled judgments where available); record disagreement and sample size.
- **EV-14:** Deterministic validator, chunker, state and budget logic use conventional automated tests, not LLM judgment alone.

## 19. Acceptance Criteria

| ID | Pass condition | Applies |
|---|---|---|
| AC-01 | Saved investigation reopens with all completed-step data after restart | FR-01 |
| AC-02 | Plan schema valid across ten varied test questions; narrow-plan exception explained | FR-02 |
| AC-03 | Mocked thin-slice research creates fetched sources, answer and cited Markdown report without invented passage IDs | FR-03/06/07 |
| AC-04 | Text PDF indexes per page and retrieves passages using stable IDs; timing benchmark documented | FR-04/05 |
| AC-05 | ≥ 90% page accuracy on fixed 20-question labeled set | EV-01 |
| AC-06 | All exported citation IDs and verbatim excerpts pass deterministic validation; sampled groundedness reported separately | FR-06/07 |
| AC-07 | At least nine of ten unanswerable tests clearly flag insufficient evidence | EV-02 |
| AC-08 | At least four of five conflict fixtures labeled contested if FR-09 is promoted or shipped | FR-09 (Should) |
| AC-09 | Mock 429/5xx triggers bounded retries, preserved state and clear recovery | ERR-01 |
| AC-10 | Crash/restart test restores checkpoint and avoids duplicate local records; external charging caveat documented | FR-L |
| AC-11 | Reduced test budget stops work exactly at allowed cap and retains partial sources | FR-11 |
| AC-12 | Scanned-only PDF produces OCR-not-supported warning | FR-04 |
| AC-13 | Disguised executable, oversized, password-protected and corrupt PDF rejected safely | SEC-15–17 |
| AC-14 | At least 20 prompt-injection fixtures cause no defined unsafe tool action or exfiltration; residual risk documented | SEC-10–14 |
| AC-15 | Seeded secrets do not appear in reports, DB, browser responses or logs; scanning detects a test secret | SEC-06–09 |
| AC-16 | Markdown report contains FR-07 sections, metadata, and accurate reference statuses | FR-07 |
| AC-17 | No critical/serious automated accessibility failures on core pages; manual keyboard test passes five flows | NFR-A |
| AC-18 | A new Windows setup succeeds from the written procedure and sample fixtures; record time/commands | NFR-S1 |
| AC-19 | Four of five novice users generate a report without instruction during usability evaluation | OBJ-7 |
| AC-20 | Core tested modules meet ≥ 80% line coverage and reference-validator error branches are exercised | NFR-M2 |
| AC-21 | Redirects and DNS changes cannot access prohibited private/loopback destinations in SSRF fixtures | SEC-21 |
| AC-22 | Delete action removes app-owned DB/file/vector artifacts in tests; external backup limitations disclosed | SEC-04/23 |

**Definition of Done:** implementation, runnable demonstration, tests, documentation/trace links and successful relevant quality gates. Partial phase success must be reported as partial, never as a complete MVP.

## 20. Dependencies, Constraints and Assumptions

- Solo developer; Windows-first local development; no dedicated GPU assumed.
- Initial browser experience is React + TypeScript + Vite with Tailwind CSS; backend Python + FastAPI; LangGraph coordinates later multi-step workflows. These are **approved planning defaults**, subject to an architecture decision record rather than an unreviewed automatic switch.
- Text-based PDF extraction: PyMuPDF is the proposed initial choice.
- Local relational storage: SQLite is the proposed initial choice; embeddings use a local adapter (e.g., Chroma) subject to benchmark and security review.
- LLM and search vendors are not yet selected; provider credentials, supported countries, current pricing, terms and limits must be validated in `INTEGRATIONS.md` before spending money or sending data.
- Embedding default is local where practical; a hosted option must have explicit data-transfer disclosure.
- English is the primary MVP language; PDFs are mostly assumed to contain extractable text.
- Internet access is required for live web research and hosted LLM calls; browsing saved investigations works offline.
- Never store API keys or uploaded user PDFs in the Git repository.

## 21. Decisions and Open Questions

| ID | Decision / question | Status | Resolve in |
|---|---|---|---|
| D-01 | Local-first, single-user, no login for MVP | Confirmed | PRD |
| D-02 | Premium dark UI; responsive web app | Confirmed | DESIGN |
| D-03 | Focused phased MVP; evidence traceability first | Confirmed | PRD |
| D-04 | React/TypeScript/Vite/Tailwind + Python/FastAPI | Proposed baseline | ARCHITECTURE |
| D-05 | LangGraph for bounded orchestrated workflows | Proposed baseline | ARCHITECTURE |
| D-06 | SQLite and locally stored vectors | Proposed baseline | DATABASE |
| OQ-01 | Search provider, quota and terms | Open | INTEGRATIONS |
| OQ-02 | LLM provider/model and cost controls | Open | INTEGRATIONS |
| OQ-03 | Local embedding model and vector-store benchmark | Open | ARCHITECTURE/DATABASE |
| OQ-04 | Reference machine and performance baselines | Open | TESTING |
| OQ-05 | License and packaging/distribution choice | Open | SETUP |
| OQ-06 | Human reviewers for groundedness labels | Open | EVALUATION |

## 22. Milestones and Release Roadmap

| Milestone | Deliverable | Exit checkpoint |
|---|---|---|
| M0 — Foundation | Repo layout, frontend/backend scaffold, local DB, env example, test/CI baseline, threat-model sketch | Starts locally; no secrets committed; AC-15 basic checks |
| M1 — Vertical slice | Basic sessions, plan, one search provider, bounded fetch, cited answer, Markdown report, simple dashboard | AC-01/02/03/06/09/11; demo on mock fixtures |
| M2 — PDFs and RAG | Upload, extraction, per-page chunks, local retrieval and page citations | AC-04/05/12/13 |
| M3 — Evidence and resilience | Semantic-support assessment, optional conflict comparison, resume/cancel, metadata/UX enhancements | AC-07/10; AC-08 only if Should feature included |
| M4 — MVP hardening | Security/adversarial suites, benchmark calibration, accessibility, usability and docs | All Must-feature AC gates; AC-14/17/18/19/20/21/22 |
| V1 | Citation-style presets, extra exports, library UX, optional light theme | Separate feature-specific QA |
| Future | OCR, local LLM, multi-user/collaboration, JS-rendered fetch, cloud deployment | Separate approved PRD changes |

Claude/other coding agents should implement **one accepted milestone at a time**, report exact file changes and tests, and stop when a phase cannot be completed within the current session. Never fabricate test results or mark unimplemented functionality complete.

## 23. Documentation and Change Control

| Order | Document | Purpose |
|---|---|---|
| 1 | `PRD.md` | Canonical product requirements |
| 2 | `docs/DESIGN.md` | Visual and interaction contracts |
| 3 | `docs/INTEGRATIONS.md` | Model/search/embedding vendor adapters and external data flows |
| 4 | `docs/ARCHITECTURE.md` | Module boundaries, workflows, key decisions |
| 5 | `docs/DATABASE.md` | Schema, vector persistence, deletion and migration |
| 6 | `docs/API.md` | Request/response contracts and errors |
| 7 | `docs/SECURITY.md` | Threat model, server/fetch/upload safeguards |
| 8 | `docs/PROMPTS.md` | Prompt versions, trust boundaries and output schemas |
| 9 | `docs/EVALUATION.md` | Golden datasets, metrics and release thresholds |
| 10 | `docs/TESTING.md` | Test pyramid, fixtures, CI and benchmark protocol |
| 11 | `docs/SETUP.md` | Windows-first reproducible setup |
| 12 | `docs/IMPLEMENTATION.md` | Phase checklist and progress tracker |
| 13 | `docs/TRACEABILITY.md` | Requirement-to-code/test mapping |
| 14 | `AGENTS.md` | Agent instructions, scope control and reporting |

**Change rule:** when a requirement changes, update this PRD's version/change log, affected documents, tests and traceability links together. Avoid duplicating the same normative requirement in conflicting wording downstream. Mark every implementation claim as `planned`, `in progress`, `verified`, or `blocked` and cite actual test evidence.

## 24. Traceability Seed Matrix

| Requirement | Design/implementation doc | Verification |
|---|---|---|
| FR-01 | DATABASE, API | AC-01, AC-22 |
| FR-02 | PROMPTS, API | AC-02 |
| FR-03 | INTEGRATIONS, SECURITY | AC-03, AC-09, AC-21 |
| FR-04 | ARCHITECTURE, SECURITY | AC-04, AC-12, AC-13 |
| FR-05 | DATABASE, ARCHITECTURE | AC-04, AC-05 |
| FR-06 | API, EVALUATION | AC-06, AC-07 |
| FR-07 | DESIGN, API | AC-16 |
| FR-08 | DESIGN, API | AC-01, UX review |
| FR-09 | PROMPTS, EVALUATION | AC-08 (Should only) |
| FR-11 | ARCHITECTURE | AC-11 |
| FR-L | ARCHITECTURE, DATABASE | AC-10 |
| SEC-06–09 | SECURITY | AC-15 |
| SEC-10–14 | SECURITY, PROMPTS | AC-14 |
| SEC-15–23 | SECURITY | AC-13, AC-21, AC-22 |
| NFR-A | DESIGN, TESTING | AC-17 |
| NFR-S1 | SETUP | AC-18 |
| NFR-M2 | TESTING | AC-20 |

---

**Document end — DeepTrace AI PRD v1.1.0.** Next document after approval: `docs/DESIGN.md`.
