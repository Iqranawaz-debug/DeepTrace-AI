# DeepTrace AI

An agentic AI research platform for multi-source investigation,
document intelligence, retrieval-augmented generation (RAG),
and evidence-backed reporting.

## Status

Phase 2 provides a local investigation workspace and manual research planning.
Research execution and external integrations remain disabled.

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
Research execution and external provider integrations are unavailable.

See [Windows setup](docs/SETUP.md), [validation](docs/TESTING.md), and
[dependency licenses and notices](docs/DEPENDENCY_LICENSES.md).
See [Phase 2 handoff](docs/PHASE2_HANDOFF.md) for API contracts and limitations.

The original planned-stack list above predates the approved integration and
architecture decisions: LangGraph is deferred; future PDF processing uses
pypdf/pypdfium2 and future vectors use SQLite/NumPy. None is installed in Phase 1.
The five specifications remain unchanged.
