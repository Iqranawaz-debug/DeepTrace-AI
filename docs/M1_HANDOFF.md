# M1 handoff — Vertical Slice

Prepared 2026-11-02 on `feature/phase3-evidence-collection` (HEAD `17c2bf1`).
**Nothing was committed, staged, pushed or merged.** Exact commands and results are in
TESTING.md.

## Status: complete in mock mode; live mode built but not exercised

PRD §22 sets the M1 exit as AC-01/02/03/06/09/11 with a "demo on mock fixtures". Those
pass. ARCHITECTURE §12 also calls for an opt-in live smoke test, and says to document
`mock-only` completion honestly if provider access is unavailable. **That is the case:**
no Tavily or Gemini key was available, so **no real provider and no real public website
has ever been contacted by this code.** Live adapters are contract-tested with fakes only.
Do not describe this as verified live research until the procedure below has passed.

| Criterion | Result | Evidence |
|---|---|---|
| AC-01 Restart restores work | Pass | `test_restart_restores_everything_and_interrupts_stale_runs` |
| AC-02 Plan schema, narrow exception | Pass with the mock model | Ten questions; a real model is untested |
| AC-03 Mock slice with cited report | Pass | API test and real Edge journey |
| AC-06 Citations pass validation | Pass | Fabricated and misquoted citations suppressed |
| AC-09 429/5xx bounded retries | Pass | Three attempts at most; state kept |
| AC-11 Budgets stop exactly | Pass | Search, page and token caps; partial sources kept |
| AC-14 Injection fixtures (M4 gate, started) | Pass on the fixture set | 22 fixtures, including a fully obedient model |
| AC-15 Seeded secret | Pass | Absent from database files, responses, logs, reports |
| AC-21 SSRF fixtures (M4 gate, started) | Pass on fixtures | Not validated against the real internet |

## What was built

- **Pipeline.** Plan → discover → fetch → extract → rank → synthesize → validate → report,
  run by the existing single lifespan worker. Each stage is checkpointed. Source failures do
  not stop a run. Hitting a limit gives `Budget reached` and keeps the evidence.
- **Plans.** Generated as a worker run, saved with provider, model and prompt version, and
  editable. An existing plan is replaced only with explicit confirmation. A plan under three
  steps must give a reason. Editing a generated plan clears its generation provenance.
- **Budgets.** Shown and adjustable before a run, with PRD ceilings enforced by the API.
- **Answers.** Claims are `Cited` only with a citation that passed validation against the
  run's allowlist of at most 12 ranked passages; otherwise `Not established`. Invalid
  citations are suppressed and counted. State is recomputed on every read.
- **Reports.** FR-07 sections, the required "AI-generated research aid" disclaimer, a
  SIMULATED banner in mock mode, queries, provider, model, prompt version, retrieval dates,
  source statuses and omissions. Immutable, checksum-verified, downloadable `.md`.
- **Model boundary.** The model has no tools and never chooses a URL. Only search leads that
  pass URL policy are fetched. Passages are delimited and cannot forge delimiters. Output is
  schema-validated with one retry. All text is escaped in the report and rendered as plain
  React text in the app.
- **Live path (opt-in).** `DEEPTRACE_MODE=live_free`, which only local configuration and a
  restart can set. Tavily and Gemini use fixed hosts with no configurable base URL. The
  gateway checks mode, allowlist, credential and versioned consent before **every** attempt.
- **Pinned transport.** Standard-library `http.client` and `ssl`: connects to the validated
  IP, verifies the certificate and SNI against the original hostname, ignores proxy
  variables, follows no redirects itself and never re-resolves. DNS has its own deadline.
- **Credentials.** Windows Credential Manager through `advapi32`. Write-only API, masked
  input, never in SQLite. `TAVILY_API_KEY` and `GEMINI_API_KEY` process variables are a
  development fallback. Do not put keys in `backend/.env`: unknown keys there stop startup.
- **Lifecycle.** Derived status (Draft, Planning, Running, Completed, Failed, Cancelled,
  Budget reached, Interrupted, Archived), archive and unarchive, a sensitive flag that blocks
  hosted-model use, and delete with exact-title confirmation.
- **Screens.** Research panel, Sources page, `/setup`, provider cards in Settings, a Report
  tab showing generated reports, dashboard status and source counts, and a live-mode banner.

## Database

Migration `006_research_pipeline` is additive apart from rebuilding `run_stages` to widen its
stage keys (nothing references that table; rows are preserved and tested). It adds
`investigation_archives`, `generated_answers`, `generated_claims`, `generated_citations` and
`generated_reports` (with an immutability trigger). Migrations 001–005 are unchanged.

## API additions

| Method | Path |
|---|---|
| POST | `/api/investigations/{id}/plan/generate` |
| POST | `/api/investigations/{id}/research` |
| GET | `/api/runs/{id}/progress?investigation_id=` |
| GET | `/api/investigations/{id}/generated-answer` |
| GET | `/api/investigations/{id}/generated-reports`, `/{n}`, `/{n}/download` |
| POST | `/api/investigations/{id}/sensitive`, `/archive` |
| DELETE | `/api/investigations/{id}` (exact-title body) |
| PUT/DELETE | `/api/providers/{id}/credential` |
| POST/DELETE | `/api/providers/{id}/consent` |

**Changed contracts:** `GET /api/providers` is extended and `live_network` can now be true;
`/api/capabilities` reports `phase: 5` and `research: true` outside offline mode; investigation
responses add `sensitive`, `archived_at`, `source_count` and `lifecycle`. A Phase 1 test that
listed `live_free` as an invalid mode now uses a mode that remains invalid. `DELETE` is allowed
only on the exact paths above, with the same Origin, token and JSON checks.

## Dependencies

None added, removed or upgraded; `httpx`, `httpcore` and `certifi` stay development-only. A
frozen production-only environment (19 packages, none of those three) ran the full pipeline.

## Differences from the specs (owner review)

1. **HTTP library.** INT-03 names HTTPX; this uses the standard library, because it gives real
   connect-time pinning with no new runtime dependency or MPL obligation. ARCHITECTURE §8
   allows an equivalent approach.
2. **Extractor.** INT-04 names Trafilatura; the owner-approved Beautiful Soup extractor is kept.
3. **Separate generated tables.** `generated_*` tables keep model output apart from the
   user-authored `answers`, `claims` and `citations`, and generated reports have their own
   version sequence.
4. **Run kind and status.** `runs.kind` stays `research` (its CHECK blocks `plan`), with the
   scope in the run snapshot. `investigations.status` stays `draft`; lifecycle is derived. Archive
   uses a new table because migration 001 forces `archived_at` to NULL.
5. **One query per plan step.** FR-02.1 allows up to three; this uses one.
6. **Setup.** No automatic first-run redirect, because mock mode needs no setup. `/setup` is linked.
7. **Evidence and sources UI.** Evidence opens in a dialog, not a docked drawer addressed by
   `?evidence=`. Sources are cards with a filter, not a sortable table.
8. **Deletion** is database-only, as M1 stores no app-managed files. Upgrade backups can still
   hold deleted data, and the dialog says so.

## Known limitations affecting live use

- Redirects to a different scheme or host are refused, including http→https.
- A missing or unreadable `robots.txt` blocks that page (ADR-A13 fails closed), so some normal
  sites will show as `blocked`.
- UTF-8 only. Near-duplicate detection is exact text hash only.
- Author and date come only from page `<meta>` tags. Extraction accuracy is unmeasured.
- Only the first validated address is tried. Interrupted runs are not resumed (M3).
- Automatic conflict detection and semantic support assessment are M3.
- Tavily's and Gemini's request shapes follow published APIs but are unverified live.
- A plan's model usage counts toward provider ledgers, not the later research run's budget.
- Keys in Windows Credential Manager are readable by other software under your account.

## Opt-in live smoke procedure (you run this; it uses your accounts)

1. Confirm in each provider's dashboard that your account and region are on a free tier, and
   choose a free Gemini model ID. Use only synthetic or public questions.
2. Open `/setup`, save both keys and accept all three disclosures.
3. In `backend/.env`, set `DEEPTRACE_MODE=live_free` and `DEEPTRACE_LLM_MODEL=<model id>`, then
   restart the backend. Leave `Allow paid APIs` off; it cannot be enabled.
4. Create a test investigation with a narrow public question. Set budgets low (for example 1
   search, 2 pages) and start research.
5. Check source statuses, open each citation, and confirm usage in the provider dashboards.
6. To return to mock mode, remove those two lines and restart; revoke consent or remove keys in
   Settings as needed.

Record the results before calling M1 live-verified. Provider terms and quotas change, so re-check
them first.
