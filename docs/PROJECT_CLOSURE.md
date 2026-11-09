# Project closure handoff

Closed 2026-11-09. This document replaces earlier handoffs where they disagree. It records:
- what DeepTrace AI is at closure;
- how it was verified;
- what is known to be wrong or missing;
- what to clean up;
- how to pick the project up again.

## Final state

| Area | State |
|---|---|
| Phases 1–4 | Complete: foundation, investigation workspace and plans, synthetic evidence collection, evidence review and user-authored reports |
| Milestone 1 | Complete: the bounded research pipeline in mock mode, and **run end to end against the real Tavily and Gemini free tiers** |
| Frontend | Redesigned as a premium research workspace (DESIGN.md §6–§8): <br>• sectioned sidebar and a research-mode chip in the header; <br>• Overview (Command Center) with real counts; <br>• Investigations library; <br>• three-panel investigation workspace with an evidence inspector |
| Milestones 2–4 | Not built (see "Not built") |
| CI | GitHub Actions workflow on Windows (`.github/workflows/ci.yml`). It runs on pull requests and on pushes to `main`, and **has not yet run on GitHub** |

### Branches

All work since Phase 2 is on `feature/phase3-evidence-collection` and has been pushed. **`main` stops
at Phase 2** (`17c2bf1`, pull request #2). To make `main` match the closed project:
1. Open a pull request from `feature/phase3-evidence-collection` into `main`. This also triggers
   the first real CI run.
2. Check that CI passes.
3. Merge.

## What the application does

1. **Plan.** Write a plan, or generate one with the model and edit it.
2. **Discover.** Search with Tavily, within the search limit.
3. **Read.**
   - Fetch public pages through policy-checked, address-pinned connections.
   - Follow robots.txt (RFC 9309); in live mode read one page per website.
   - Extract text in a separate process, split it into passages and rank them, with at most
     four passages per source.
4. **Check.**
   - Gemini drafts an answer from at most 12 passages.
   - Code validates every citation: the reference exists, it was allowed for this run, and any
     quotation matches the saved text.
   - Findings are **Cited** or **Not established**; invalid citations are suppressed and counted.
5. **Report.** An immutable, SHA-256-checked Markdown report with the required AI disclaimer,
   the queries used, provider and model, prompt version, source statuses and omissions.

When a run hits a limit or the quota runs out, it still produces a labelled partial report.

Everything is stored locally. API keys are in Windows Credential Manager, never the database.

## Verification at closure

| Check | Result |
|---|---|
| Backend: Ruff, format, mypy | Passed |
| Backend tests with coverage | 326 passed, 92% line and branch coverage (floor 85%) |
| Frontend: ESLint, TypeScript, build | Passed |
| Component tests | 39 passed |
| Microsoft Edge tests (with axe) | 7 passed on the redesign; not rerun after the final two small changes (see TESTING.md) |
| Secret scan | Passed, 148 files |
| First live run (2026-11-09) | 7 cited findings, 9 of 9 quotations matched, 2 invalid citations suppressed |

## Known issues and limits

- **Gemini free tier is often busy.**
  - A later live run failed with `unavailable` after three attempts, once all pages had already
    been read. The run keeps its sources and now explains the failure; start it again later.
  - No fallback model is configured.
- **Model choice matters.** On the owner's free key, `gemini-3.8-flash`, `gemini-3.7-flash` and
  `gemini-flash-latest` never answered. `gemini-3.5-flash` answered in about 3 seconds and is
  the configured model.
- **Temporary DNS failures** on the home network caused some pages to be skipped. The resolver
  waits 5 seconds and retries once.
- **Evidence can lean on a few sources.** Diversity caps help (one page per website in live
  mode, four passages per source), but nothing judges source credibility.
- **No check of whether a passage supports a claim.** Citation validation proves that the
  reference exists and the quotation matches, not that the claim is true. The interface says
  so wherever checks are shown.
- **Not measured:** frontend code coverage, a manual screen-reader audit, a penetration test,
  a CVE scan. Coverage of `parser_process.py` is understated because it runs in a subprocess.
- **Windows only.** Credentials use the Windows Credential Manager, and CI and the browser
  tests run on Windows with Microsoft Edge.

## Not built

These were planned in the PRD and never built:

| Milestone | Scope |
|---|---|
| M2 | PDFs and the user's own documents, local embeddings (FastEmbed), semantic search |
| M3 | Assessing whether a passage supports a claim, resuming interrupted runs, the evidence comparison view, filtering |
| M4 | Release hardening, packaging and an installer |

## Closing checklist (owner)

These steps protect your accounts now that the project is closed.

1. **Revoke the API keys** at the providers:
   - Tavily: the dashboard's API keys page.
   - Gemini: Google AI Studio → API keys.

   Revoking is what actually stops a key from working anywhere.
2. **Remove the local copies** from Windows Credential Manager. Either use Remove in DeepTrace's
   Settings for each provider, or run:
   ```powershell
   cmdkey /delete:DeepTraceAI/tavily
   cmdkey /delete:DeepTraceAI/gemini
   ```
3. **Return to mock mode:** delete the `DEEPTRACE_MODE` and `DEEPTRACE_LLM_MODEL` lines from
   `backend/.env`. The file is git-ignored and never contained keys.
4. **Decide about local data.**
   - Investigations live in `%LOCALAPPDATA%\DeepTraceAI\deeptrace.sqlite3`, together with
     upgrade backups and logs.
   - Keep the folder to preserve your research, or delete it to remove everything.
   - Reports you downloaded are separate files and are not affected.
5. **Optionally merge to `main`** as described under "Branches".

## How to resume

1. Follow [SETUP.md](SETUP.md), then run `.\scripts\check.ps1` with the dev servers stopped.
2. Read, in order:
   - this document;
   - [PRD.md](../PRD.md) §22 (milestones);
   - [ARCHITECTURE.md](ARCHITECTURE.md);
   - [DESIGN.md](DESIGN.md) §6–§10.
3. Start with the recommended next steps:
   1. Merge to `main` and confirm CI passes on GitHub.
   2. Add a fallback when the model is busy: a second free model, or a clear "retry the answer
      only" action that reuses the passages already read.
   3. M3 support assessment: an independent check of whether each passage supports its claim,
      shown separately from the deterministic checks.
   4. M2 documents: PDF extraction and local semantic search.
   5. Source credibility and diversity signals in the Sources tab.
   6. Packaging (M4).

## Where things are

| Path | Contents |
|---|---|
| `backend/src/deeptrace/research/` | Pipeline, gateway, providers, prompts (`synthesize-v2`), credentials |
| `backend/src/deeptrace/collection/` | URL policy, pinned transport, fetcher and robots.txt, extraction |
| `backend/src/deeptrace/storage/` | SQLite repositories and migrations 001–006 |
| `frontend/src/features/workspace/` | Three-panel workspace, shared research state, evidence inspector |
| `frontend/src/features/overview/` | Command Center |
| `frontend/e2e/` | Microsoft Edge journeys with axe checks |
| `scripts/` | `check.ps1`, `dev.ps1`, secret scan, dependency license audit, production smoke test |
