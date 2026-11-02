# DeepTrace AI

An agentic AI research platform for multi-source investigation,
document intelligence, retrieval-augmented generation (RAG),
and evidence-backed reporting.

## Status

Phase 3 adds synthetic evidence collection, persistent run history, immutable
source snapshots, provenance-aware passages and saved (never retrieved) URLs.
Phase 4 adds user-authored evidence review, citation-checked report drafts and
immutable, downloadable Markdown report versions. No AI model is used.
M1 adds a bounded research pipeline with generated plans, cited answers and reports. It works
fully in mock mode. Live Tavily, Gemini and web retrieval are opt-in and have not yet been
exercised against real services. See [M1 handoff](docs/M1_HANDOFF.md).

## Planned Technology Stack

- Frontend: React, TypeScript, Vite, Tailwind CSS
- Backend: Python, FastAPI
- AI Orchestration: LangGraph
- Document Processing: PyMuPDF
- Vector Database: ChromaDB
- Database: SQLite
- Testing: Pytest, Vitest

## Local workspace

The local, mock/offline application implements a responsive Chart Room shell,
investigation creation/search/editing and manual plans with up to eight ordered
steps. SQLite persists saved work; stale updates are rejected without overwriting
newer changes. The existing health/readiness API remains available.
Mock collection uses application-owned fixtures only; offline mode permits saved
evidence reads. No real website or provider is contacted.

See [Windows setup](docs/SETUP.md), [validation](docs/TESTING.md), and
[dependency licenses and notices](docs/DEPENDENCY_LICENSES.md).
See [Phase 3 handoff](docs/PHASE3_HANDOFF.md) and [Phase 4 handoff](docs/PHASE4_HANDOFF.md)
for API contracts, recorded spec deviations, validation and limitations.

The original planned-stack list above predates the approved integration and
architecture decisions: LangGraph is deferred; future PDF processing uses
pypdf/pypdfium2 and future vectors use SQLite/NumPy. None is installed in Phase 1.
The five specifications remain unchanged.
