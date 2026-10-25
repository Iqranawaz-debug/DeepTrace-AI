# DeepTrace AI

An agentic AI research platform for multi-source investigation,
document intelligence, retrieval-augmented generation (RAG),
and evidence-backed reporting.

## Status

Project initialization completed. Development will proceed in phases.

## Planned Technology Stack

- Frontend: React, TypeScript, Vite, Tailwind CSS
- Backend: Python, FastAPI
- AI Orchestration: LangGraph
- Document Processing: PyMuPDF
- Vector Database: ChromaDB
- Database: SQLite
- Testing: Pytest, Vitest

## Phase 1 foundation

The local, mock/offline foundation implements a responsive Chart Room shell,
read-only health/readiness API, and minimal checksummed SQLite migrations.
Research execution and external provider integrations are unavailable.

See [Windows setup](docs/SETUP.md), [validation](docs/TESTING.md), and
[dependency licenses and notices](docs/DEPENDENCY_LICENSES.md).

The original planned-stack list above predates the approved integration and
architecture decisions: LangGraph is deferred; future PDF processing uses
pypdf/pypdfium2 and future vectors use SQLite/NumPy. None is installed in Phase 1.
The five specifications remain unchanged.
