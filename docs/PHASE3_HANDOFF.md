# Phase 3 handoff — Evidence Collection and Source Management

Prepared 2026-10-28 on `feature/phase3-evidence-collection` (HEAD `17c2bf1`, which
equals `main` and `origin/main`; Phase 2 is merged). **Nothing was committed,
staged, pushed or merged.** All changes are unstaged in the working tree.

## Provenance of this work

At the start of this session the working tree already contained an uncommitted
Phase 3 implementation (collection package, migration 003, collection
repository/routes/UI, tests and documentation edits). It was preserved, audited and
extended; it was not rewritten. This session added the fixes and features marked
**[this session]** below. Historical Phase 1/2 results in other documents remain
historical; the results in TESTING.md were produced in this session.

## Implemented

- **Bounded execution lifecycle.** Collection runs (`queued → running →
  completed | failed | cancelled | interrupted | budget_reached`) persist a run
  configuration snapshot (URLs, question, plan revision). One active run per
  application is enforced by a partial unique index and an atomic claim. Admission
  requires the expected plan revision. Startup converts stale queued/running rows
  to `interrupted`; nothing is replayed automatically. A single lifespan-managed
  worker thread does network-shaped work outside transactions. An OS file lock
  stops a second process from owning the same data directory.
- **Worker-failure handling [this session].** An unexpected exception now
  persists the run as `failed` with `error_code=worker_failure` and the worker
  keeps serving. Previously the worker stopped and the run stayed `running` until
  restart. `finish()` no longer rewrites a run that is already terminal.
- **Cancellation and consent.** Cooperative cancel and fixture-consent revocation
  are checked between URLs, between response chunks and before any save. A
  cancelled/revoked run saves nothing further.
- **Fetch boundary.** URL normalization (http/https only, default ports only, no
  credentials, no backslashes/control characters, IDNA, no `localhost`/`.local`/
  `.internal`, no non-global/multicast/reserved/mapped/6to4/Teredo/NAT64 IPs), DNS
  results all validated, a pinned-transport contract that carries the validated
  IP separately from the Host/SNI name, same-origin redirects only (max 5) with
  every hop re-validated and robots-checked, fail-closed robots.txt, a 15 s total
  deadline, a 5 MB decoded cap, `text/html`/`text/plain` only, bounded gzip only,
  and safe error codes.
- **Host-policy fix [this session].** Letter-only hostnames such as `bad.cafe`
  were wrongly rejected, while `example.123` was accepted even though WHATWG
  parsers treat a numeric final label as IPv4. The policy now rejects only
  numeric or `0x` final labels.
- **Extraction.** Beautiful Soup 4.15.0 with `html.parser`, in a killable
  subprocess with a 5 s deadline. A node/depth structure guard runs first. Scripts,
  styles, nav, header, footer, aside, forms, SVG and hidden nodes are removed. An
  explicit single `<main>`/`<article>` is preferred; otherwise extraction falls
  back to the body and the result is marked `partial`. Very short output is marked
  `partial` with a JavaScript/incomplete-content limitation. Input is UTF-8 only;
  author and date are never inferred.
- **Extraction fixes [this session]; version is now `bs4-4.15.0-html.parser-v2`.**
  Words merged across table cells, `h5`/`h6`, blockquote, definition lists and
  figures (`alpha`+`beta` → `alphabeta`). These elements now get boundaries. The
  title now comes only from the document `<title>`, never from an `<svg><title>`
  icon. Existing v1 snapshots are immutable and keep their recorded version.
- **Storage and provenance.** Immutable `sources`/`passages` (UPDATE triggers);
  SHA-256 of the exact UTF-8 saved text; passages are exact code-point slices of
  the saved text, with offsets checked by tests. Duplicate content within an
  investigation is stored as `duplicate`, linked to the original, with no new
  passages. Failures are stored as source rows without text, and earlier evidence
  is preserved. All reads are scoped by investigation (composite FKs plus
  query-level ownership).
- **Manual URL saving [this session].** `saved_urls` (migration 004) lets users
  record any public http(s) URL with an optional note. Saving never fetches,
  creates a source, run or passage, or becomes evidence. The UI and API label
  every row `retrieved: false` ("Saved · not retrieved"). The same URL policy
  rejects private/loopback/credentialed URLs. The canonical URL is unique per
  investigation (409 on duplicates), identifiers are idempotent, and the limit
  is 200 per investigation.
- **UI.** The Evidence workspace in the investigation page shows the fixture
  disclosure and explicit consent, the synthetic URL form, run history with
  cancel, saved sources with status/limitation/duplicate notes, and an accessible
  inspector (URLs, timestamps, hash, extraction version, exact text, passages with
  offsets). The new **Saved URLs (not retrieved)** panel works in offline mode too.

## Live networking status

**Superseded by M1 (2026-11-02):** a pinned live transport now exists behind opt-in `live_free`
mode; it has not contacted a real website. See M1_HANDOFF.md. The text below is the Phase 3 record.

**Live fetching is disabled and has not been validated.** `DisabledTransport`
raises for every request, and `require_live_permission()` has no opening
condition. Mock mode uses only the in-process `fixture.example` transport; no DNS
lookup, socket or website is used. The fixture/policy tests check the code paths,
**not** real DNS deadlines, connect-time pinning, TLS SNI/certificate checks,
proxy bypass, pooling or real-world redirect/decompression behaviour. A disabled
fetcher is not evidence that live fetching is secure. A real connector needs
separate implementation, controlled validation and owner approval.

## Database

| Migration | Status | Contents |
|---|---|---|
| 001, 002 | Unchanged byte-for-byte (verified with `git diff`) | Phase 1/2 |
| 003_evidence_collection | Pre-existing, unchanged this session | runs, run_stages, run_events, provider_usage, search_queries, provider_consents, sources, passages, immutability triggers |
| 004_saved_urls | **New** | saved_urls |

All pending migrations apply in a single transaction with a pre-upgrade backup;
a failure rolls back every pending migration. Tests cover a populated Phase 2 →
003 upgrade/rollback and a populated 003 → 005 upgrade/rollback (see PHASE4_HANDOFF).

## API (all under `/api`; mutations need exact Origin, session token, JSON)

| Method | Path | Notes |
|---|---|---|
| GET | `/providers` | Gemini/Tavily `disabled`, `live_network:false`, fixture/consent state |
| POST | `/web-consent`, `/web-consent/revoke` | Fixture disclosure consent only (mock mode) |
| POST | `/investigations/{id}/runs` (alias `/sources`) | 202; 1–15 `fixture.example` URLs |
| GET | `/investigations/{id}/runs`, `/runs/{id}?investigation_id=` | History / one run |
| POST | `/runs/{id}/cancel?investigation_id=` | Cooperative cancel |
| GET | `/investigations/{id}/events?run_id=` | Ordered safe events |
| GET | `/investigations/{id}/sources`, `/sources/{id}?investigation_id=` | Summaries / snapshot |
| GET | `/sources/{id}/passages?investigation_id=`, `/passages/{id}?investigation_id=` | Passages |
| GET/POST | `/investigations/{id}/saved-urls` **[new]** | List (50/page) / save (201) |

`/api/capabilities` now reports `phase: 4`, and `research`/`outbound` remain
`false`. All other Phase 1/2 contracts are unchanged.

## Dependencies

No dependency was added, removed or upgraded this session. The pre-existing
Phase 3 change pins beautifulsoup4 4.15.0 and soupsieve 3.0.4 (MIT), and promotes
httpx 0.28.1 / httpcore 1.0.9 (BSD-3-Clause) and certifi (MPL-2.0, approved
exception) to runtime, as recorded in DEPENDENCY_LICENSES.md. **Superseded 2026-10-29:** with owner approval, httpx and httpcore
were returned to development-only because no application code imports them;
certifi is no longer in the production graph (see DEPENDENCY_LICENSES.md). The offline audit
passed and its regenerated outputs were byte-identical (see TESTING.md).

## Remaining limitations and risks

- Only synthetic fixtures can be collected; live fetching, search, Tavily and
  Gemini are disabled.
- UTF-8 only; other declared charsets are reported as `unsupported_encoding`.
- Extraction is heuristic: boilerplate may remain, content may be omitted and
  JavaScript-rendered pages are only flagged. No extraction-accuracy benchmark
  on real pages exists.
- Passages are fixed 2,000-code-point windows that break at spaces, not at
  semantic paragraphs.
- No source deletion or retention workflow, and no automated resume of
  interrupted runs.
- A run with any partial or failed URL is labelled `failed` with
  `partial_collection`, even when other URLs succeeded. The saved sources remain
  visible.
