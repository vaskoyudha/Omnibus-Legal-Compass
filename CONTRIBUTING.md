# Contributing to Omnibus Legal Compass

Thank you for your interest in contributing! This guide will help you get started.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Architecture](#project-architecture)
- [Coding Standards](#coding-standards)
- [Commit Conventions](#commit-conventions)
- [Pull Request Process](#pull-request-process)
- [Testing](#testing)
- [Good First Issues](#good-first-issues)

## Code of Conduct

This project follows our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold a welcoming, respectful environment.

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Omnibus-Legal-Compass.git
   cd "Omnibus-Legal-Compass"
   ```
3. **Add upstream** remote:
   ```bash
   git remote add upstream https://github.com/vaskoyudha/Omnibus-Legal-Compass.git
   ```
4. **Create a branch** for your work:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for Qdrant vector database)
- Git

### Backend

```bash
# Create and activate virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Start Qdrant
docker run -d --name omnibus-qdrant \
  -p 6333:6333 -p 6334:6334 \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant:latest

# Set environment variables
cp .env.example .env
# Edit .env with your NVIDIA_API_KEY

# Ingest sample data
cd backend && python scripts/ingest.py

# Start backend server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

### Running Tests

```bash
# Backend tests (401 tests)
python -m pytest tests/test_api.py tests/test_api_versioning.py \
  tests/test_chat.py tests/test_rag_chain.py tests/test_retriever_unit.py \
  tests/test_rate_limit.py tests/test_knowledge_graph.py \
  tests/test_knowledge_graph_ingest.py tests/test_graph_api.py \
  tests/test_dashboard.py tests/test_corpus.py \
  tests/test_eval_embeddings.py tests/test_external_service_failures.py \
  -v --tb=short

# Backend with coverage
python -m pytest tests/test_api.py tests/test_api_versioning.py \
  tests/test_chat.py tests/test_rag_chain.py tests/test_retriever_unit.py \
  tests/test_rate_limit.py tests/test_knowledge_graph.py \
  tests/test_knowledge_graph_ingest.py tests/test_graph_api.py \
  tests/test_dashboard.py tests/test_corpus.py \
  tests/test_eval_embeddings.py tests/test_external_service_failures.py \
  --cov=backend --cov-report=term-missing

# Frontend tests
cd frontend && npm test
```

> **Note**: Do NOT run `pytest tests/` without excluding `test_retriever.py` — it contains live Qdrant integration tests that require a running Qdrant instance.

## Project Architecture

```
backend/
├── main.py              # FastAPI app with all routes
├── rag_chain.py         # RAG pipeline (NVIDIA NIM + LangChain)
├── retriever.py         # Hybrid search (BM25 + dense + reranking)
├── chat/session.py      # Multi-turn session manager
├── knowledge_graph/     # Legal knowledge graph (NetworkX)
└── dashboard/           # Coverage computation
frontend/
├── src/app/             # Next.js pages (6 pages)
├── src/components/      # React components
└── src/lib/api.ts       # API client
tests/                   # 401 backend tests
docs/                    # VitePress documentation
```

For detailed architecture documentation, see our [Architecture Guide](https://vaskoyudha.github.io/Omnibus-Legal-Compass/architecture).

## Coding Standards

### Python (Backend)

- **Formatter**: Follow existing code style (consistent with ruff)
- **Type hints**: Use type hints on all function signatures
- **No type suppression**: Never use `# type: ignore`, `# pyright: ignore`, or `typing.cast(Any, ...)`
- **Docstrings**: Add docstrings to public functions and classes
- **Async**: Use `async`/`await` for I/O operations
- **Error handling**: Never use empty `except` blocks. Always handle specific exceptions.

### TypeScript (Frontend)

- **Strict mode**: TypeScript strict mode is enabled
- **No `any`**: Avoid `any` type — use proper interfaces
- **Components**: Functional components with hooks
- **Styling**: Tailwind CSS utility classes. Follow existing dark theme patterns.
- **State**: Use React hooks (`useState`, `useEffect`). No external state libraries unless justified.

### General

- Keep changes focused — one feature or fix per PR
- Don't mix refactoring with feature work
- Preserve existing UI design and colors (dark theme with `#AAFF00` accent)
- All new backend endpoints must be under `/api/v1/`

## Commit Conventions

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <description>

[optional body]
```

### Types

| Type | Usage |
|------|-------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `test` | Adding or updating tests |
| `refactor` | Code refactoring (no behavior change) |
| `style` | Formatting, whitespace (no code change) |
| `chore` | Build process, dependencies, CI |
| `perf` | Performance improvements |

### Examples

```
feat: add document upload to knowledge graph ingestion
fix: correct streaming response chunking for long answers
docs: add deployment guide for Docker Compose
test: add edge case tests for compliance checker
```

## Pull Request Process

1. **Sync** your branch with upstream main:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run tests** and ensure they pass:
   ```bash
   python -m pytest tests/test_api.py tests/test_api_versioning.py \
     tests/test_chat.py tests/test_rag_chain.py tests/test_retriever_unit.py \
     tests/test_rate_limit.py tests/test_knowledge_graph.py \
     tests/test_knowledge_graph_ingest.py tests/test_graph_api.py \
     tests/test_dashboard.py tests/test_corpus.py \
     tests/test_eval_embeddings.py tests/test_external_service_failures.py \
     -v --tb=short
   ```

3. **Push** your branch and open a PR against `main`

4. **Fill out** the PR template completely:
   - Description of changes
   - Type of change (feature, fix, etc.)
   - Testing performed
   - Screenshots (for UI changes)

5. **Wait for CI** — all checks must pass before merge

6. A maintainer will review your PR. Address feedback promptly.

### PR Checklist

- [ ] Tests pass locally
- [ ] New code has test coverage
- [ ] No type errors or lint warnings introduced
- [ ] Commit messages follow conventions
- [ ] PR description is complete
- [ ] Documentation updated (if applicable)

## Testing

### Writing Tests

- Place backend tests in `tests/` directory
- Name test files `test_<module>.py`
- Use `pytest` fixtures for shared setup
- Mock external services (Qdrant, NVIDIA NIM) — see existing tests for patterns
- Use `TestClient` from `starlette.testclient` for API tests
- Target >80% coverage for new code

### Test Patterns

```python
# API endpoint test example
from starlette.testclient import TestClient
from unittest.mock import patch, AsyncMock

def test_ask_endpoint(test_client):
    """Test the /api/v1/ask endpoint returns expected response."""
    mock_result = {"answer": "Test answer", "citations": []}
    with patch("main.rag_chain") as mock_chain:
        mock_chain.query.return_value = mock_result
        response = test_client.post("/api/v1/ask", json={"question": "Test?"})
    assert response.status_code == 200
    assert "answer" in response.json()
```

### Frontend Tests

```typescript
// Component test example
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Navbar } from '../components/Navbar'

describe('Navbar', () => {
  it('renders navigation links', () => {
    render(<Navbar />)
    expect(screen.getByText('Tanya Jawab')).toBeInTheDocument()
  })
})
```

## Good First Issues

New to the project? Look for issues labeled [`good first issue`](https://github.com/vaskoyudha/Omnibus-Legal-Compass/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22). These are carefully scoped tasks suitable for first-time contributors.

### Suggested Starter Tasks

Here are some areas where contributions are welcome:

1. **Add more legal document samples** — Expand `data/peraturan/` with additional Indonesian regulations
2. **Improve Indonesian language prompts** — Refine LLM prompts for better Bahasa Indonesia output
3. **Add unit tests for edge cases** — Increase test coverage for error paths
4. **Improve accessibility** — Add ARIA labels and keyboard navigation to frontend
5. **Add loading skeletons** — Replace loading spinners with skeleton placeholders
6. **Optimize mobile layout** — Improve responsive design for smaller screens
7. **Add search history** — Let users see their recent questions
8. **Expand knowledge graph schema** — Support additional document types (Perda, Permen)
9. **Add export functionality** — Allow users to export answers as PDF
10. **Improve error messages** — Make API error responses more user-friendly

## Questions?

- Open a [GitHub Issue](https://github.com/vaskoyudha/Omnibus-Legal-Compass/issues/new) for bugs or feature requests
- Check the [Documentation](https://vaskoyudha.github.io/Omnibus-Legal-Compass/) for guides and API reference

Thank you for contributing to Indonesian legal technology!
