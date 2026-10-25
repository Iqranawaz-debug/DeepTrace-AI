# Phase 1 validation

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
