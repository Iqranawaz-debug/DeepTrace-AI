# Phase 1 handoff

Implemented and validated locally; not a complete research engine or MVP.

## Implemented

- React/TypeScript/Vite/Tailwind Chart Room shell, responsive sidebar/rail/mobile
  dialog, focus/skip-link support, local fonts, honest empty dashboard and Settings.
- Typed local health client, loading/error/retry states and mock/offline notice.
- FastAPI `/api/health`, `/api/ready`, `/api/capabilities` and OpenAPI schema.
- Typed local-only configuration, explicit CORS/Host/Origin checks, read-only API,
  safe structured request logs and non-leaking errors.
- SDK-independent provider extension points and unconditional outbound denial.
- SQLite `schema_meta`, `settings`, `investigations`; no fake production records.
  Checksummed migrations, WAL, foreign keys, busy timeout, rollback and upgrade backup.
- Locked dependency environments, Apache-2.0 application license, local font
  licenses, approved MPL exception record and generated third-party notices.
- PowerShell development/check helpers and backend/component/browser tests.

## Deferred and limitations

Investigation CRUD, research planning/execution, live Gemini/Tavily, credential
storage, consent onboarding, SSRF-safe live fetching, evidence/citations/reports,
PDF processing, embeddings, semantic assessment, worker recovery and packaged
single-origin release are deferred. Provider mode cannot enable network calls.

The SQLite database is not encrypted and inherits user-profile permissions.
Loopback is not authentication against malicious software running as the same
user. State-changing endpoints are rejected; future writes need a reviewed
CSRF/session protection strategy. Console logs do not persist to a rotating file.
No claim of full WCAG compliance, universal security, or complete vulnerability
coverage is made. See `TESTING.md` for exact results and remaining checks.

## Start on Windows

Full installation and migration explanation: `SETUP.md`.
From repository root, in separate PowerShell windows:

```powershell
.\scripts\dev.ps1 migrate
.\scripts\dev.ps1 backend
```

```powershell
.\scripts\dev.ps1 frontend
```

Open http://127.0.0.1:5173. Backend: http://127.0.0.1:8000/api/health.
Default data location: `%LOCALAPPDATA%\DeepTraceAI\deeptrace.sqlite3`.

## Git handoff

Branch: `feature/phase1-foundation`, based on `52a8540`.
No commit, push, merge or pull request was performed. The five specifications
are unchanged. Only `.gitignore` and README were modified among existing files;
all other implementation files below are new. Dependencies, virtual environments,
databases, caches, build output and screenshots are ignored.

Suggested commit message (not committed):
`feat: establish local-first Phase 1 foundation`

## Complete changed-file inventory

Inventory paths are repository-relative; generated build/cache outputs are excluded.

- `.env.example`
- `.gitattributes`
- `.gitignore`
- `LICENSE`
- `README.md`
- `backend/pyproject.toml`
- `backend/src/deeptrace/__init__.py`
- `backend/src/deeptrace/__main__.py`
- `backend/src/deeptrace/config.py`
- `backend/src/deeptrace/main.py`
- `backend/src/deeptrace/providers.py`
- `backend/src/deeptrace/storage/__init__.py`
- `backend/src/deeptrace/storage/database.py`
- `backend/src/deeptrace/storage/migrations/001_foundation.sql`
- `backend/tests/conftest.py`
- `backend/tests/test_api.py`
- `backend/tests/test_database.py`
- `backend/uv.lock`
- `docs/DEPENDENCY_LICENSES.md`
- `docs/PHASE1_HANDOFF.md`
- `docs/SETUP.md`
- `docs/TESTING.md`
- `docs/THIRD_PARTY_NOTICES.txt`
- `docs/dependency-inventory.json`
- `docs/licenses/react-remove-scroll-bar-2.3.8.txt`
- `frontend/e2e/foundation.spec.ts`
- `frontend/eslint.config.js`
- `frontend/index.html`
- `frontend/package-lock.json`
- `frontend/package.json`
- `frontend/playwright.config.ts`
- `frontend/public/THIRD_PARTY_NOTICES.txt`
- `frontend/public/fonts/ibm-plex-mono-LICENSE.txt`
- `frontend/public/fonts/ibm-plex-sans-LICENSE.txt`
- `frontend/public/fonts/source-serif-4-LICENSE.txt`
- `frontend/src/api/client.ts`
- `frontend/src/app/App.tsx`
- `frontend/src/components/States.tsx`
- `frontend/src/main.tsx`
- `frontend/src/styles/app.css`
- `frontend/src/styles/fonts.css`
- `frontend/src/styles/tokens.css`
- `frontend/src/test/App.test.tsx`
- `frontend/src/test/setup.ts`
- `frontend/tsconfig.json`
- `frontend/vite.config.ts`
- `scripts/audit_dependencies.py`
- `scripts/check.ps1`
- `scripts/dev.ps1`
