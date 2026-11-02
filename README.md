# DeepTrace AI

A local-first research workspace. You ask a question, DeepTrace plans bounded
research, saves exactly what each source said, drafts a cited answer, and produces
a versioned Markdown report you can check claim by claim.

## Status

Milestone 1 (the first working vertical slice) is complete **in mock mode**, which is
the default. It runs on simulated providers and synthetic sample pages, so nothing
leaves your computer and nothing it produces is real research.

Live research through Tavily, Gemini and public websites is built and opt-in, but it
**has not yet been run against the real services**. See [M1 handoff](docs/M1_HANDOFF.md)
for the procedure, known limitations and differences from the specifications.

PDFs and semantic search (M2), automated support assessment and resuming runs (M3),
and release hardening (M4) are not built yet.

## What works today

- Create, edit, search, archive and delete investigations.
- Write a research plan, or generate one and edit it.
- See and adjust run limits, then start, follow and cancel research.
- Findings marked **Cited** or **Not established**. Invalid citations are suppressed.
- Open any citation to see the saved passage, its source and what was checked.
- Download immutable Markdown reports, including a labelled partial report when a
  run hits a limit.
- Write your own evidence reviews and citation-checked reports.

A valid citation shows that a passage exists and any quotation matches it. It does
not show that the passage supports the claim.

## Technology

| Area | Choice |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Backend | Python 3.14, FastAPI |
| Storage | SQLite (WAL, checksummed migrations) |
| Text extraction | Beautiful Soup with Python's `html.parser` |
| Live search and model (opt-in) | Tavily and Gemini, using your own free-tier keys |
| Tests | Pytest, Vitest, Playwright with Microsoft Edge |

Planned for M2: `pypdf` and `pypdfium2` for PDFs, local FastEmbed embeddings, and
exact vector search with SQLite and NumPy.

## Documentation

- [Windows setup](docs/SETUP.md)
- [Validation results](docs/TESTING.md)
- [Dependency licenses and notices](docs/DEPENDENCY_LICENSES.md)
- Handoffs: [M1](docs/M1_HANDOFF.md), [Phase 4](docs/PHASE4_HANDOFF.md),
  [Phase 3](docs/PHASE3_HANDOFF.md), [Phase 2](docs/PHASE2_HANDOFF.md),
  [Phase 1](docs/PHASE1_HANDOFF.md)
- Specifications: [PRD](PRD.md), [Design](docs/DESIGN.md),
  [Integrations](docs/INTEGRATIONS.md), [Architecture](docs/ARCHITECTURE.md),
  [Database](docs/DATABASE.md)

The handoffs and test records describe each phase as it stood at the time; the latest
one takes precedence. The application is licensed under Apache-2.0.
