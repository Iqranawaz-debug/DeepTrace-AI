# Validation records

Records are kept in the order they were added, so **the latest results are the last
section of this file**. Earlier sections are history: their counts and statements
describe the project at that time and are not current.

To run every gate, from the repository root and without redirecting its output:

```powershell
.\scripts\check.ps1
```

# Phase 2 validation

Final checks executed 2026-10-25 on Windows, Python 3.14.3 / SQLite 3.50.4.
The full scripts/check.ps1 suite passed. After the final in-flight navigation
protection change, frontend lint/types/components/build/browser checks were rerun.

| Check | Command | Final result |
|---|---|---|
| Backend lint (backend directory) | `.venv/Scripts/ruff.exe check src tests` | Passed |
| Backend format (backend directory) | `.venv/Scripts/ruff.exe format --check src tests` | Passed, 18 files |
| Backend types (backend directory) | `.venv/Scripts/mypy.exe src` | Passed, 11 source files |
| Backend regression (backend directory) | `.venv/Scripts/python.exe -m pytest -q --basetemp=.cache/test-<unique-id>` | 56 passed |
| Frontend lint (frontend directory) | `npm.cmd run lint` | Passed |
| TypeScript (frontend directory) | `npm.cmd run typecheck` | Passed |
| Components (frontend directory) | `npm.cmd run test` | 11 passed, 3 files |
| Production build (frontend directory) | `npm.cmd run build` | Passed |
| Real browser (frontend directory) | `npm.cmd run test:browser` | 4 passed, Edge 156.0.4314.42 |
| License audit (root) | `backend/.venv/Scripts/python.exe scripts/audit_dependencies.py` | Passed, 372 locked artifacts / 326 installed; generated notices unchanged |
| Python lock (backend directory) | `uv lock --check --offline --cache-dir .cache/uv` | Passed, 32 packages |
| Whitespace (root) | `git diff --check` and `git diff --cached --check` | Passed |

Backend tests include the Phase 1 regressions plus creation/retry/duplicate titles,
validation, bounded listing, literal search, edit conflicts, ordered plan saves,
removal, stable IDs, ownership isolation, simultaneous writer conflicts, injected
write failure rollback, foreign keys, missing/invalid IDs and persistence after
reconnecting. Migration tests cover a fresh schema and populated Phase 1 upgrades,
backup integrity/data retention, failure rollback and checksum/version rejection.
No real user database is touched.

Security tests include hostile/missing/opaque/duplicate Origin, bad Host, invalid,
missing/duplicate/non-ASCII tokens, content type, malformed JSON, oversize bodies,
CORS preflight, session no-store and exclusion of input/tokens from application
logs. Existing provider denial and socket isolation guards remain active.

Component tests cover creation retries with stable UUIDs, persisted-success-only
navigation, failed/conflicting saves retaining input, dashboard recovery/search,
keyboard reordering, step removal, save status and unsaved-navigation confirmation.
A pending-save test verifies that Discard and leave stays disabled until completion.

Edge uses a unique frontend/.cache/browser-<UUID> data directory per invocation;
no destructive cleanup or personal investigation data is used. Tests verify the
full real create/edit/plan/reorder/save/refresh/reopen workflow, a two-tab 409,
Settings round trip, local search, browser Back and discard/keep-editing dialogs.
The Phase 1 shell checks widths 360/390/768/1024/1280/1440; the populated workspace
checks 360/390/768/1440 with no horizontal overflow. axe checks new-investigation,
workspace, Dashboard and Settings: no critical/serious findings after fixing the
reorder buttons' label/name mismatch. Desktop/mobile screenshots under ignored
test-results were visually reviewed. Instrumented browser scenarios observed no
non-local HTTP requests or page exceptions. Non-local requests were blocked.

Initial failures were investigated, not counted as passes: an incorrect initial
pytest temporary path, Windows sandbox IPC restrictions, formatting findings,
a stale health-request fixture and the reorder accessibility labels. Final runs
used approved local execution for browser/worker processes. Existing Starlette
httpx deprecation and Node NO_COLOR/FORCE_COLOR warnings are non-failing.
No full WCAG/NVDA certification, comprehensive penetration/CVE scan or packaged
production-server test is claimed. Production assets were built; E2E runs use Vite.

---

# Historical Phase 1 validation

Final regression: 2026-10-25, Windows, Python 3.14.3 / SQLite 3.50.4,
Node 24.21.0 / npm 11.19.0. Commands executed from the repository root through
`scripts/check.ps1`, which stops at the first failing command.

| Check | Exact command (in indicated directory) | Result |
|---|---|---|
| Backend lint | `backend: .venv/Scripts/ruff.exe check src tests` | Passed |
| Backend formatting | `backend: .venv/Scripts/ruff.exe format --check src tests` | Passed, 10 files |
| Backend types | `backend: .venv/Scripts/mypy.exe src` | Passed, 7 source files |
| Backend regression | `backend: .venv/Scripts/python.exe -m pytest -q --basetemp=.cache/test-<unique-id>` | 31 passed |
| Frontend lint | `frontend: npm.cmd run lint` | Passed |
| TypeScript | `frontend: npm.cmd run typecheck` | Passed |
| Components | `frontend: npm.cmd run test` | 5 passed, 1 test file |
| Production build | `frontend: npm.cmd run build` | Passed |
| Browser | `frontend: npm.cmd run test:browser` | 2 passed, Microsoft Edge |
| Dependency licenses | `backend/.venv/Scripts/python.exe scripts/audit_dependencies.py` | Passed, 372 locked artifacts, 326 installed |
| Frozen Python lock | `backend: uv lock --check --offline --cache-dir .cache/uv` | Passed, 32 packages resolved |
| Frozen environment | `backend: uv sync --frozen --offline --cache-dir .cache/uv` | Passed |
| Git whitespace | `git diff --check` | Passed |
| Specifications | `git diff --exit-code HEAD -- PRD.md docs/DESIGN.md docs/INTEGRATIONS.md docs/ARCHITECTURE.md docs/DATABASE.md` | Passed; unchanged |

## Exercised behavior

Backend coverage includes health, readiness failure, capabilities, default mock
and explicit offline modes, local CORS preflight, hostile/opaque origins,
untrusted/malformed Host values, rejected state-changing requests, unsafe
configuration rejection, safe error shape and secret/content exclusion from
application logs and responses. All provider identifiers, including Gemini and
Tavily, are denied by the provider boundary. Socket connection APIs are blocked
in tests, except Python's internal Windows asyncio wakeup socket pair. Explicit
guard tests verify that real connection attempts fail before network use.

Six database tests cover clean initialization, empty production tables, migration
replay with unchanged metadata, WAL, per-connection foreign keys and busy timeout,
transaction rollback, checksum tampering, newer schema rejection, failed DDL
upgrade rollback, readable backup integrity, rejection of credential settings,
and concurrent replay. Temporary foreign-key fixture tables verify enforcement;
the three Phase 1 tables have no domain relationships requiring foreign keys yet.
Tests use isolated databases, never the user's application database.

Frontend tests cover shell/empty states, milestone gating, Settings navigation
and focus, connection failure/retry, sidebar preference and malformed API data.

Real Edge tests run the actual backend and Vite proxy. They check widths 360,
390, 768, 1024, 1280 and 1440 pixels; no document-level horizontal overflow;
no critical/serious axe violations on the tested pages; Settings focus; mobile
dialog Escape/focus return; visibility under reduced motion/forced colors;
connection failure/retry; no page JavaScript errors; and zero non-local HTTP
requests. Non-local browser requests are blocked and recorded. No live provider
or paid API is involved. This is not a full WCAG compliance certification.

Desktop/mobile screenshots are generated under ignored `frontend/test-results`.
They were visually reviewed during implementation. Browser smoke uses the dev
server; the production artifact is separately built and checked for local font
preloads, included licenses, and absence of MPL tools in its bundled module list.

## Warnings and verification limits

- Starlette emits one deprecation warning for the HTTPX-based test client and
  recommends httpx2. Tests pass; no replacement package was silently introduced.
- Playwright/Node may report that FORCE_COLOR overrides NO_COLOR; nonfunctional.
- Windows sandbox loopback/temp restrictions blocked early runs; the final suite
  ran with approved local execution outside those restrictions. Initial failures
  were not counted as passes. A Windows executable quoting error was fixed.
- Earlier npm peer mismatch was fixed using TypeScript 6.0.3; supported ESLint 10
  replaced deprecated ESLint 9 without force/legacy-peer-deps overrides.
- The license inventory initially hit Windows default text decoding; it now reads
  manifests explicitly as UTF-8. Missing upstream MIT notice handling is recorded
  in `DEPENDENCY_LICENSES.md`.
- No NVDA session, fresh-machine installer test, performance benchmark or broad
  penetration test was performed. Full zoom/text-spacing and manual accessibility
  coverage remain release-hardening work. No backend CVE scan is claimed.
- No cloud/provider functionality, research engine or full user-data deletion
  workflow exists to validate in Phase 1.

## Phase 3 checks

The same `scripts/check.ps1` command includes the new collection tests and real
Edge evidence workflow. All content is synthetic; the browser blocks external
requests, backend tests guard socket connections, and runtime mock retrieval has
no network connector. Run tests against disposable data directories only.

New suites: `test_collection_security.py` (URL/DNS, redirect/robots, compression,
consent, extraction, parser timeout and Unicode offsets), `test_collection_api.py`
(run admission/history, source hashes/immutability, ownership, cancellation,
revocation, deduplication, atomic checkpoints, worker lock and Tavily contracts),
`test_phase3_migrations.py` (populated 002 upgrade, failed 003 rollback and verified
backup), `EvidenceWorkspace.test.tsx`, and `e2e/phase3-evidence.spec.ts`.

Dependency checks: the offline `scripts/audit_dependencies.py` regenerates exact
inventory/notices; `npm.cmd audit --json` checks npm advisories. The Phase 3 OSV
batch audit checked all 33 non-application packages in uv.lock by exact version.
Only dependency metadata was transmitted. Network-dependent audits are separate
from ordinary application tests and require network access.

Live-network activation remains gated: synthetic tests cannot verify actual
socket address pinning, TLS SNI/certificate checks, operating-system DNS deadlines,
proxy bypass prevention under a real connector, connection pooling behavior or
real-world redirect/decompression behavior. A future connector needs separate
controlled validation and owner approval before any live research traffic.


## Phase 3 completion and Phase 4 validation (executed 2026-10-28)

Windows 11, Python 3.14.3, SQLite 3.50.4, Node 24.21.0, Microsoft Edge
156.0.4314.50. Final run: `.\scripts\check.ps1` from the repository root, exit 0.

| Check | Command | Result |
|---|---|---|
| Backend lint | `ruff check src tests` | Passed |
| Backend format | `ruff format --check src tests` | Passed, 43 files |
| Backend types | `mypy src` | Passed, 30 source files |
| Backend tests | `pytest -q --basetemp=.cache/test-<guid>` | **146 passed** |
| Frontend lint / types | `npm.cmd run lint`, `npm.cmd run typecheck` | Passed |
| Components | `npm.cmd run test` | **19 passed**, 5 files |
| Production build | `npm.cmd run build` | Passed |
| Real browser | `npm.cmd run test:browser` | **6 passed** (Edge 156.0.4314.50) |
| License audit (root) | `backend/.venv/Scripts/python.exe scripts/audit_dependencies.py` | Passed: 374 locked / 328 installed; regenerated inventory and both notices byte-identical |
| Python lock (backend) | `uv lock --check --offline --cache-dir .cache/uv` | Passed, 34 packages |

Baseline before this session's changes (same machine): 120 backend, 15 component
and 3 of 5 browser tests passed. The `investigations` two-tab conflict test passed
when re-run alone (10.4 s) and in both later full runs, so it is treated as a
load-timing flake; its 5 s assertion was not relaxed. The Phase 3 evidence spec
had a real race (`isVisible()` before the panel loaded); the test now waits for
the provider state. The committed `HEAD` backend (exported via `git archive`,
outside the repo) passed 56 tests, matching the historical Phase 2 report.

New and updated suites:
- `test_phase3_fixes.py`: hex-letter hostnames accepted; numeric/0x final labels
  rejected; no word merging across cells/h5/blockquote/dl; `<head>` title only;
  worker failure → `failed/worker_failure` with the worker still serving; a
  terminal run is never rewritten.
- `test_synthesis_api.py`: saved URL is a lead (no source/run, idempotent,
  duplicate 409, unsafe 422, isolation); evidence reviews (revisions, stale 409,
  unknown target, foreign passage 404, removed step keeps label); fabricated,
  cross-investigation and mismatched-quote citations rejected with nothing
  persisted; NFC/whitespace, case-sensitive quotes; cited / not-established /
  contradicting states; report creation, escaping (no unescaped `<` or `](`),
  checksum, download bytes and headers, UPDATE trigger, version 2 leaving version 1
  unchanged, older-version warnings, persistence across an app restart,
  tamper detection (500), cross-investigation isolation, DB composite-FK
  rejection, token/origin on all new mutations, kernel and escaping units.
- `test_phase4_migrations.py`: populated 003 → 005 upgrade preserves sources and
  passages; a failing 005 rolls back all pending migrations; backup verified.
- `test_database.py` / `test_phase3_migrations.py`: version numbers derived from
  the migration count instead of hard-coded.
- `Report.test.tsx`: hostile source text rendered inertly (no img/script, no
  execution); a rejected citation keeps edits and shows the server reason;
  Cited/Not-established badges; passage dialog; exact preview and download href;
  saved-URL retry identifier reuse.
- `e2e/phase4-report.spec.ts`: save URL → collect → review → claim with quotation
  → save → create version → download; the downloaded file's SHA-256 equals the
  stored hash; 390/1440 px no horizontal overflow and no serious/critical axe
  findings; reload persistence; injected `<script>` in the summary not executed;
  zero non-local requests; no page errors. The test found a real 390 px overflow
  (unbreakable SHA-256 line), which was fixed.

Running `check.ps1` with `*>&1` redirection under Windows PowerShell 5.1 fails
on Node's `NO_COLOR` stderr warning; run it unredirected. Not claimed: manual
WCAG/NVDA audit, penetration test, CVE scan, real-network fetch validation or
extraction accuracy on real web pages.

## Re-audit validation (executed 2026-10-29)

Same toolchain and Edge 156.0.4314.50. All results below come from this run.

| Check | Command | Result |
|---|---|---|
| Baseline before re-audit edits | `.\scripts\check.ps1` | Exit 0: 146 backend, 19 component, 6 Edge passed |
| Backend lint / format / types | `ruff check`, `ruff format --check`, `mypy src` | Passed (44 files formatted; 30 source files typed) |
| Backend tests | `pytest -q` (via check.ps1) | **156 passed** (adds `test_phase4_integrity.py`, 10 tests) |
| Components | `npm.cmd run test` | **20 passed** (adds keyboard claim reorder) |
| Lint / types / build | `npm.cmd run lint`, `typecheck`, `build` | Passed |
| Edge, final check.ps1 | `npm.cmd run test:browser` | 5 passed, **1 failed**: `foundation` timed out (30 s) inside its six-width axe scan |
| Edge, two standalone re-runs | `npx.cmd playwright test` | **6 passed** both times (foundation 25.8 s and 20.0 s) |
| License audit | `backend/.venv/Scripts/python.exe scripts/audit_dependencies.py` | Passed: 374 locked / 328 installed; outputs byte-identical |

One run caught a real formatting failure in a new test file (`ruff format
--check`); it was formatted and the full suite re-run, not skipped.

**Timing risk (pre-existing Phase 1 test, not modified):** `foundation.spec.ts`
uses Playwright's default 30 s test timeout and here takes 15–26 s, mostly in
CPU-bound axe scans at six widths. Under load it can exceed 30 s. Its assertions
are unaffected. Raising its timeout would be a test-configuration change for the
owner to decide.

Dependency facts were checked against `backend/pyproject.toml` and `uv.lock`,
not the handoff: beautifulsoup4 4.15.0, soupsieve 3.0.4, httpx 0.28.1, httpcore
1.0.9 and certifi 2026.10.23 (MPL-2.0, runtime through httpx/httpcore), matching
DEPENDENCY_LICENSES.md. No application module imports httpx or httpcore (see the
PHASE4_HANDOFF addendum). The npm audit and OSV checks recorded on 2026-10-26
need network access and were **not** re-run; they remain historical.

## Dependency move validation (executed 2026-10-29)

After httpx/httpcore were returned to development-only (see DEPENDENCY_LICENSES.md):

| Check | Command | Result |
|---|---|---|
| Relock (backend) | `uv lock --offline` (default uv cache) | 34 packages; only `deeptrace`'s two runtime requirements removed |
| Lock gate (backend) | `uv lock --check --offline` | Passed, 34 packages |
| Dev environment (backend) | `uv sync --frozen --offline`, then `--check` | Only the editable project reinstalled; "Would make no changes" |
| Production-only install | `UV_PROJECT_ENVIRONMENT=<scratch> uv sync --frozen --no-dev --offline` (project cache, skipping bs4/soupsieve), then the same with the default cache, then `--check` | 19 packages; httpx, httpcore, certifi, pytest and mypy absent; "Would make no changes" |
| Production smoke | scratch `python -I prod_smoke.py` (raw ASGI, no httpx) | Passed: ready, session, create, consent, collection (P-0001, extractor v2), cited draft, report, byte-exact download |
| License audit | `scripts/audit_dependencies.py` | Passed: 374 / 328; inventory changed only certifi/httpcore/httpx `development` flags; notices byte-identical |
| Full gates | `.\scripts\check.ps1` | Exit 0: see the summary below |

The production install needs two offline passes because no single local uv cache
holds every locked wheel: `.cache/uv` lacks beautifulsoup4, and the default
cache lacks the pydantic-core wheel. A normal online `uv sync --frozen --no-dev`
would fetch the same hash-locked artifacts. No network was used. The smoke script
lives in the session scratchpad, not the repository; there is still no committed
production-only install test.

Full gates after the move: ruff/format (44 files)/mypy (30 files) passed; **156**
backend, **20** component and **6/6** Edge tests passed; build passed.

## M1 validation (executed 2026-11-02)

Same toolchain, Edge 156.0.4314.50. `.\scripts\check.ps1`, run unredirected, exit 0.

| Check | Command | Result |
|---|---|---|
| Backend lint / format / types | `ruff check`, `ruff format --check`, `mypy src` | Passed (58 files formatted; 42 source files typed) |
| Backend tests | `pytest -q` | **277 passed** |
| Frontend lint / types / build | `npm.cmd run lint`, `typecheck`, `build` | Passed |
| Components | `npm.cmd run test` | **29 passed**, 6 files |
| Real browser | `npm.cmd run test:browser` | **7 passed** |
| License audit | `backend/.venv/Scripts/python.exe scripts/audit_dependencies.py` | Passed, 374 / 328; outputs byte-identical |
| Python lock | `uv lock --check --offline` | Passed, 34 packages |
| Production-only smoke | scratch `python -I prod_smoke.py` in a `--no-dev` environment | Passed: plan, research, report; httpx/httpcore/certifi absent |
| Real TLS on loopback | scratch `tls_check.py` with a temporary self-signed certificate (deleted after) | Untrusted certificate fails closed; trusted connects to pinned IP with correct SNI; wrong name fails closed |

New suites: `test_m1_research.py`, `test_m1_live_boundary.py`, `Research.test.tsx`,
`e2e/m1-research.spec.ts`. Backend tests allow real sockets only in one loopback fixture, which
proves where a pinned connection goes. `test_windows_credential_manager_round_trip` writes a
synthetic value to Windows Credential Manager under a random test name, then deletes it.

**Not run:** any real Tavily, Gemini or public-website request (no keys; see M1_HANDOFF.md).
The production and TLS checks are scratch scripts and are not part of `check.ps1`. A manual
keyboard or NVDA audit, penetration test and CVE scan are not claimed.

## M1 follow-up validation (executed 2026-11-02)

After the missed M1 requirements were fixed. `.\scripts\check.ps1`, unredirected, exit 0.

| Check | Result |
|---|---|
| Backend lint / format / types | Passed |
| Backend tests | **290 passed** |
| Frontend lint / types / build | Passed |
| Components | **34 passed**, 6 files |
| Real browser | **7 passed**, Edge 156.0.4314.50 |
| License audit | Passed, 374 / 328; outputs byte-identical |
| Python lock | Passed, 34 packages |
| Production-only smoke (scratch script) | Passed; httpx, httpcore and certifi absent |

New: `test_m1_gaps.py` covers partial reports, `Retry-After`, log rotation and the storage
warning. `Research.test.tsx` and `m1-research.spec.ts` cover the tracker, activity log, cancel
confirmation and evidence view. **Still not run:** any real Tavily, Gemini or website request.

## CI validation (executed 2026-11-02)

`.github/workflows/ci.yml` has two Windows jobs: all project checks, and a production-only
install. **It has not yet run on GitHub**, because the commit that adds it has not been pushed.
Every step was instead replayed in clean local clones with fresh installs, under a short path:

| Step | Result |
|---|---|
| `uv sync --frozen`, `npm ci` | Passed |
| `uv lock --check` | Passed, 35 packages |
| `scripts/scan_secrets.py --history` | Passed, 143 files and full history |
| `scripts/check.ps1` with `CI=true` | Exit 0: **308 backend** tests, **92%** line and branch coverage, **34 component** tests, build, **7 Edge** tests |
| `scripts/audit_dependencies.py`, then `git diff --exit-code` | Passed, 375 / 329; records unchanged |
| `uv sync --frozen --no-dev`, then `scripts/production_smoke.py` | Passed, 5 sources, report saved |

Differences from the real runner: the rehearsal used Windows PowerShell 5.1 where the runner uses
PowerShell 7, ran on this machine's existing Edge, and did not exercise the action wrappers or
caching. The workflow was parsed as YAML and its actions checked as pinned to commits; `actionlint`
was not run. In CI, Playwright's per-test timeout is 90 s rather than 30 s, with no retries.

Coverage floor: `fail_under = 85` in `backend/pyproject.toml`, above the 80% target in NFR-M2.
Code run in the parser subprocess is not counted, which understates `parser_process.py` (55%).
Frontend coverage is not measured. The secret scan matches known key formats only.

Windows' 260-character path limit can fail `test_secret_scan.py` when the checkout path is very
long, because those tests create Git repositories under pytest's temporary folder.
