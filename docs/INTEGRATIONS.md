# DeepTrace AI — Integration Decisions and Contracts

**Status:** Approved integration specification; implementation and provider onboarding not yet started
**Version:** 1.0.0
**Decision date:** 2026-10-23
**Scope:** Windows-first, single-user, local-first web application
**Sources of requirements:** `PRD.md` v1.1.0 and `docs/DESIGN.md`

> **Cost commitment:** Free-only development and MVP operation. No automatic paid tier, billing upgrade, paid fallback, or usage-based purchase. A free service may change its terms or become unavailable; in that event, stop the relevant live operation safely rather than incur a charge.

## 1. Decision register

| ID | Area | Approved baseline | Phase | Notes |
|---|---|---|---|---|
| INT-01 | Language model | Mock adapter for tests; opt-in Google Gemini API **free-tier eligible** text model for live use | M1 | Pin an actually available model ID after account/region verification; do not hard-code an unverified model name. |
| INT-02 | Web search | Mock adapter for tests; Tavily free-plan search adapter for live use | M1 | Stay under verified free credits; no pay-as-you-go fallback. |
| INT-03 | Web retrieval | HTTPX with application-owned URL/DNS/redirect safety checks | M1 | Respect robots, site restrictions and request budgets. |
| INT-04 | Web text parsing | Trafilatura, with provenance-preserving extraction wrapper | M1 | Treat extracted web content as untrusted. |
| INT-05 | Embeddings | Local FastEmbed using `BAAI/bge-small-en-v1.5` | M2 | English-centric; pin model revision and audit model/runtime licenses. |
| INT-06 | Vector search | SQLite-stored vectors + NumPy exact cosine similarity | M2 | Start with small, investigation-scoped corpora; benchmark before scaling. |
| INT-07 | PDF parsing | `pypdf` plus `pypdfium2` | M2 | Permissive baseline; text PDFs only; no OCR in MVP. |
| INT-08 | Alternative local LLM | Optional Ollama adapter **after** device feasibility checks | Later | No GPU or adequate local-model performance assumed. |
| INT-09 | Paid Anthropic models / commercial PDF license | Not in free-only MVP | Deferred | Require fresh explicit approval before adding. |
| INT-10 | Project source license | Apache License 2.0 | Setup | Add LICENSE and notices only in an authorized documentation/setup task. |

These choices **supersede the earlier provisional integration examples** in PRD §20 (PyMuPDF, Chroma) and resolve PRD OQ-01 and OQ-02 at the provider-selection level; OQ-03 remains subject to performance validation. They do **not** silently rewrite the PRD or design document. Record an architecture decision and reconcile the wording when those documents are next revised.

## 2. Provider modes and activation

1. **Mock mode:** Deterministic fixture-driven search and language-model adapters; usable for CI, UI previews, offline demonstrations and failure testing. Mock output must be visibly labeled as a simulation, not live research.
2. **Live free mode:** Requires the user to supply valid Gemini and Tavily credentials, review the outbound-data disclosure, explicitly consent, and pass a zero-cost eligibility/configuration check. Credentials are never included in builds or examples.
3. **Offline inspection:** Saved investigations, cached sources, citations and reports remain viewable without providers. New live web research and hosted model generation are disabled offline.
4. **No fallback to paid services:** Quota exhaustion, model unavailability, authentication failure, or ambiguous billing status must halt the affected step and retain partial evidence. Do not silently substitute another vendor or model.

The initial setup wizard and Settings screen must show provider name, role, data sent, free-limit status, credential state and consent state. Revoke consent must prevent new outbound transmissions. A stored API key does not itself constitute consent.

## 3. Integration interface contracts

Define provider interfaces independently of SDKs and UI. The following are **logical contracts**, not a frozen implementation syntax:

### 3.1 `SearchProvider`

- **Input:** validated search query, bounded result count, safe timeout, cancellation token and investigation/run ID.
- **Output:** source URL, title/snippet when supplied, rank, provider name, retrieval metadata and provider response classification; never fabricate publication dates or authors.
- **Failure categories:** unavailable, authentication rejected, rate-limited, free quota exhausted, malformed response, timed out, cancelled.
- **Controls:** Tavily call/credit budget, run-level request count, no retry storms, bounded exponential backoff only where safe.
- Search results are *leads*, not verified evidence; answer citations point to stored fetched passages rather than search snippets alone.

### 3.2 `LLMProvider`

- **Input:** task type (`plan`, `synthesize`, later `assess`), prompt version, validated question, deliberately selected source passage IDs/text, structured response schema, token ceiling, timeout and cancellation token.
- **Output:** structured data, declared model ID, provider ID, token usage if reported, response status and safe error category.
- **Restrictions:** no arbitrary tool execution, file access, network fetches, invented source IDs or unchecked URLs from model output.
- Validate schemas, source references, quote fidelity and investigation scope deterministically after generation; suppress invalid citations and label unsupported claims. Semantic support is a **separate**, fallible evaluation introduced in M3, not an automatic consequence of valid citation IDs.
- Log model and prompt versions without prompts containing sensitive passage text or keys.

### 3.3 `EmbeddingProvider`

- **Input:** normalized text passages and stable passage identifiers, batched within memory/time limits.
- **Output:** fixed-dimension vectors with model identifier, revision, preprocessing version and vector dimension.
- **Baseline:** local-only FastEmbed `BAAI/bge-small-en-v1.5`; expected 384-dimensional output must be asserted against the actual pinned artifact.
- Never send uploaded PDFs or passages to hosted embedding providers. Changing embedding models requires reindexing or a versioned separate index; never mix incompatible dimensions.

### 3.4 `DocumentExtractor` and `WebExtractor`

- Return extracted text **with** source fingerprint, source type, physical PDF page index or URL, extraction version, position/offset where reliable, and extraction-quality status.
- Preserve PDF page boundaries during chunking. Do not claim printed page labels unless reliably available; physical page numbers must remain distinguishable.
- Unknown author, publication date or offset must be represented as unknown, never guessed.
- Handle empty, malformed, blocked, password-protected, scanned and partially extracted sources with explicit statuses.

## 4. Free-tier LLM: Gemini

- Verify **at setup time**, against official Google documentation and the account itself, that the chosen model is available in Pakistan, has an applicable free API tier, and exposes sufficient quotas. Model names, prices and rate limits are volatile; keep the model ID configurable and version-pinned in reproducible run metadata.
- Do not attach billing or enable automatic chargeable quota for the MVP. Treat uncertain tier status as disabled.
- A call quota is not a guarantee of zero cost if an account is configured for paid usage. Preflight account configuration and enforce application-side allowlists for model IDs and operation types; never promise the app can override provider-side billing.
- User-facing notice: **Gemini free-tier content may be used by Google to improve products under applicable terms.** Only send synthetic, public or deliberately approved non-sensitive question/context data. Do not automatically transmit original PDFs. Clearly preview which extracted snippets will leave the device and require explicit authorization for document-derived context.
- If content is marked sensitive, block hosted LLM passage transmission. Without an approved local model, explain that AI synthesis is unavailable and allow local inspection/export of evidence instead.
- Grounding via Gemini's own search tools is **not** assumed free, enabled or used: Tavily is the explicit search channel, and all retrieved citations resolve to our local evidence records.

## 5. Free-tier search: Tavily

- The published free plan currently advertises **1,000 credits/month**, but credit consumption varies by endpoint and option; verify the actual account balance, plan and current policy before enabling live mode.
- Default to the least-cost search capability that meets evidence discovery requirements. Do not enable premium/advanced options implicitly.
- Add conservative, configurable **application** ceilings below provider quotas. The PRD's limits (20 search calls, 15 fetched pages and 20 minutes per run) are hard upper bounds, **not goals**. Set a lower practical default after observing real credit use.
- Never cross investigation/run caps or retry a rate-limit/quota response indefinitely. Retain partial results and visibly report `Budget reached` or `Provider quota exhausted`.
- Search queries leave the computer; disclose this before first live search. Search results are untrusted data, not executable instructions.

## 6. Web fetch and extraction security

- Use `httpx` for controlled GET requests and `trafilatura` to derive readable text. Do not permit arbitrary schemes, URL credentials, local file reads, JavaScript execution or bypasses of access controls.
- Enforce PRD §12 defaults: **15 s** per-page timeout, **5 MB** response ceiling and **five redirects** maximum, with safe caps on any user configuration.
- Respect robots.txt, site terms, rate limits, paywalls and a descriptive user agent. Mark blocked, paywalled, partial, failed and unsupported status accurately.
- **SEC-21 is mandatory:** parse/normalize URLs; resolve all A/AAAA addresses; deny loopback, private, link-local, multicast, reserved and metadata endpoints; revalidate at every redirect and actual connection; prohibit DNS rebinding/TOCTOU by controlling the connection destination (a check followed by an unrelated default re-resolution is insufficient). Test proxies and redirects rather than assuming the HTTP library is SSRF-safe by default.
- Restrict accepted response types; safely decompress within limits; avoid requests to known internal hosts and network interfaces. Handle redirect URL credentials, IPv6 literals, encoded addresses and hostnames resolving to mixed public/private addresses.
- Preserve original URL, trustworthy canonical URL, retrieval timestamp, text extraction version and stored passage IDs. Sanitized rendered markdown must not execute remote content.

## 7. PDF stack and distribution licensing

### 7.1 Selection and scope

- **Use `pypdf`** for PDF structural/text processing and metadata where supported.
- **Use `pypdfium2`** for PDFium-backed page processing/rendering and supplementary text extraction where its results improve page fidelity.
- Accept **text-based** PDFs only for MVP; identify likely image-only/scanned pages and explain OCR is not available. Do not silently produce fabricated text from empty pages.
- Enforce PRD SEC-15 defaults: **25 MB per PDF**, **300 pages per PDF**, **ten PDFs per investigation**, plus bounded CPU, memory and processing time.
- Validate extension, signature, content/parser behavior and controlled upload paths. Handle password protection, corruption, extraction degradation, tables/columns, rollback and deletion of derived embeddings.
- Store stable file fingerprint, per-page passage IDs and **physical page number**. Store a printed page label only when reliably extracted. Citation clicks must resolve to the original stored passage and page.

### 7.2 License rationale

- `pypdf`: **BSD-3-Clause**.
- `pypdfium2`: its Python wrapper is dual-licensed **Apache-2.0 OR BSD-3-Clause**. Bundled PDFium binaries and transitive components carry additional notices/licenses that must be reviewed, recorded and redistributed as required.
- `PyMuPDF`: **AGPL or commercial** licensing; intentionally *not* selected for the first open-distribution baseline. AGPL-compatible distribution is possible under its conditions, but adds compliance analysis we can avoid at this stage. Do not introduce PyMuPDF transitively or copy its code without an explicit license review.
- DeepTrace AI application source: **Apache-2.0**, as approved by the project owner. Before publication, create the license text, preserve third-party attribution/NOTICE material where required, validate font/model/data licenses separately and inventory runtime/binary dependencies. An Apache-2.0 project license does **not** automatically relicense third-party code, models, datasets or user content.
- Legal review is a release gate if licensing facts remain uncertain. This section is engineering guidance, not legal advice.

### 7.3 Acceptance benchmark

Test representative Windows PDFs: ordinary text, multi-column, tables/footnotes, unusual Unicode, 300-page boundary, scanned, corrupt, encrypted and huge/decompression-heavy. Compare page-level accuracy, extraction time and memory between pypdf/pypdfium2; do not claim perfect layout fidelity. If the baseline fails, propose a new licensed alternative for approval rather than quietly switching.

## 8. Local semantic retrieval

- Use FastEmbed with an explicitly pinned `BAAI/bge-small-en-v1.5` model revision. Download model artifacts from a verified source; cache locally; record checksum/revision and audit model weights/license and all runtime dependencies separately.
- Use SQLite to store investigation, source, passage and vector metadata, with compact serialized vectors and their dimensions. Use NumPy for normalized exact similarity on **investigation-scoped** candidates; protect against cross-investigation leakage and malformed/non-finite vectors.
- Initial chunk target: **200–500 tokens with overlap**, **never across PDF pages**; top-k retrieval defaults to **8** (PRD FR-05). Persist chunker/normalizer/index versions.
- Benchmark latency, RAM, indexing time, corpus growth, first-run model download and cold/warm cache on the actual Windows reference machine. Consider a dedicated vector index only after evidence that exact search no longer meets the measured workload.
- English is the initial retrieval language. Warn about uncertain behavior with Urdu/other languages rather than promising multilingual correctness.

## 9. Secret management, outbound-data policy and retention

- Bring-your-own provider keys only. Prefer OS-protected credential storage; as a development fallback, use untracked protected `.env`. Never commit actual secrets, log them, put them in exports, return them via Settings APIs, or expose them in frontend bundles.
- UI states: `Not configured`, `Saved`, `Invalid`, `Quota reached`, `Unavailable`, and `Consent revoked`. Saved values must remain masked; replacement and removal must work without displaying the stored secret.
- Keep investigations, PDFs, extracted passages, embeddings and reports locally by default. Outbound flows are limited to approved Tavily search queries, approved Gemini selected context, and public-site HTTP fetches. No telemetry by default.
- Provide provider-specific disclosure before initial use and in Settings. Track consent version and purpose. Revocation prevents new requests, but cannot retract provider-side transmissions already made; explain retention limits honestly.
- Deleting a PDF removes app-managed original, derived passages and embeddings; restore only explicitly permitted backups. Existing immutable report versions must indicate removed sources rather than present broken citations as active evidence.
- Treat web and PDF text as untrusted. Include adversarial prompt-injection fixtures, enforce tool/data separation and never let a model initiate arbitrary fetches or execute code.

## 10. Configuration and operational limits

The following are **example names** for the eventual implementation; no environment file or credentials are being created by this specification:

| Setting | Proposed meaning | Default |
|---|---|---|
| `DEEPTRACE_MODE` | `mock`, `live_free`, or `offline` | `mock` |
| `DEEPTRACE_LLM_PROVIDER` | Allowed LLM adapter | `mock` |
| `DEEPTRACE_LLM_MODEL` | Explicit verified eligible Gemini model ID | unset |
| `GEMINI_API_KEY` | Local-only, protected BYO Gemini key | unset |
| `DEEPTRACE_SEARCH_PROVIDER` | Allowed search adapter | `mock` |
| `TAVILY_API_KEY` | Local-only, protected BYO Tavily key | unset |
| `DEEPTRACE_EMBEDDING_MODEL` | Pinned local embedding model | `BAAI/bge-small-en-v1.5` |
| `DEEPTRACE_ALLOW_PAID_APIS` | Must remain false for MVP; defensive guard | `false` |

Do not use a simple `ALLOW_PAID_APIS=false` flag as the **sole** spending guarantee. Account/billing state, provider quotas and API entitlements still require verification. Never accept an arbitrary provider base URL or route secrets to unapproved endpoints.

PRD FR-11 ceilings still apply to every run: 25 workflow steps, 20 searches, 15 fetched pages, 400,000 **estimated** tokens and 20 minutes. Enforce hard maxima, cancellation and safe partial-result persistence. Provider-specific lower caps must be adjustable and tracked independently. Token and price estimates are not authoritative billing records.

## 11. Test and release gates

### Automated/offline gates — no API keys required

- All adapters conform to the same test doubles and typed failure/result categories.
- Deterministic mocked end-to-end journey: create investigation → plan → mock search → safe fetch fixture → extract passage → generate structured answer → verify citation → export versioned Markdown report.
- Citation IDs must resolve to active, same-investigation stored passages; verbatim quotes must pass documented Unicode/whitespace-normalized match. Reject wrong-investigation IDs and invented quotes.
- Mock quota-exceeded, timeout, rate-limit, invalid key, provider outage, cancellation, user consent revoked and malformed model response; no unbounded retries or false `Complete` state.
- Test SSRF with private/loopback/metadata IPv4 and IPv6, URL encoding tricks, redirect chains, mixed DNS answers and DNS rebinding at connect time. No live network needed for fixtures.
- Test PDF page continuity, extraction errors, file/page limits, cleanup/rollback, path traversal, symlink handling and per-investigation retrieval isolation.
- Test prompt-injection fixtures (PRD SEC-14: at least 20) and injection attempts through source titles, body text, citation fields and uploaded filenames.
- Test Windows paths, Unicode, low-memory conditions, local binding/CORS/Host/Origin restrictions, secret redaction and network-disabled UI.
- Run dependency/license scanning; capture exact runtime/model/PDFium license and NOTICE inventory.

### Opt-in live smoke gates — only after setup approval

1. Validate Gemini free-tier model/region/key and privacy disclosure using harmless synthetic material. Record rate limits and model ID **without** storing a real key in reports.
2. Validate Tavily free-plan entitlement and credit accounting using a minimal public query.
3. Fetch one robots-permitted public site, store traceable passage metadata and show partial/blocked states accurately.
4. Verify quota errors stop without spending and an interrupted run retains valid partial evidence.
5. Record environment, versions, test fixtures and measured results. Live tests are never mandatory in CI.

### Release criteria

- Zero intentional paid API calls and no automatic chargeable fallback.
- Source and quote validation gates meet PRD AC-06; semantic support is not falsely declared just because references are valid.
- No known successful SSRF bypass or prompt-injection exfiltration in the release fixture set; disclose remaining risks.
- PDF extraction limits and deletion/retention semantics pass; license/NOTICE inventory is complete.
- External data disclosure and revocation work; no secrets occur in logs, reports or Git.
- Demonstration clearly distinguishes mock research from verified live research.

## 12. Open validation items and future changes

| Item | Required evidence | Owner/checkpoint |
|---|---|---|
| Exact Gemini free model and regional availability | Official current model/rate-limit docs plus actual account smoke test | M1 setup |
| Gemini data-use and provider retention terms | Current terms and user-facing privacy copy | M1 setup |
| Tavily account credits and options | Current dashboard/terms and lightweight smoke test | M1 setup |
| BGE weight and binary license inventory | Authoritative model card, pinned revision and dependencies | M2 |
| PDFium native binary third-party notices | Actual packaged artifact notices and dependency inventory | M2 packaging |
| Windows local retrieval performance | Reproducible benchmark with documented hardware and corpus | M2 |
| Automated claim semantic groundedness | Human-reviewed evaluation and calibrated method | M3 |
| Optional Ollama hardware feasibility | CPU/RAM/latency/quality test and privacy decision | Later |

**Change control:** Switching providers, enabling a paid plan, uploading raw PDFs to an external model, introducing AGPL/copyleft dependencies, changing project license, or replacing the local storage strategy requires a reviewed decision and the owner's explicit approval. Update this specification together with the relevant PRD/design/architecture decision references.

## 13. Authoritative reference links (check again at implementation)

- Google Gemini API pricing: https://ai.google.dev/gemini-api/docs/pricing
- Google Gemini API terms: https://ai.google.dev/gemini-api/terms
- Google Gemini API rate limits: https://ai.google.dev/gemini-api/docs/rate-limits
- Tavily plans/docs: https://docs.tavily.com/
- pypdf documentation and licensing: https://pypdf.readthedocs.io/
- pypdfium2 license and packaged PDFium notices: https://github.com/pypdfium2-team/pypdfium2
- PyMuPDF licensing (excluded baseline): https://pymupdf.readthedocs.io/en/latest/about.html
- BGE model card: https://huggingface.co/BAAI/bge-small-en-v1.5
- Apache License 2.0: https://www.apache.org/licenses/LICENSE-2.0

---

**Implementation is not authorized by this document alone.** Next checkpoint: reconcile documentation and approve the initial M1 implementation plan; create/configure keys only after separate setup consent.
