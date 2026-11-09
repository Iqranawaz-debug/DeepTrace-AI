# Windows setup — Phases 1–4

Verified environment: Windows, PowerShell 7.6.5, Python 3.14.3, SQLite 3.50.4,
Node 24.21.0, npm 11.19.0 and uv 0.13.4. Python 3.14 is the supported backend
interpreter for this application. Runtime dependencies are recorded in `backend/uv.lock`;
frontend dependencies are recorded in `frontend/package-lock.json`.

## Install

Run from the repository root. Installation downloads packages; the running app
does not contact providers. No Docker, provider keys or billing setup is needed.

```powershell
Set-Location C:\Users\iqran\OneDrive\Desktop\DeepTrace-AI
Set-Location backend
uv venv --python 3.14
uv sync --frozen
Set-Location ..\frontend
npm.cmd ci --ignore-scripts
Set-Location ..
```

`uv sync` also creates the virtual environment if it is missing. Activation is
optional; commands below use its interpreter directly. Do not overwrite an
existing `.env`. If customization is needed, copy the root `.env.example` to
`backend/.env` only when that destination does not exist.

## Run

First PowerShell window:

```powershell
Set-Location C:\Users\iqran\OneDrive\Desktop\DeepTrace-AI
.\scripts\dev.ps1 migrate
.\scripts\dev.ps1 backend
```

Second PowerShell window:

```powershell
Set-Location C:\Users\iqran\OneDrive\Desktop\DeepTrace-AI
.\scripts\dev.ps1 frontend
```

Open http://127.0.0.1:5173. Stop each server with Ctrl+C.
The Vite server proxies `/api` to http://127.0.0.1:8000.
Health: `/api/health`; readiness: `/api/ready`; capabilities:
`/api/capabilities`; schemas: `/api/openapi.json`.

If script execution is restricted by your organization's policy, use these
commands directly instead of changing the policy:

```powershell
# Backend window, from repository root
Set-Location backend
.\.venv\Scripts\python.exe -m deeptrace migrate
.\.venv\Scripts\python.exe -m deeptrace serve
# Frontend window, from repository root
Set-Location frontend
npm.cmd run dev
```

Ports 8000 and 5173 must be available. Keep the defaults for this development
workflow; a backend port change also requires updating the Vite proxy. Both
servers bind loopback. Do not expose them on a LAN.

## Local data and migrations

Default database: `%LOCALAPPDATA%\DeepTraceAI\deeptrace.sqlite3`, outside the
OneDrive checkout. An absolute `DEEPTRACE_DATA_DIR` override is available for
tests and development. Avoid synced/shared directories: their backup or sync
services may copy data outside the machine. User-profile filesystem permissions
are inherited; the database is not encrypted.

Startup and the `migrate` command both apply/verify numbered migrations.
Migration 001 creates `settings` and `investigations`; the runner creates
`schema_meta`. Migration 002 adds optional descriptions and manual `plans` /
`plan_items`. Existing migration 001 and records are preserved. No seed records
are inserted. Investigations remain drafts, identified by UUIDs with UTC
ISO-8601 timestamps. Readiness requires the current migration version.

Each connection enables foreign keys and a 5-second busy timeout. WAL is enabled
and verified during migration. `BEGIN IMMEDIATE` serializes migrations/writes;
errors roll back the migration and version record together. SQL files use LF
line endings so checksums survive Git checkout on Windows. Historical checksums,
noncontiguous history and newer schemas are rejected; no automatic reset occurs.

Before an upgrade of an existing versioned database, SQLite's backup API saves
a timestamped snapshot in the data directory's `backups` folder. Backups remain
until deliberately removed by the owner. A failed upgrade retains its backup
and rolls back SQL. Stop the app before any manual recovery; preserve the original
database and sidecars, inspect the failure, and restore a verified backup with
owner approval. Do not delete data or edit old migration checksums to bypass an error.

## Checks

```powershell
.\scripts\check.ps1
```

This runs the secret scan, Ruff lint/format, mypy, pytest with coverage (85% minimum), ESLint,
TypeScript, Vitest, production build and Edge browser tests. Do not redirect its output in
Windows PowerShell 5.1. Individual commands are in `TESTING.md`.

The same checks run on GitHub on every pull request and push to `main`
(`.github/workflows/ci.yml`), along with a full-history secret scan, the license audit and
a production-only install (`scripts/production_smoke.py`). CI uses no API keys.
Browser tests require Microsoft Edge installed, use a unique synthetic fixture directory per invocation under
`frontend/.cache`, and start/stop their own loopback servers. Close development
servers first. Test databases never use the normal application data directory.

## Scope and privacy

Create an investigation from the Dashboard, enter its title and research question,
then save. In its workspace, edit details and build a manual plan of up to eight
steps. Move up/down controls reorder steps; Save plan persists the complete plan.
Reopen an investigation with Continue editing. Saved work survives refresh.
Details and plans have separate Save buttons. Unsaved edits remain in memory on
failure; leaving or refreshing asks for confirmation. Do not discard them during
conflict recovery until you have copied anything needed. Reload the saved version
and reapply edits deliberately; automatic conflict merging is not provided.

Mock mode uses simulated providers and synthetic pages only; nothing it produces is real
research. Analytics, remote fonts and a PDF pipeline are not included. Live providers are
opt-in (see M1 research below). Deletion is permanent and needs the exact title; upgrade
backups in the data folder and files you downloaded are not affected.

Workspace writes require an allowed Origin, Host, JSON content type and a valid
X-DeepTrace-Token header. The frontend obtains a process-local token from
/api/session into transient memory before saving. Tokens are never stored in browser
storage, URLs or application logs; responses use no-store. Restarting the backend
invalidates old tokens; retry fetches a new token. Reads without Origin still
support CLI health checks; explicit origins must match the existing local allowlist.
Loopback/token protection is not authentication against malicious software already
running under the same operating-system account. Credential endpoints are write-only and
keep keys in Windows Credential Manager, never in the database. Other software running under
your account can read that store.

The production frontend build is validated, but a packaged single-origin release
server/installer remains deferred. Use the documented two-server development workflow.

## Phase 3 synthetic evidence workflow

Migration 003 adds collection runs, checkpoints, events, source snapshots,
passages and reserved provider/consent bookkeeping. Migrations 001 and 002 are
unchanged. Upgrade backups and atomic rollback behavior described above apply.
Only one application process may own a data directory; a second process fails
startup rather than interrupting the first worker. Interrupted queued/running
runs are marked interrupted on restart and are never automatically replayed.

In mock mode, open an investigation and scroll to Evidence workspace. Read the
synthetic disclosure, check its acknowledgement, and select **Enable synthetic
collection**. Use `https://fixture.example/article` (or `/second`) to collect
application-owned sample text. `/failure` and `/blocked` demonstrate failures.
These reserved example URLs are matched locally: no DNS, website or provider is
contacted. Inspect saved sources for hashes, timestamps, exact text and passages.
History and saved text survive restart. Revocation stops collection and retains
previously saved evidence. No real evidence or final answers are produced.

`DEEPTRACE_MODE=offline` disables collection while allowing saved evidence reads.
There is no setting or credential that activates live collection. Existing
fixture consent cannot authorize future live networking. Live functionality
requires a separate approved implementation and security validation.

Limits: 15 URLs/run, one active run/application, 25 items/page, up to 100 passages
per source, 1 MB UTF-8 parser input and 200,000 normalized text characters. Failed
or partial extraction is labelled. Default live transport rejects all operations.
Do not interpret mock policy tests as verification of real DNS/TLS behavior.

### Saved URLs (Phase 3)

In the Evidence workspace, **Saved URLs (not retrieved)** records a public
http(s) address and an optional note. Nothing is fetched; saved URLs are not
sources, evidence or citations. Private, loopback and credentialed URLs are
refused. Migration 004 adds this table. It works in offline mode too.

## Phase 4 evidence review and reports

Migration 005 adds evidence reviews, the report draft, claims, citations and
immutable report versions (backup and single-transaction rollback apply as above).
Open an investigation and select **Report** in the Investigation navigation:

1. **Evidence review:** link each saved passage to the question or a plan step
   and record your own classification and note.
2. **Report draft:** write the sections and claims. Add citations to saved
   passages with an optional exact quotation, then select **Save draft**. Invalid
   citations (unknown passage or non-matching quotation) are rejected with a
   reason, and your edits stay on screen.
3. **Report versions:** **Create report version** re-checks citations and stores
   an immutable Markdown snapshot. Preview shows the exact file;
   **Download Markdown (.md)** saves it through the browser.

No model writes or judges anything. "Cited" means only that a valid supporting
citation exists; it does not mean the source supports the claim.

## M1 research

Open an investigation, generate or write a plan, review the limits and select **Start research**.
In mock mode, first enable synthetic collection in the Evidence workspace; no account is needed
and nothing leaves this computer. Migration 006 applies automatically, with the same backup and
rollback behaviour. Application logs rotate at about 1 MB under `logs` in the data folder (four
files at most) and hold fixed events only. Set `DEEPTRACE_STORAGE_WARNING_MB` to change the
500 MB per-investigation warning. Live research is opt-in: follow the procedure in
[M1_HANDOFF.md](M1_HANDOFF.md), and never put API keys in `backend/.env`.
