# Omnibus Legal Compass - Indonesian Legal RAG System

## TL;DR

> **Quick Summary**: Build a production-ready RAG system for Indonesian legal documents that answers questions with proper citations, checks business compliance, and guides users through regulatory requirements.
> 
> **Deliverables**:
> - Python backend (FastAPI) with LangChain RAG pipeline
> - Next.js frontend with Q&A, Compliance Checker, and Form Guidance
> - Qdrant vector database populated with 541,445 legal document segments
> - NVIDIA NIM integration (Kimi 2.5 LLM + NIM Embeddings)
> 
> **Estimated Effort**: Large (3-4 weeks for full suite)
> **Parallel Execution**: YES - 4 waves
> **Critical Path**: Task 1 → Task 3 → Task 5 → Task 8 → Task 12

---

## Context

### Original Request
> "A RAG (Retrieval-Augmented Generation) system specifically tuned for Bahasa Indonesia Hukum (Legal Indonesian). The AI doesn't just answer. It provides Citations."

User wants to help business owners and students navigate Indonesian bureaucracy (UU Cipta Kerja, Perda vs National UU complexity).

### Interview Summary
**Key Discussions**:
- **Data Source**: Using Open-Technology-Foundation/peraturan.go.id (5,817 docs, 541,445 segments) instead of scraping JDIHN
- **LLM**: NVIDIA NIM with Kimi 2.5 (FREE tier) - user explicitly chose this
- **Embeddings**: NVIDIA NIM Embeddings for consistency
- **Features**: Full Suite MVP (Q&A + Citations + Compliance Checker + Form Guidance)
- **Auth**: Public access (no login required)
- **Testing**: TDD approach

**Research Findings**:
- `langchain-nvidia-ai-endpoints` package provides seamless NVIDIA NIM + LangChain integration
- Hybrid search (BM25 + dense vectors) is critical for legal terminology precision
- JohnAmadeo/indolaw provides reference patterns for Pasal/Ayat structure parsing
- Academic research confirms RAG approach works for Indonesian legal domain (ITK 2025 paper)

### Gap Analysis (Self-Identified)
| Gap | Resolution |
|-----|------------|
| NVIDIA NIM API key setup | Task 1 includes explicit API key configuration |
| peraturan.go.id data format unknown | Task 2 includes data exploration step |
| Qdrant hybrid search configuration | Task 4 includes BM25 + dense setup |
| Citation format undefined | Defaulting to: "Berdasarkan [Jenis] No. [Nomor] Tahun [Tahun], Pasal [X]..." |
| Error handling for "I don't know" | Task 7 includes confidence threshold guardrail |

---

## Work Objectives

### Core Objective
Build a production-ready Indonesian Legal RAG system that provides accurate legal answers with verifiable citations, checks business compliance, and guides users through regulatory requirements.

### Concrete Deliverables
1. `/backend` - Python FastAPI server with LangChain RAG pipeline
2. `/frontend` - Next.js web application with Tailwind CSS
3. `/data` - Processed legal document dataset in Qdrant
4. `/tests` - Comprehensive test suite (pytest + Jest/Vitest)
5. `docker-compose.yml` - Local development stack

### Definition of Done
- [x] User can ask legal question and receive answer with citation
- [x] Citation links to original regulation source
- [x] Compliance Checker accepts text input and PDF upload
- [x] Form Guidance provides step-by-step regulatory guidance
- [ ] All tests pass: `pytest` (backend) + `npm test` (frontend)
- [x] System responds "Saya tidak menemukan informasi spesifik..." when confidence < threshold

### Must Have
- NVIDIA NIM Kimi 2.5 as LLM (user's explicit choice)
- NVIDIA NIM Embeddings for vector similarity
- Qdrant for vector storage with hybrid search
- Citation in every response (format: regulation name + pasal)
- Bahasa Indonesia responses

### Must NOT Have (Guardrails)
- **NO GPT-4o or other paid LLMs** - user chose free NVIDIA NIM tier
- **NO user authentication** - public access only
- **NO mobile app** - web only for MVP
- **NO real-time regulation scraping** - use existing dataset
- **NO English translations** - Bahasa Indonesia only
- **NO over-engineered abstractions** - keep code simple and direct
- **NO hallucinated legal advice** - always cite sources or say "I don't know"

---

## Verification Strategy

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> ALL tasks in this plan MUST be verifiable WITHOUT any human action.
> Every criterion is verified by the agent using tools (Playwright, curl, pytest, etc.).

### Test Decision
- **Infrastructure exists**: NO (greenfield project)
- **Automated tests**: YES (TDD)
- **Backend Framework**: pytest with pytest-asyncio
- **Frontend Framework**: Vitest + Testing Library
- **E2E Framework**: Playwright

### TDD Workflow
Each implementation task follows RED-GREEN-REFACTOR:
1. **RED**: Write failing test first
2. **GREEN**: Implement minimum code to pass
3. **REFACTOR**: Clean up while keeping tests green

### Agent-Executed QA Scenarios
All tasks include specific scenarios verified by:
- **Backend API**: `curl` commands with JSON assertions
- **Frontend UI**: Playwright browser automation
- **Database**: Qdrant API queries

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately):
├── Task 1: Project setup + NVIDIA NIM configuration
└── Task 2: Download and explore peraturan.go.id dataset

Wave 2 (After Wave 1):
├── Task 3: Setup Qdrant + data ingestion pipeline
├── Task 4: Configure hybrid search (BM25 + dense)
└── Task 5: Build core RAG chain with LangChain

Wave 3 (After Wave 2):
├── Task 6: FastAPI endpoints for Q&A
├── Task 7: Citation generation + "I don't know" guardrail
├── Task 8: Next.js project setup + Q&A interface
└── Task 9: Compliance Checker backend (text + PDF)

Wave 4 (After Wave 3):
├── Task 10: Compliance Checker frontend
├── Task 11: Form Guidance feature
└── Task 12: Integration testing + Polish

Critical Path: Task 1 → Task 3 → Task 5 → Task 6 → Task 8 → Task 12
Parallel Speedup: ~50% faster than sequential
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 3, 4, 5 | 2 |
| 2 | None | 3 | 1 |
| 3 | 1, 2 | 4, 5 | None |
| 4 | 3 | 5 | None |
| 5 | 4 | 6, 7 | None |
| 6 | 5 | 8 | 7 |
| 7 | 5 | 8 | 6 |
| 8 | 6, 7 | 10, 11 | 9 |
| 9 | 5 | 10 | 8 |
| 10 | 8, 9 | 12 | 11 |
| 11 | 8 | 12 | 10 |
| 12 | 10, 11 | None | None |

---

## TODOs

### Task 1: Project Setup + NVIDIA NIM Configuration

- [x] 1. Project Setup + NVIDIA NIM Configuration

  **What to do**:
  - Create project directory structure (`/backend`, `/frontend`, `/data`, `/tests`)
  - Initialize Python virtual environment with Poetry or pip
  - Install dependencies: `langchain-nvidia-ai-endpoints`, `langchain`, `qdrant-client`, `fastapi`, `uvicorn`, `pymupdf`, `pytesseract`
  - **Install Tesseract OCR engine** (system-level: `apt install tesseract-ocr` on Linux, `brew install tesseract` on macOS, or download from https://github.com/UB-Mannheim/tesseract/wiki on Windows)
  - Create `.env.example` with required environment variables (NVIDIA_API_KEY)
  - Write test to verify NVIDIA NIM API connection
  - Configure NVIDIA NIM API key (user must provide - get from https://build.nvidia.com/)

  **Must NOT do**:
  - Do NOT install OpenAI or other LLM SDKs
  - Do NOT create complex folder hierarchies

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Standard project setup, well-defined steps
  - **Skills**: [`git-master`]
    - `git-master`: For proper git initialization and .gitignore

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: Tasks 3, 4, 5
  - **Blocked By**: None

  **References**:
  
  **NVIDIA NIM API Configuration** (from user):
  ```python
  # API Endpoint
  invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
  
  # Headers (use env variable for API key)
  headers = {
    "Authorization": f"Bearer {os.getenv('NVIDIA_API_KEY')}",
    "Accept": "text/event-stream"  # for streaming
  }
  
  # Payload structure for Kimi 2.5 with thinking mode
  payload = {
    "model": "moonshotai/kimi-k2.5",
    "messages": [{"role": "user", "content": "Your question here"}],
    "max_tokens": 16384,
    "temperature": 1.00,
    "top_p": 1.00,
    "stream": True,
    "chat_template_kwargs": {"thinking": True},  # Enable thinking mode
  }
  ```
  
  **.env.example content**:
  ```
  NVIDIA_API_KEY=nvapi-YOUR_KEY_HERE
  ```

  **External References**:
  - NVIDIA NIM API Docs: https://build.nvidia.com/moonshotai/kimi-k2.5/modelcard
  - LangChain NVIDIA Integration: https://docs.langchain.com/oss/python/integrations/providers/nvidia
  - LangChain NVIDIA Package: `pip install langchain-nvidia-ai-endpoints`

  **Acceptance Criteria**:

  **TDD Tests**:
  - [x] Test file: `tests/test_config.py`
  - [x] Test: `test_nvidia_nim_connection` - verifies API key works
  - [x] `pytest tests/test_config.py` → PASS

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: NVIDIA NIM API responds to test query
    Tool: Bash (Python script)
    Preconditions: .env file with NVIDIA_API_KEY set
    Steps:
      1. Run: python -c "from langchain_nvidia_ai_endpoints import ChatNVIDIA; llm = ChatNVIDIA(model='moonshotai/kimi-k2.5'); print(llm.invoke('Hello').content[:50])"
      2. Assert: Output contains text (not error)
      3. Assert: Exit code 0
    Expected Result: LLM responds with text
    Evidence: Terminal output captured

  Scenario: Project structure exists
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: ls -la backend/ frontend/ data/ tests/
      2. Assert: All directories exist
      3. Assert: backend/requirements.txt exists
    Expected Result: All directories and core files present
    Evidence: ls output captured
  ```

  **Commit**: YES
  - Message: `feat(setup): initialize project with NVIDIA NIM configuration`
  - Files: `backend/`, `frontend/`, `.env.example`, `requirements.txt`
  - Pre-commit: `pytest tests/test_config.py`

---

### Task 2: Download and Explore peraturan.go.id Dataset

- [x] 2. Download and Explore peraturan.go.id Dataset

  **What to do**:
  - Clone or download Open-Technology-Foundation/peraturan.go.id repository
  - Explore data format (JSON, CSV, or database export?)
  - Document data schema: fields available per segment
  - Create data exploration notebook or script
  - Identify: total documents, total segments, date range, regulation types
  - Create sample subset (~1000 segments) for development

  **Must NOT do**:
  - Do NOT process full dataset yet (Task 3)
  - Do NOT start ingestion without understanding schema

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Data exploration task, straightforward
  - **Skills**: []
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: Task 3
  - **Blocked By**: None

  **References**:
  
  **External References**:
  - GitHub Repo: https://github.com/Open-Technology-Foundation/peraturan.go.id
  - Description: "5,817 dokumen hukum (2001-2025) menjadi 541,445 segmen teks"

  **Acceptance Criteria**:

  **TDD Tests**:
  - [x] Test file: `tests/test_data_loader.py`
  - [x] Test: `test_load_sample_data` - loads sample and returns expected structure
  - [x] `pytest tests/test_data_loader.py` → PASS

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Dataset downloaded and readable
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: ls -la data/peraturan/
      2. Assert: Data files exist
      3. Run: python -c "import json; data = json.load(open('data/peraturan/sample.json')); print(len(data))"
      4. Assert: Output shows count > 0
    Expected Result: Data files accessible and parseable
    Evidence: File listing and count output

  Scenario: Data schema documented
    Tool: Bash
    Preconditions: Data downloaded
    Steps:
      1. Run: cat data/DATA_SCHEMA.md
      2. Assert: File contains field descriptions
      3. Assert: Fields include: jenis_dokumen, nomor, tahun, judul, pasal, ayat
    Expected Result: Schema documentation exists
    Evidence: Schema file content
  ```

  **Commit**: YES
  - Message: `feat(data): add peraturan.go.id dataset with schema documentation`
  - Files: `data/`, `data/DATA_SCHEMA.md`
  - Pre-commit: `pytest tests/test_data_loader.py`

---

### Task 3: Setup Qdrant + Data Ingestion Pipeline

- [x] 3. Setup Qdrant + Data Ingestion Pipeline

  **What to do**:
  - Add Qdrant to docker-compose.yml (or use Qdrant Cloud)
  - Create ingestion script: `backend/scripts/ingest.py`
  - Define collection schema with metadata fields
  - Implement batch ingestion with progress tracking
  - Use NVIDIA NIM Embeddings for vector generation
  - Ingest sample dataset first (~1000 segments)
  - Verify ingestion with count query

  **Must NOT do**:
  - Do NOT ingest full 541K segments in first pass (memory issues)
  - Do NOT skip metadata (jenis_dokumen, nomor, tahun, pasal needed for citations)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Database setup + ingestion pipeline requires careful implementation
  - **Skills**: []
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (sequential after Wave 1)
  - **Blocks**: Tasks 4, 5
  - **Blocked By**: Tasks 1, 2

  **References**:
  
  **Pattern References**:
  - Qdrant Python client: https://qdrant.tech/documentation/quick-start/
  - LangChain Qdrant integration: https://python.langchain.com/docs/integrations/vectorstores/qdrant

  **External References**:
  - NVIDIA NIM Embeddings: https://build.nvidia.com/nvidia/embed-qa-4
  - Qdrant Hybrid Search: https://qdrant.tech/documentation/concepts/hybrid-queries/

  **Acceptance Criteria**:

  **TDD Tests**:
  - [x] Test file: `tests/test_ingestion.py`
  - [x] Test: `test_ingest_single_document` - ingests one doc and retrieves it
  - [x] Test: `test_ingest_batch` - ingests batch and counts match
  - [x] `pytest tests/test_ingestion.py` → PASS

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Qdrant container running
    Tool: Bash
    Preconditions: docker-compose.yml exists
    Steps:
      1. Run: docker-compose up -d qdrant
      2. Run: curl http://localhost:6333/collections
      3. Assert: HTTP 200
      4. Assert: Response contains "collections" key
    Expected Result: Qdrant API accessible
    Evidence: curl response body

  Scenario: Sample data ingested
    Tool: Bash
    Preconditions: Qdrant running, sample data ready
    Steps:
      1. Run: python backend/scripts/ingest.py --sample
      2. Assert: Exit code 0
      3. Run: curl http://localhost:6333/collections/legal_docs
      4. Assert: points_count >= 1000
    Expected Result: At least 1000 vectors in collection
    Evidence: Collection info response

  Scenario: Metadata preserved in vectors
    Tool: Bash
    Preconditions: Data ingested
    Steps:
      1. Run: curl -X POST http://localhost:6333/collections/legal_docs/points/scroll -d '{"limit":1}'
      2. Assert: Response contains payload.jenis_dokumen
      3. Assert: Response contains payload.nomor
      4. Assert: Response contains payload.tahun
    Expected Result: Metadata fields present
    Evidence: Point payload JSON
  ```

  **Commit**: YES
  - Message: `feat(db): setup Qdrant with NVIDIA NIM embeddings ingestion`
  - Files: `docker-compose.yml`, `backend/scripts/ingest.py`
  - Pre-commit: `pytest tests/test_ingestion.py`

---

### Task 4: Configure Hybrid Search (BM25 + Dense)

- [x] 4. Configure Hybrid Search (BM25 + Dense Vectors)

  **What to do**:
  - Enable sparse vectors in Qdrant collection for BM25
  - Implement hybrid search retriever combining:
    - Dense vector similarity (NVIDIA NIM Embeddings)
    - Sparse vector BM25 (for exact legal terms like "Pasal 33")
  - Configure reranking/fusion strategy (Reciprocal Rank Fusion)
  - Create retriever class: `backend/retriever.py`
  - Test with legal queries requiring exact term matches

  **Must NOT do**:
  - Do NOT use only semantic search (misses "Pasal 33" exact matches)
  - Do NOT use only BM25 (misses semantic similarity)

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
    - Reason: Complex search configuration requiring deep understanding of hybrid retrieval
  - **Skills**: []
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (after Task 3)
  - **Blocks**: Task 5
  - **Blocked By**: Task 3

  **References**:
  
  **External References**:
  - Qdrant Hybrid Search: https://qdrant.tech/documentation/concepts/hybrid-queries/
  - Sparse Vectors in Qdrant: https://qdrant.tech/documentation/concepts/vectors/#sparse-vectors
  - Reciprocal Rank Fusion: https://www.elastic.co/guide/en/elasticsearch/reference/current/rrf.html

  **Acceptance Criteria**:

  **TDD Tests**:
  - [x] Test file: `tests/test_retriever.py`
  - [x] Test: `test_semantic_retrieval` - finds relevant docs by meaning
  - [x] Test: `test_keyword_retrieval` - finds "Pasal 33" exactly
  - [x] Test: `test_hybrid_retrieval` - combines both approaches
  - [x] `pytest tests/test_retriever.py` → PASS

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Exact term "Pasal 33" retrieved
    Tool: Bash (Python)
    Preconditions: Data ingested with hybrid vectors
    Steps:
      1. Run: python -c "from backend.retriever import HybridRetriever; r = HybridRetriever(); results = r.retrieve('Pasal 33'); print([d.metadata['pasal'] for d in results[:3]])"
      2. Assert: Output contains "33"
    Expected Result: Pasal 33 appears in top results
    Evidence: Retrieval results

  Scenario: Semantic query finds related regulations
    Tool: Bash (Python)
    Preconditions: Retriever configured
    Steps:
      1. Run: python -c "from backend.retriever import HybridRetriever; r = HybridRetriever(); results = r.retrieve('izin usaha warung kopi'); print(len(results))"
      2. Assert: results count > 0
      3. Assert: Results relate to business licensing
    Expected Result: Relevant regulations found
    Evidence: Retrieval results with metadata
  ```

  **Commit**: YES
  - Message: `feat(search): implement hybrid BM25 + dense vector retrieval`
  - Files: `backend/retriever.py`, `tests/test_retriever.py`
  - Pre-commit: `pytest tests/test_retriever.py`

---

### Task 5: Build Core RAG Chain with LangChain

- [x] 5. Build Core RAG Chain with LangChain

  **What to do**:
  - Create RAG chain: `backend/rag_chain.py`
  - Connect: Hybrid Retriever → Context Builder → Kimi 2.5 LLM → Response
  - Design prompt template for legal Q&A in Bahasa Indonesia
  - Include citation extraction from retrieved documents
  - Implement streaming response support
  - Add context window management (avoid token overflow)

  **Must NOT do**:
  - Do NOT hardcode prompts in English
  - Do NOT skip citation in responses
  - Do NOT allow responses without source documents

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
    - Reason: Core RAG logic, prompt engineering for legal domain
  - **Skills**: []
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (after Task 4)
  - **Blocks**: Tasks 6, 7
  - **Blocked By**: Task 4

  **References**:
  
  **External References**:
  - LangChain RAG: https://python.langchain.com/docs/tutorials/rag/
  - NVIDIA NIM Chat: https://docs.langchain.com/oss/python/integrations/chat/nvidia_ai_endpoints

  **Pattern References**:
  - Citation prompt pattern: Include "Cite your sources as: [Jenis] No. [Nomor] Tahun [Tahun], Pasal [X]"

  **Acceptance Criteria**:

  **TDD Tests**:
  - [x] Test file: `tests/test_rag_chain.py`
  - [x] Test: `test_rag_returns_answer` - chain produces response
  - [x] Test: `test_rag_includes_citation` - response contains source reference
  - [x] Test: `test_rag_bahasa_indonesia` - response in Indonesian
  - [x] `pytest tests/test_rag_chain.py` → PASS

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: RAG chain answers legal question with citation
    Tool: Bash (Python)
    Preconditions: RAG chain configured, data ingested
    Steps:
      1. Run: python -c "from backend.rag_chain import RAGChain; rag = RAGChain(); response = rag.query('Apa syarat mendirikan PT?'); print(response)"
      2. Assert: Response contains "Berdasarkan" or "Menurut"
      3. Assert: Response contains regulation reference (UU/PP/Perpres)
      4. Assert: Response is in Bahasa Indonesia
    Expected Result: Cited legal answer
    Evidence: Full response text

  Scenario: RAG chain streams response
    Tool: Bash (Python)
    Preconditions: RAG chain configured
    Steps:
      1. Run: python -c "from backend.rag_chain import RAGChain; rag = RAGChain(); for chunk in rag.stream('Apa itu UU Cipta Kerja?'): print(chunk, end='')"
      2. Assert: Multiple chunks printed progressively
    Expected Result: Streaming works
    Evidence: Streamed output
  ```

  **Commit**: YES
  - Message: `feat(rag): implement core RAG chain with citation support`
  - Files: `backend/rag_chain.py`, `tests/test_rag_chain.py`
  - Pre-commit: `pytest tests/test_rag_chain.py`

---

### Task 6: FastAPI Endpoints for Q&A

- [x] 6. FastAPI Endpoints for Q&A

  **What to do**:
  - Create FastAPI app: `backend/main.py`
  - Implement endpoints:
    - `POST /api/ask` - submit question, get answer with citations
    - `GET /api/ask/stream` - SSE streaming response
    - `GET /api/health` - health check
  - Add request/response Pydantic models
  - Add CORS for frontend access
  - Add rate limiting (optional for MVP)

  **Must NOT do**:
  - Do NOT add authentication endpoints
  - Do NOT create complex middleware

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Standard FastAPI setup, well-defined patterns
  - **Skills**: []
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 7)
  - **Blocks**: Task 8
  - **Blocked By**: Task 5

  **References**:
  
  **External References**:
  - FastAPI SSE: https://fastapi.tiangolo.com/advanced/custom-response/#eventstream
  - Pydantic models: https://docs.pydantic.dev/latest/

  **Acceptance Criteria**:

  **TDD Tests**:
  - [x] Test file: `tests/test_api.py`
  - [x] Test: `test_ask_endpoint` - POST /api/ask returns 200
  - [x] Test: `test_health_endpoint` - GET /api/health returns 200
  - [x] `pytest tests/test_api.py` → PASS

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: POST /api/ask returns legal answer
    Tool: Bash (curl)
    Preconditions: FastAPI server running on localhost:8000
    Steps:
      1. Run: curl -X POST http://localhost:8000/api/ask \
           -H "Content-Type: application/json" \
           -d '{"question": "Apa syarat mendirikan CV?"}'
      2. Assert: HTTP 200
      3. Assert: Response contains "answer" field
      4. Assert: Response contains "citations" array
    Expected Result: JSON with answer and citations
    Evidence: Response body JSON

  Scenario: Health check responds
    Tool: Bash (curl)
    Preconditions: Server running
    Steps:
      1. Run: curl http://localhost:8000/api/health
      2. Assert: HTTP 200
      3. Assert: Response contains "status": "healthy"
    Expected Result: Health check passes
    Evidence: Response body
  ```

  **Commit**: YES
  - Message: `feat(api): add FastAPI endpoints for legal Q&A`
  - Files: `backend/main.py`, `backend/models.py`, `tests/test_api.py`
  - Pre-commit: `pytest tests/test_api.py`

---

### Task 7: Citation Generation + "I Don't Know" Guardrail

- [x] 7. Citation Generation + "I Don't Know" Guardrail

  **What to do**:
  - Create citation formatter: `backend/citation.py`
  - Extract structured citation from retrieved documents:
    - Format: `[Jenis] No. [Nomor] Tahun [Tahun], Pasal [X], Ayat [Y]`
    - Include source URL if available
  - Implement confidence threshold check
  - If retrieval score < threshold OR no relevant docs:
    - Return: "Saya tidak menemukan peraturan spesifik tentang hal ini. Silakan konsultasikan dengan ahli hukum."
  - Add citation to response model

  **Must NOT do**:
  - Do NOT allow responses without citations
  - Do NOT guess/hallucinate legal information
  - Do NOT set threshold too low (causes false positives)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Critical safety feature, requires careful threshold tuning
  - **Skills**: []
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 6)
  - **Blocks**: Task 8
  - **Blocked By**: Task 5

  **References**:
  
  **Pattern References**:
  - Citation format from peraturan.go.id data schema

  **Acceptance Criteria**:

  **TDD Tests**:
  - [x] Test file: `tests/test_citation.py`
  - [x] Test: `test_format_citation` - formats citation correctly
  - [x] Test: `test_low_confidence_response` - returns "I don't know" when confidence low
  - [x] Test: `test_no_docs_response` - returns "I don't know" when no docs retrieved
  - [x] `pytest tests/test_citation.py` → PASS

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Citation formatted correctly
    Tool: Bash (Python)
    Preconditions: Citation module exists
    Steps:
      1. Run: python -c "from backend.citation import format_citation; c = format_citation({'jenis_dokumen': 'UU', 'nomor': '11', 'tahun': '2020', 'pasal': '5'}); print(c)"
      2. Assert: Output contains "UU No. 11 Tahun 2020"
      3. Assert: Output contains "Pasal 5"
    Expected Result: Proper citation format
    Evidence: Formatted citation string

  Scenario: Low confidence returns "I don't know"
    Tool: Bash (curl)
    Preconditions: API running
    Steps:
      1. Run: curl -X POST http://localhost:8000/api/ask \
           -d '{"question": "Bagaimana cara membangun roket luar angkasa?"}'
      2. Assert: Response contains "tidak menemukan" or "konsultasikan"
    Expected Result: Polite refusal for out-of-domain query
    Evidence: Response body
  ```

  **Commit**: YES
  - Message: `feat(safety): add citation formatter and confidence guardrail`
  - Files: `backend/citation.py`, `tests/test_citation.py`
  - Pre-commit: `pytest tests/test_citation.py`

---

### Task 8: Next.js Project Setup + Q&A Interface

- [x] 8. Next.js Project Setup + Q&A Interface

  **What to do**:
  - Initialize Next.js 14 with App Router: `npx create-next-app@latest frontend`
  - Install Tailwind CSS, shadcn/ui components
  - Create pages:
    - `/` - Landing page with search box
    - `/ask` - Q&A interface with streaming responses
  - Implement components:
    - `SearchBox` - question input
    - `ResponseCard` - answer with citations
    - `CitationBadge` - clickable citation link
  - Connect to FastAPI backend
  - Implement streaming response display

  **Must NOT do**:
  - Do NOT use Pages Router (App Router only)
  - Do NOT skip loading/error states
  - Do NOT hardcode backend URL

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Frontend UI work with React components
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: For polished UI/UX design

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 9)
  - **Blocks**: Tasks 10, 11
  - **Blocked By**: Tasks 6, 7

  **References**:
  
  **External References**:
  - Next.js App Router: https://nextjs.org/docs/app
  - shadcn/ui: https://ui.shadcn.com/
  - React Streaming: https://nextjs.org/docs/app/building-your-application/routing/loading-ui-and-streaming

  **Acceptance Criteria**:

  **TDD Tests**:
  - [x] Test file: `frontend/__tests__/SearchBox.test.tsx`
  - [x] Test: `renders search input`
  - [x] Test: `submits question on enter`
  - [x] `npm test` → PASS

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Landing page loads
    Tool: Playwright
    Preconditions: Frontend dev server on localhost:3000
    Steps:
      1. Navigate to: http://localhost:3000
      2. Wait for: input[placeholder*="Tanyakan"] visible (timeout: 5s)
      3. Assert: Search box exists
      4. Screenshot: .sisyphus/evidence/task-8-landing.png
    Expected Result: Landing page with search
    Evidence: .sisyphus/evidence/task-8-landing.png

  Scenario: Q&A flow works end-to-end
    Tool: Playwright
    Preconditions: Frontend + Backend running
    Steps:
      1. Navigate to: http://localhost:3000
      2. Fill: input[type="text"] → "Apa itu UU Cipta Kerja?"
      3. Click: button[type="submit"]
      4. Wait for: .response-card visible (timeout: 30s)
      5. Assert: Response contains text
      6. Assert: Citation badge exists
      7. Screenshot: .sisyphus/evidence/task-8-qa-response.png
    Expected Result: Answer displayed with citation
    Evidence: .sisyphus/evidence/task-8-qa-response.png
  ```

  **Commit**: YES
  - Message: `feat(frontend): add Next.js Q&A interface with streaming`
  - Files: `frontend/`
  - Pre-commit: `npm test`

---

### Task 9: Compliance Checker Backend (Text + PDF)

- [x] 9. Compliance Checker Backend (Text + PDF)

  **What to do**:
  - Create endpoint: `POST /api/compliance/check`
  - Accept: text description OR PDF file upload
  - For PDF: Extract text using PyMuPDF + Tesseract OCR
  - Analyze text against relevant regulations
  - Return: list of applicable regulations, compliance status, recommendations
  - Use RAG chain to find relevant regulations

  **Must NOT do**:
  - Do NOT give definitive legal advice (always recommend consulting lawyer)
  - Do NOT process files > 10MB

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: PDF processing + compliance logic
  - **Skills**: []
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 8)
  - **Blocks**: Task 10
  - **Blocked By**: Task 5

  **References**:
  
  **External References**:
  - PyMuPDF: https://pymupdf.readthedocs.io/
  - Tesseract Python: https://github.com/madmaze/pytesseract

  **Acceptance Criteria**:

  **TDD Tests**:
  - [x] Test file: `tests/test_compliance.py`
  - [x] Test: `test_check_text_input` - analyzes text description
  - [x] Test: `test_check_pdf_upload` - processes PDF and analyzes
  - [x] `pytest tests/test_compliance.py` → PASS

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Text compliance check
    Tool: Bash (curl)
    Preconditions: API running
    Steps:
      1. Run: curl -X POST http://localhost:8000/api/compliance/check \
           -H "Content-Type: application/json" \
           -d '{"text": "Saya ingin membuka usaha warung kopi di Jakarta"}'
      2. Assert: HTTP 200
      3. Assert: Response contains "regulations" array
      4. Assert: Response contains "recommendations"
    Expected Result: Compliance analysis returned
    Evidence: Response JSON

  Scenario: PDF upload compliance check
    Tool: Bash (curl)
    Preconditions: Sample PDF in tests/fixtures/
    Steps:
      1. Run: curl -X POST http://localhost:8000/api/compliance/check \
           -F "file=@tests/fixtures/business_plan.pdf"
      2. Assert: HTTP 200
      3. Assert: Response contains extracted text summary
      4. Assert: Response contains applicable regulations
    Expected Result: PDF processed and analyzed
    Evidence: Response JSON
  ```

  **Commit**: YES
  - Message: `feat(compliance): add text + PDF compliance checker endpoint`
  - Files: `backend/compliance.py`, `tests/test_compliance.py`
  - Pre-commit: `pytest tests/test_compliance.py`

---

### Task 10: Compliance Checker Frontend

- [x] 10. Compliance Checker Frontend

  **What to do**:
  - Create page: `/compliance` 
  - Implement components:
    - `TextInput` - multi-line business description input
    - `FileUpload` - PDF drag-and-drop upload (max 10MB)
    - `ComplianceResult` - regulation cards with status indicators
    - `RecommendationList` - actionable next steps
  - Add tab interface to switch between text/PDF modes
  - Display loading state during analysis
  - Link to source regulations in results

  **Must NOT do**:
  - Do NOT allow files > 10MB
  - Do NOT skip disclaimer about consulting lawyers

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Frontend UI with file upload components
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: For polished form UI

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Task 11)
  - **Blocks**: Task 12
  - **Blocked By**: Tasks 8, 9

  **References**:
  
  **External References**:
  - React Dropzone: https://react-dropzone.js.org/
  - shadcn/ui Tabs: https://ui.shadcn.com/docs/components/tabs

  **Acceptance Criteria**:

  **TDD Tests**:
  - [x] Test file: `frontend/__tests__/ComplianceChecker.test.tsx`
  - [x] Test: `renders text input mode`
  - [x] Test: `renders file upload mode`
  - [x] `npm test` → PASS

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Compliance page with text input
    Tool: Playwright
    Preconditions: Frontend running
    Steps:
      1. Navigate to: http://localhost:3000/compliance
      2. Click: tab[data-value="text"]
      3. Fill: textarea → "Usaha warung kopi di area perumahan Jakarta Selatan"
      4. Click: button[type="submit"]
      5. Wait for: .compliance-result visible (timeout: 30s)
      6. Assert: Result cards displayed
      7. Assert: Disclaimer text visible
      8. Screenshot: .sisyphus/evidence/task-10-compliance-text.png
    Expected Result: Compliance results shown
    Evidence: .sisyphus/evidence/task-10-compliance-text.png

  Scenario: File upload interaction
    Tool: Playwright
    Preconditions: Frontend running
    Steps:
      1. Navigate to: http://localhost:3000/compliance
      2. Click: tab[data-value="pdf"]
      3. Assert: Dropzone visible with "Upload PDF" text
      4. Screenshot: .sisyphus/evidence/task-10-upload-zone.png
    Expected Result: Upload zone visible
    Evidence: .sisyphus/evidence/task-10-upload-zone.png
  ```

  **Commit**: YES
  - Message: `feat(frontend): add compliance checker UI with text + PDF modes`
  - Files: `frontend/app/compliance/`
  - Pre-commit: `npm test`

---

### Task 11: Form Guidance Feature

- [x] 11. Form Guidance Feature

  **What to do**:
  - Create page: `/guidance`
  - Implement wizard flow:
    1. User selects business type (dropdown)
    2. User selects location (province/city)
    3. System shows required documents/forms
    4. Links to OSS (Online Single Submission) portal
    5. Checklist of requirements
  - Use RAG to find relevant requirements
  - Store common business types as presets

  **Must NOT do**:
  - Do NOT auto-fill government forms (out of scope)
  - Do NOT promise completion guarantees

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Multi-step wizard UI
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: For wizard flow design

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Task 10)
  - **Blocks**: Task 12
  - **Blocked By**: Task 8

  **References**:
  
  **External References**:
  - OSS Portal: https://oss.go.id/
  - NIB Info: https://oss.go.id/informasi/nib

  **Acceptance Criteria**:

  **TDD Tests**:
  - [x] Test file: `frontend/__tests__/Guidance.test.tsx`
  - [x] Test: `renders business type selector`
  - [x] Test: `shows requirements after selection`
  - [x] `npm test` → PASS

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Form guidance wizard flow
    Tool: Playwright
    Preconditions: Frontend running
    Steps:
      1. Navigate to: http://localhost:3000/guidance
      2. Select: select[name="businessType"] → "Warung/Kedai Kopi"
      3. Select: select[name="location"] → "DKI Jakarta"
      4. Click: button[text="Lihat Persyaratan"]
      5. Wait for: .requirements-list visible
      6. Assert: NIB mentioned in requirements
      7. Assert: OSS link present
      8. Screenshot: .sisyphus/evidence/task-11-guidance.png
    Expected Result: Requirements checklist shown
    Evidence: .sisyphus/evidence/task-11-guidance.png
  ```

  **Commit**: YES
  - Message: `feat(frontend): add form guidance wizard for business requirements`
  - Files: `frontend/app/guidance/`
  - Pre-commit: `npm test`

---

### Task 12: Integration Testing + Polish

- [x] 12. Integration Testing + Polish

  **What to do**:
  - Write E2E tests with Playwright covering full user journeys
  - Test Q&A flow end-to-end
  - Test Compliance Checker with real PDF
  - Test Form Guidance complete flow
  - Fix any discovered bugs
  - Add loading skeletons and error boundaries
  - Optimize for mobile responsiveness
  - Add meta tags for SEO
  - Create README with setup instructions

  **Must NOT do**:
  - Do NOT deploy to production (separate task)
  - Do NOT add features not in scope

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Integration testing + bug fixing requires full system understanding
  - **Skills**: [`playwright`]
    - `playwright`: For E2E testing

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4 (final task)
  - **Blocks**: None (final)
  - **Blocked By**: Tasks 10, 11

  **References**:
  
  **External References**:
  - Playwright Testing: https://playwright.dev/docs/intro

  **Acceptance Criteria**:

  **TDD Tests**:
  - [x] Test file: `e2e/full-journey.spec.ts`
  - [x] Test: `complete Q&A journey`
  - [x] Test: `complete compliance check journey`
  - [x] Test: `complete guidance journey`
  - [x] `npx playwright test` → PASS

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Full Q&A journey
    Tool: Playwright
    Preconditions: Full stack running
    Steps:
      1. Navigate to: http://localhost:3000
      2. Fill: input → "Apa persyaratan mendirikan PT?"
      3. Submit form
      4. Wait for: response card (timeout: 60s)
      5. Assert: Answer contains legal content
      6. Assert: Citation badge clickable
      7. Click: citation badge
      8. Assert: Regulation details shown
      9. Screenshot: .sisyphus/evidence/task-12-qa-journey.png
    Expected Result: Complete Q&A journey works
    Evidence: .sisyphus/evidence/task-12-qa-journey.png

  Scenario: Mobile responsiveness
    Tool: Playwright
    Preconditions: Frontend running
    Steps:
      1. Set viewport: 375x667 (iPhone SE)
      2. Navigate to: http://localhost:3000
      3. Assert: Search box visible
      4. Assert: No horizontal scroll
      5. Screenshot: .sisyphus/evidence/task-12-mobile.png
    Expected Result: Mobile-friendly layout
    Evidence: .sisyphus/evidence/task-12-mobile.png
  ```

  **Commit**: YES
  - Message: `test(e2e): add integration tests and polish UI`
  - Files: `e2e/`, `README.md`
  - Pre-commit: `npx playwright test`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | `feat(setup): initialize project with NVIDIA NIM configuration` | backend/, frontend/, .env.example | pytest tests/test_config.py |
| 2 | `feat(data): add peraturan.go.id dataset with schema documentation` | data/ | pytest tests/test_data_loader.py |
| 3 | `feat(db): setup Qdrant with NVIDIA NIM embeddings ingestion` | docker-compose.yml, backend/scripts/ | pytest tests/test_ingestion.py |
| 4 | `feat(search): implement hybrid BM25 + dense vector retrieval` | backend/retriever.py | pytest tests/test_retriever.py |
| 5 | `feat(rag): implement core RAG chain with citation support` | backend/rag_chain.py | pytest tests/test_rag_chain.py |
| 6 | `feat(api): add FastAPI endpoints for legal Q&A` | backend/main.py | pytest tests/test_api.py |
| 7 | `feat(safety): add citation formatter and confidence guardrail` | backend/citation.py | pytest tests/test_citation.py |
| 8 | `feat(frontend): add Next.js Q&A interface with streaming` | frontend/ | npm test |
| 9 | `feat(compliance): add text + PDF compliance checker endpoint` | backend/compliance.py | pytest tests/test_compliance.py |
| 10 | `feat(frontend): add compliance checker UI with text + PDF modes` | frontend/app/compliance/ | npm test |
| 11 | `feat(frontend): add form guidance wizard for business requirements` | frontend/app/guidance/ | npm test |
| 12 | `test(e2e): add integration tests and polish UI` | e2e/, README.md | npx playwright test |

---

## Success Criteria

### Verification Commands
```bash
# Backend tests
cd backend && pytest --cov=. --cov-report=term-missing  # Expected: All pass, >80% coverage

# Frontend tests  
cd frontend && npm test  # Expected: All pass

# E2E tests
npx playwright test  # Expected: All pass

# Full stack health
curl http://localhost:8000/api/health  # Expected: {"status": "healthy"}
curl http://localhost:3000  # Expected: 200 OK
```

### Final Checklist
- [x] User can ask legal questions and receive cited answers
- [x] Citations link to regulation sources
- [x] Compliance Checker works with text AND PDF input
- [x] Form Guidance shows requirements for selected business type
- [x] "I don't know" response for out-of-domain queries
- [x] Mobile responsive design
- [ ] All tests pass (pytest + npm test + playwright)
- [x] No hardcoded secrets in codebase
- [x] README with complete setup instructions
