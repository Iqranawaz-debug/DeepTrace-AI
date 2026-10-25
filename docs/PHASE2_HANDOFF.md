# Phase 2 handoff — Investigation Workspace and Research Planning

Implemented on 2026-10-25 on `feature/phase2-investigation-workspace`, based on
clean, remotely verified main `45b23adb29e70a6eafbba9c2701e0b34c9310d38`.
No commit, push, merge or pull request was performed. Changes are unstaged.

## Implemented

- Local investigation creation, title/question search, bounded pagination,
  recent-activity sorting, reopening and draft detail editing.
- UUIDs, persisted UTC timestamps, duplicate titles, optional descriptions.
- One editable manual plan per investigation, zero to eight steps, optional
  search-query notes, stable identifiers, accessible ordering and step removal.
- Atomic whole-plan saves, revision-based conflicts (409), timestamp-based
  investigation edit conflicts, and retry-safe creation using a client UUID.
- Separate details/plan save feedback; failed requests preserve edits in memory.
  In-app navigation, browser Back and refresh protection for unsaved work.
  Leaving is disabled while a save is pending; no automatic conflict overwrite.
- Existing Chart Room tokens, local fonts, navigation, Settings, connectivity
  indicators, health/readiness, provider denial and licensing preserved.

## Approved Phase 2 resolutions

The owner's conditional approval authorizes manual planning and editing now,
without changing the five specifications or DESIGN review status. Investigations
remain `draft`; reopening means continuing editing, not resuming execution.
Questions may be edited while drafts. Description is an additive bounded field.

Each investigation has one mutable plan. `revision_no` is an optimistic concurrency
counter, not retained historical snapshots. Provider/model/prompt fields are NULL
for manual work; `originating_run_id` is deferred until runs exist. No fabricated
model provenance, evidence, execution status or findings are generated. Empty
plans and fewer than three steps are valid drafts; an entered step requires a
nonblank sub-question. Query notes are never executed. Plan-item removals become
persistent only after Save plan. Investigation deletion/archive are deferred.

## API contracts

All endpoints retain `/api`. Existing health responses remain compatible;
capabilities now reports phase 2 and investigations=true, with research/outbound=false.

| Method and path | Contract |
|---|---|
| GET /api/health | Existing health response |
| GET /api/ready | Current schema readiness |
| GET /api/capabilities | Phase and offline capability flags |
| GET /api/openapi.json | Typed request/response schema |
| GET /api/session | Transient process-local token; no-store |
| POST /api/investigations | title, question, optional description and optional UUID id; 201 |
| GET /api/investigations | q (max 1000), limit (1–100, default 25), offset (0–1000000); items + total |
| GET /api/investigations/{id} | Saved investigation, or 404 |
| PATCH /api/investigations/{id} | title, question, description, expected_updated_at; 200 or 409 |
| GET /api/investigations/{id}/plan | id, revision_no, items; absent plan returns null id, revision 0, [] |
| PUT /api/investigations/{id}/plan | expected_revision and ordered items; atomic 200 or 409 |

PATCH submits the complete editable details, not a partial field merge. Each
plan item contains UUID id, sub_question and optional search_query. Array order
becomes database ordinal. Parent ownership is checked before any replacement.
Unknown request fields, duplicate item IDs and invalid UUIDs are rejected.

Input limits: trimmed title 1–120, question 10–1000, description up to 5000,
step sub-question 1–1000, query note up to 500 characters. At most eight steps;
mutation body cap 65536 bytes. Errors use the existing safe error envelope, with
422 validation, 404 missing resource, 409 conflict, 403 origin/token, 415 content
type and 413 size responses. Internal errors do not expose SQL or input content.

Creation uses a browser-generated UUID retained across retries. Repeating the
same id and details returns the existing record; changing its content returns
409. Callers omitting id receive a server-generated UUID. Duplicate titles with
different IDs are allowed. Search is a parameterized literal substring match
against title/question; SQLite's default case folding is ASCII-oriented.

## Database

Migration `001_foundation.sql` is unchanged byte-for-byte. New migration
`002_investigation_workspace.sql` adds nullable investigation description,
plans and plan_items with ownership FKs, unique plan per investigation and
unique positive ordinals within each plan. No user data is deleted or seeded.

The existing runner verifies checksums, uses WAL, enables FKs per connection,
backs up existing databases before upgrade, and rolls back failed migration SQL
and version records together. Readiness now uses the current migration count.
Writes use BEGIN IMMEDIATE. Plan item replacement, revision increment and activity
update commit together; any failure restores all previous values. Read snapshots
keep a plan's revision and items consistent. Activity timestamps advance only on
successful writes. Automatic downgrade is not implemented; rollback tests cover
failed migrations and failed transactions, not destructive schema downgrades.

## Security and privacy

Writes require the existing exact local Host/Origin allowlists, a single valid
X-DeepTrace-Token header and application/json. Missing, opaque, hostile or
duplicate Origin/token headers are denied. Token comparison handles malformed
non-ASCII input safely. Unsupported mutation routes/methods remain unavailable.
CORS permits only the required methods/headers, no wildcard or credentials.

The random token exists for the backend process lifetime. The frontend fetches
it into request-local memory; no token is placed in URLs, localStorage,
sessionStorage or logs. Session responses use no-store. Browser saves obtain a
fresh token each time. Application logs contain only fixed event/status fields,
not questions, request URLs, tokens or raw exception details.

This is browser request protection, not authentication against malicious software
running under the same OS account. SQLite is not encrypted; inherited OS profile
permissions and upgrade backups remain as in Phase 1. Approved localhost origins
must be trusted. No protection against a compromised allowed frontend is claimed.

Gemini/Tavily remain unconditionally disabled; no provider call, telemetry,
remote font, paid service, scraping or research transmission was introduced.
Backend tests deny real socket connections, allowing only Python's internal
Windows asyncio wakeup pair. Browser checks block and record non-local requests.

## Dependencies and licensing

No dependencies were installed, added or upgraded. Python 3.14.3, SQLite 3.50.4
and the existing Node/npm environment were used. Both lockfiles, Apache-2.0
application license, font assets/licenses, approved MPL exceptions and third-party
notices are unchanged. Offline audit: 372 locked artifacts, 326 installed; no new
copyleft/unknown license identifiers. Frozen Python lock check resolved 32 packages.
The Phase 1 distribution obligations and limitations still apply.

## Windows startup

From repository root in one PowerShell window:

```powershell
.\scripts\dev.ps1 migrate
.\scripts\dev.ps1 backend
```

In a second window:

```powershell
.\scripts\dev.ps1 frontend
```

Open http://127.0.0.1:5173. Default data remains
`%LOCALAPPDATA%\DeepTraceAI\deeptrace.sqlite3`, outside OneDrive. Migration backs
up an existing Phase 1 database before applying 002. See SETUP.md for installation
and recovery precautions. No personal application database was used for testing.

## Validation

See TESTING.md for exact commands, results and browser coverage. Final results:
56 backend tests, 11 component tests, four real Edge tests; Ruff lint/format,
mypy, ESLint, TypeScript, production build and offline license audit passed.
Edge version: 156.0.4314.42. Tested create/edit/reorder/save/refresh/reopen,
two-tab stale-plan conflicts, Settings, search, keyboard movement and browser Back.
No serious/critical axe violations in tested screens, no non-local HTTP requests
or page exceptions in the instrumented workflow. Desktop/mobile screenshots
were visually reviewed. This is not a full accessibility/security certification.

## Known limitations and deferred capabilities

- Manual planning only: no AI helper, execution, search, sources, evidence, reports,
  PDFs, embeddings, authentication, cloud sync or packaged release.
- No investigation deletion/archive, historical plan versions or automatic merge.
- Unsaved edits exist only in browser memory. On conflict, copy edits, reload the
  saved version and reapply deliberately. A lost success response may require
  reloading to inspect persisted data; no automatic overwrite is attempted.
- Only one optional query note per step; generated multi-query plans are deferred.
- Default SQLite ASCII case-insensitive matching; no linguistic search index.
- Existing Starlette/httpx deprecation and Node color-environment warnings remain.
- No NVDA audit, broad penetration test, backend CVE scan, installer or complete
  zoom/text-spacing audit is claimed.

## Inventory and Git

Complete changed-file inventory is listed below. The only addition to the planned
implementation file set is frontend/src/main.tsx, switching the existing router
to its data-router entry point for supported navigation blocking; no dependency
change was required. Existing foundation browser tests were preserved unchanged.
No files are staged. Suggested commit message:

`feat: add local investigation workspace and manual research plans`

| Status | File |
|---|---|
| Modified | `README.md` |
| Modified | `backend/src/deeptrace/main.py` |
| New | `backend/src/deeptrace/models.py` |
| New | `backend/src/deeptrace/routes.py` |
| New | `backend/src/deeptrace/security.py` |
| Modified | `backend/src/deeptrace/storage/database.py` |
| New | `backend/src/deeptrace/storage/migrations/002_investigation_workspace.sql` |
| New | `backend/src/deeptrace/storage/repository.py` |
| Modified | `backend/tests/test_api.py` |
| Modified | `backend/tests/test_database.py` |
| New | `backend/tests/test_investigations.py` |
| New | `backend/tests/test_phase2_migrations.py` |
| New | `backend/tests/test_plans.py` |
| New | `backend/tests/test_security.py` |
| New | `docs/PHASE2_HANDOFF.md` |
| Modified | `docs/SETUP.md` |
| Modified | `docs/TESTING.md` |
| New | `frontend/e2e/investigations.spec.ts` |
| Modified | `frontend/playwright.config.ts` |
| Modified | `frontend/src/api/client.ts` |
| Modified | `frontend/src/app/App.tsx` |
| Modified | `frontend/src/components/States.tsx` |
| New | `frontend/src/features/investigations/Dashboard.tsx` |
| New | `frontend/src/features/investigations/InvestigationForm.tsx` |
| New | `frontend/src/features/investigations/InvestigationPage.tsx` |
| New | `frontend/src/features/plans/PlanEditor.tsx` |
| Modified | `frontend/src/main.tsx` |
| Modified | `frontend/src/styles/app.css` |
| Modified | `frontend/src/test/App.test.tsx` |
| New | `frontend/src/test/Investigations.test.tsx` |
| New | `frontend/src/test/PlanEditor.test.tsx` |
