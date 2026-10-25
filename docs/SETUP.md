# Windows setup — Phase 2

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

This runs Ruff lint/format, mypy, pytest, ESLint, TypeScript, Vitest, production
build and Edge browser tests. Individual commands are in `TESTING.md`.
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

Mock means providers are disabled; manual plans are not AI results. No credentials,
hosted calls, web fetch, analytics, remote fonts, PDF pipeline or reports are included.
Investigation deletion and archive are unavailable.

Workspace writes require an allowed Origin, Host, JSON content type and a valid
X-DeepTrace-Token header. The frontend obtains a process-local token from
/api/session into transient memory before saving. Tokens are never stored in browser
storage, URLs or application logs; responses use no-store. Restarting the backend
invalidates old tokens; retry fetches a new token. Reads without Origin still
support CLI health checks; explicit origins must match the existing local allowlist.
Loopback/token protection is not authentication against malicious software already
running under the same operating-system account. No credential endpoints exist.

The production frontend build is validated, but a packaged single-origin release
server/installer remains deferred. Use the documented two-server development workflow.
