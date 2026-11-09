# DeepTrace AI

A local-first research workspace you can trace. Ask a question and DeepTrace:

1. plans bounded research;
2. saves exactly what each source said;
3. drafts an answer in which every finding cites a saved passage;
4. checks those citations with deterministic code;
5. produces a versioned Markdown report you can verify claim by claim.

Your investigations stay on your computer.

> **Project status: closed (2026-11-09).** Milestone 1 is complete and has been run end to
> end against the real Tavily and Gemini free tiers. The project is not being developed further.
> See the [closure handoff](docs/PROJECT_CLOSURE.md) for the final state, known issues and how
> to pick it up again.

## The problem

AI research assistants are fast but hard to trust:
- They cite sources that don't contain the quoted words.
- They mix opinion with evidence.
- They rarely say what they couldn't find.
- They usually send your questions and documents off your machine.

## How DeepTrace answers it

- **Bounded pipeline.** Plan → Discover → Read → Check → Report, with hard limits on
  searches, pages, workflow steps, tokens and minutes. Hitting a limit stops the run as
  "Budget reached" and keeps what it found.
- **Citations checked by code, not by a model.** A finding is **Cited** only if its passage:
  - exists in this investigation's saved sources;
  - came from the passages the model was allowed to use;
  - contains any quotation the model presented, matched against the saved text.

  Otherwise the finding is **Not established**. Citations that fail are suppressed and counted.
- **Honest limits.** The interface says plainly that a valid citation shows the source says
  those words, not that the claim is true.
- **Honest failures.** When a run fails it says why. Partial reports are labelled.
- **Evidence inspector.** Open any citation to see:
  - the saved passage with the quotation highlighted;
  - a link to the original page;
  - the three automatic checks;
  - every finding that cites it.
- **Local and private by design.**
  - Data lives in SQLite on your computer.
  - API keys go to Windows Credential Manager, never the database.
  - Mock mode is the default; live mode needs local configuration, your own keys and
    explicit consent for each provider.
  - A "sensitive" flag stops an investigation's question and passages from ever reaching a
    hosted model.
- **Careful web access.**
  - robots.txt is followed (RFC 9309).
  - Requests to private or internal addresses are refused.
  - Connections go only to the address that passed those checks, with certificate checks.
  - Redirects and proxies are never followed.
  - The model has no tools and never chooses a URL.

## What works

- **Investigations:** create, edit, search, archive and delete them (deleting needs the exact
  title). The Overview shows real totals, investigations to continue and recent activity.
- **Investigation workspace** in three panels:
  - an outline with the question, plan and run tracker;
  - Plan, Findings, Sources, Evidence and Report tabs;
  - the evidence inspector.
- **Plans:** write your own, or generate one and edit it.
- **Runs:** adjust run limits, start research, follow live progress and an activity log,
  and cancel.
- **Reports:** download immutable, SHA-256-checked Markdown reports, including partial ones.
- **Your own work:** write evidence reviews and your own citation-checked report drafts and
  versions.

**First live run:** 7 cited findings, 9 of 9 quotations matched, and 2 invalid citations
caught and suppressed.

## Quick start (Windows)

Requirements: Python 3.14 with [uv](https://docs.astral.sh/uv/), Node.js 24, Microsoft Edge.
Full instructions are in [SETUP.md](docs/SETUP.md).

```powershell
# Backend (first window)
cd backend
uv sync --frozen
.\.venv\Scripts\python.exe -m deeptrace migrate
.\.venv\Scripts\python.exe -m deeptrace serve

# Frontend (second window)
cd frontend
npm.cmd ci --ignore-scripts
npm.cmd run dev
```

Open http://127.0.0.1:5173. Mock mode works immediately and sends nothing anywhere.

For live research:
1. Put `DEEPTRACE_MODE=live_free` and `DEEPTRACE_LLM_MODEL=gemini-3.5-flash` in
   `backend/.env`. **Never put keys there.**
2. Restart the backend.
3. Add your free-tier Tavily and Gemini keys in **Settings** and accept each disclosure.

## Checks

```powershell
.\scripts\check.ps1
```

This runs:
- the secret scan;
- Ruff, mypy and the backend tests with a coverage floor of 85% (last measured at 92%);
- ESLint, the TypeScript check, the frontend tests and the build;
- the Microsoft Edge tests with axe accessibility checks.

Stop the dev servers first, because the browser tests use ports 5173 and 8000.
GitHub Actions runs the same checks on Windows.

## Technology

| Area | Choice |
|---|---|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, Radix UI, lucide icons |
| Backend | Python 3.14, FastAPI, Pydantic |
| Storage | SQLite (WAL, checksummed migrations with automatic backups) |
| Text extraction | Beautiful Soup with Python's `html.parser`, in a separate process |
| Live search and model (opt-in) | Tavily and Gemini, using your own free-tier keys |
| Tests | Pytest, Coverage.py, Vitest, Playwright with Microsoft Edge, axe-core |
| Automation | GitHub Actions on Windows: tests, coverage, secret scan, license audit |

## Not built

These were planned but never built:

| Milestone | Scope |
|---|---|
| M2 | PDFs and your own documents, local embeddings and semantic search |
| M3 | Automatic assessment of whether a passage supports a claim, resuming interrupted runs, the evidence comparison view |
| M4 | Release hardening and packaging |

## Documentation

- [Project closure handoff](docs/PROJECT_CLOSURE.md): final state, known issues, how to resume
- [Windows setup](docs/SETUP.md) and [validation results](docs/TESTING.md)
- Specifications:
  - [PRD](PRD.md)
  - [Design](docs/DESIGN.md)
  - [Architecture](docs/ARCHITECTURE.md)
  - [Integrations](docs/INTEGRATIONS.md)
  - [Database](docs/DATABASE.md)
- Earlier handoffs:
  - [M1](docs/M1_HANDOFF.md)
  - [Phase 4](docs/PHASE4_HANDOFF.md)
  - [Phase 3](docs/PHASE3_HANDOFF.md)
  - [Phase 2](docs/PHASE2_HANDOFF.md)
  - [Phase 1](docs/PHASE1_HANDOFF.md)
- [Dependency licenses and notices](docs/DEPENDENCY_LICENSES.md)

Handoffs describe each phase as it stood at the time. The closure handoff takes precedence.

## License

Apache-2.0. See [LICENSE](LICENSE).
