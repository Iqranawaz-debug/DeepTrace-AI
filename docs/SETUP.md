# Phase 1 Windows setup

Verified environment: Windows, PowerShell 7.6.5, Python 3.14.3, SQLite 3.50.4,
Node 24.21.0, npm 11.19.0 and uv 0.13.4. Python 3.14 is the supported backend
interpreter for this foundation. Runtime dependencies are recorded in `backend/uv.lock`;
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
`schema_meta`. No seed investigations are inserted. Phase 1 accepts only
draft investigations and mock/offline mode settings; later states and setting
keys require migrations. The intended future record convention is UUID strings
and UTC ISO-8601 timestamps. No investigation write API exists yet.

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
Browser tests require Microsoft Edge installed, use temporary fixture data under
`frontend/.cache`, and start/stop their own loopback servers. Close development
servers first. Test databases never use the normal application data directory.

## Scope and privacy

Phase 1 provides a dashboard empty state and informational Settings screen.
Mock means providers are disabled; no simulated research engine or results exist.
No credential-entry endpoint, hosted model call, web fetch, analytics, remote
font, PDF pipeline, report generator or investigation CRUD workflow is included.

All API methods that could mutate data are rejected. Reads without Origin support
CLI health checks; reads with an Origin must match the explicit local allowlist.
Host values are restricted. Loopback is not authentication: malicious software
running as the same OS user can access local files. A CSRF/session strategy must
be implemented and tested before future write/credential endpoints are enabled.

The production frontend build is validated, but a packaged single-origin release
server/installer remains deferred. Use the documented two-server development workflow.
