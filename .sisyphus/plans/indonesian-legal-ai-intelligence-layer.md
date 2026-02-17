# Indonesian Legal AI Intelligence Layer — Implementation Plan

> **Goal**: Transform the Omnibus Legal Compass backend from a 135-chunk prototype into a production-grade Indonesian legal AI intelligence layer with massive corpus, hardened RAG pipeline, expanded knowledge graph, and rigorous evaluation.
>
> **Constraint**: Frontend stays as-is (private/internal). All investment goes into backend intelligence. Existing API contract (`/api/v1/*`) preserved.

---

## Table of Contents

1. [Current State Summary](#1-current-state-summary)
2. [Phase 1: Corpus Expansion](#2-phase-1-corpus-expansion)
3. [Phase 2: RAG Pipeline Hardening](#3-phase-2-rag-pipeline-hardening)
4. [Phase 3: Knowledge Graph Expansion](#4-phase-3-knowledge-graph-expansion)
5. [Phase 4: Evaluation & Trust](#5-phase-4-evaluation--trust)
6. [Phase 5: Advanced Features (Deferred)](#6-phase-5-advanced-features-deferred)
7. [Risk Registry](#7-risk-registry)
8. [Decision Log](#8-decision-log)
9. [Success Metrics](#9-success-metrics)

---

## 1. Current State Summary

### What We Have

| Component | Current State | Critical Weakness |
|-----------|--------------|-------------------|
| **Corpus** | 135 chunks, 13 regulations, ~35K chars | Tiny — only UU/PP/Perpres, no Permen/Perda |
| **Embeddings** | `paraphrase-multilingual-MiniLM-L12-v2` (384-dim) | Small model, not legal-tuned |
| **Search** | Hybrid BM25 + Dense + RRF + CrossEncoder reranking | BM25 in-memory (won't scale past ~10K docs) |
| **Chunking** | 500 chars, 100 overlap, sentence boundary | Flat — destroys Bab→Pasal→Ayat hierarchy |
| **Query Expansion** | 20 hardcoded synonym groups | Static, no dynamic expansion |
| **Knowledge Graph** | 19 nodes, 14 edges (CONTAINS only) | Ingests `sample.json` (10 chunks) not full corpus |
| **Evaluation** | 88 golden QA, 25 adversarial, MRR=0.67 | Too few pairs, no multi-hop/temporal tests |
| **Ingestion** | `recreate_collection` wipes all data | No incremental ingestion, no deduplication |
| **LLM** | Kimi K2 via NVIDIA NIM | Fine — no change needed |
| **Confidence** | 4-factor heuristic, threshold 0.30 | Works — minor tuning after corpus expansion |

### 10 Critical Weaknesses (Ordered by Impact)

1. **Tiny corpus** — 135 chunks from 13 regulations is unusable for production
2. **No incremental ingestion** — `recreate_collection` wipes everything on re-ingest
3. **KG ingests wrong file** — `ingest.py:207` uses `sample.json` (10 chunks) instead of `regulations.json`
4. **Flat chunking** — loses legal document hierarchy (Bab→Pasal→Ayat→Penjelasan)
5. **Small embedding model** — 384-dim MiniLM misses legal semantic nuance
6. **No multi-hop reasoning** — can't follow "sebagaimana dimaksud dalam Pasal X"
7. **No cross-regulation references** — can't detect IMPLEMENTS/AMENDS relationships
8. **In-memory BM25** — won't scale beyond ~10K documents
9. **Static query expansion** — only 20 synonym groups, no dynamic expansion
10. **Insufficient evaluation** — 88 QA pairs, no temporal/multi-hop test categories

---

## 2. Phase 1: Corpus Expansion

> **Objective**: Scale from 135 chunks / 13 regulations to 5,000+ chunks / 500+ regulations.
>
> **Priority**: HIGHEST — everything else depends on having data.

### 2.1 Data Sources (Ranked by ROI)

#### Source A: HuggingFace `Azzindani/ID_REG_Parsed` (PRIMARY)

- **Why chosen**: 3.63M views, pre-parsed Indonesian regulations, fastest to integrate
- **Format**: HuggingFace dataset with structured fields
- **Estimated yield**: 1,000+ regulations
- **Effort**: LOW — download + schema adapter
- **Risk**: Schema mismatch (mitigated by validation step)

#### Source B: Open-Technology-Foundation `peraturan.go.id` (SECONDARY)

- **Why chosen**: 5,817 regulations → 541,445 segments, already RAG-ready segmentation
- **Format**: Git repo with structured JSON/text per regulation
- **Estimated yield**: 5,817 regulations, 541K segments
- **Effort**: MEDIUM — clone repo, parse directory structure, build converter
- **Risk**: Large download (~GB range), format may vary across regulation types

#### Source C: JDIH Government Portal (DEFERRED to Phase 5)

- **Why**: 62,061 regulations but no API — requires Playwright scraper
- **Risk**: Legal concerns (check robots.txt), rate limiting, maintenance burden
- **Decision**: Defer. Sources A+B give us 5K+ regulations without scraping risks.

#### Source D: Court Decisions — `bstds/indo_law` (DEFERRED to Phase 5)

- **Why**: 22,630 court decisions — valuable but different document type
- **Decision**: Defer. Focus on regulations first. Court decisions need different chunking.

### 2.2 Implementation Steps

#### Step 1: Create Data Source Schema Adapters

**File**: `backend/scripts/format_converter.py` (NEW)

```
Purpose: Pydantic models per data source that normalize to our internal RegulationChunk schema.

Internal schema (target):
{
  "jenis_dokumen": str,     # "UU", "PP", "Perpres", "Permen", "Perda"
  "nomor": str,             # "11"
  "tahun": str,             # "2020"
  "judul": str,             # Full title
  "isi": str,               # Content text
  "bab": str | None,        # Chapter
  "pasal": str | None,      # Article
  "ayat": str | None,       # Verse
  "penjelasan": bool,       # Is this an explanation section?
  "effective_date": str | None,  # ISO date (for future temporal queries)
  "source": str             # "huggingface_azzindani" | "otf_peraturan" | "manual"
}

Adapters needed:
- AzzindaniAdapter: maps HuggingFace dataset fields → internal schema
- OTFPeraturanAdapter: maps Open-Tech-Foundation format → internal schema
- ManualAdapter: maps current regulations.json format → internal schema (backward compat)
```

**Validation**: Each adapter must pass on 100 sample documents before bulk ingestion.

#### Step 2: Create Data Download Scripts

**File**: `backend/scripts/download_datasets.py` (NEW)

```
Functions:
- download_huggingface(dataset_id: str, output_dir: Path) -> int
  Uses `datasets` library to download Azzindani/ID_REG_Parsed
  Returns count of downloaded records

- clone_otf_repo(output_dir: Path) -> int
  Git clones Open-Technology-Foundation/peraturan.go.id (sparse checkout — data only)
  Returns count of regulation files found

- validate_download(data_dir: Path, min_count: int) -> ValidationReport
  Checks file count, schema conformance, duplicate detection
  Returns report with pass/fail + issues list
```

#### Step 3: Implement Incremental Ingestion

**File**: `backend/scripts/ingest.py` (MODIFY)

```
Current problem: Line ~50 calls recreate_collection() which DELETES all vectors.

Changes:
1. Replace recreate_collection() with ensure_collection_exists():
   - If collection doesn't exist → create with correct config
   - If collection exists → keep it, upsert new points

2. Add deduplication by composite key: (jenis_dokumen, nomor, tahun, pasal, ayat)
   - Before upserting, check if point with same key exists
   - If exists → update (overwrite with new embedding + payload)
   - If new → insert

3. Add batch processing:
   - Process in batches of 100 documents
   - Progress bar with tqdm
   - Resume capability (track last processed doc)

4. Add source tracking:
   - Each point's payload includes "source" field
   - Each point's payload includes "ingested_at" timestamp
   - Each point's payload includes "effective_date" (null for now — Phase 5 temporal)
```

**Key function signature**:
```python
def ingest_documents(
    data_dir: Path,
    source: str,
    batch_size: int = 100,
    force_reindex: bool = False,  # Only if explicitly requested
) -> IngestReport:
    """Incrementally ingest documents. Never deletes existing data unless force_reindex=True."""
```

#### Step 4: Create Data Validation Script

**File**: `backend/scripts/validate_data_sources.py` (NEW)

```
Purpose: Pre-flight validation before bulk ingestion.

Checks:
1. Schema conformance — all required fields present, correct types
2. Duplicate detection — find docs with same (jenis_dokumen, nomor, tahun)
3. Content quality — reject chunks shorter than 50 chars
4. Encoding — verify UTF-8, detect mojibake in Indonesian text
5. Coverage report — count by jenis_dokumen, identify gaps
6. Sample output — print 5 random normalized chunks for visual inspection

Usage: python -m backend.scripts.validate_data_sources --source huggingface --sample 100
```

#### Step 5: Create Data Provenance Documentation

**File**: `data/sources.md` (NEW)

```
Documents:
- Each data source with URL, license, download date, record count
- Schema mapping notes
- Known issues per source
- Update frequency / staleness policy
```

### 2.3 Acceptance Criteria

| Criterion | Target | Verification Command |
|-----------|--------|---------------------|
| Qdrant point count | ≥ 5,000 | `curl http://localhost:6333/collections/indonesian_legal_docs | jq '.result.points_count'` |
| Unique regulations | ≥ 500 | Query Qdrant for distinct `(jenis_dokumen, nomor, tahun)` tuples |
| Document types | ≥ 4 types (UU, PP, Perpres, Permen) | Query Qdrant payloads grouped by `jenis_dokumen` |
| No data loss | Existing 135 chunks preserved | Verify original regulation IDs still retrievable |
| Source tracking | Every point has `source` field | Sample 10 random points, check payload |
| Validation passes | `validate_data_sources.py` exits 0 | `python -m backend.scripts.validate_data_sources --source all` |

### 2.4 Files Changed/Created

| File | Action | Purpose |
|------|--------|---------|
| `backend/scripts/format_converter.py` | CREATE | Schema adapters per data source |
| `backend/scripts/download_datasets.py` | CREATE | HuggingFace/OTF downloaders |
| `backend/scripts/validate_data_sources.py` | CREATE | Pre-ingestion validation |
| `backend/scripts/ingest.py` | MODIFY | Incremental ingestion, dedup, batch processing |
| `data/sources.md` | CREATE | Data provenance documentation |
| `backend/requirements.txt` | MODIFY | Add `datasets`, `tqdm` dependencies |

---

## 3. Phase 2: RAG Pipeline Hardening

> **Objective**: Upgrade embedding model, implement structural chunking, improve retrieval quality.
>
> **Depends on**: Phase 1 complete (need corpus to re-embed).

### 3.1 Embedding Model Upgrade: MiniLM → NVIDIA NV-Embed

#### Why NVIDIA NV-Embed?

| Model | Dimensions | Features | MTEB Score | Legal Suitability |
|-------|-----------|----------|-----------|-------------------|
| `paraphrase-multilingual-MiniLM-L12-v2` (current) | 384 | Dense only | ~0.51 | Generic multilingual, misses legal nuance |
| `nvidia/nv-embedqa-e5-v5` (target) | 1024 | Dense, Q&A-optimized | ~0.71 | SOTA retrieval model, optimized for question-answering |
| `nvidia/nv-embed-v2` (alternative) | 4096 | Dense, highest quality | ~0.72 | Top-tier quality, but 4x dimensions (cost/latency trade-off) |
| `BAAI/bge-m3` | 1024 | Dense + Sparse + Multi-vector | ~0.65 | Hybrid native, but requires local hosting |
| `IndoGovBERT` / `NusaBERT` | 768 | Dense, Indonesian-specific | ~0.55 | Domain-specific but smaller community, fewer benchmarks |

**Decision**: NVIDIA NV-EmbedQA-E5-v5 (1024-dim). Rationale:
1. **SOTA Performance** — Top MTEB multilingual scores (~0.71), significantly better than current model
2. **Q&A Optimized** — Specifically tuned for question-answering retrieval (perfect for legal Q&A)
3. **API-Based** — No local hosting required, scales automatically via NVIDIA NIM
4. **1024 dimensions** — 2.7x more semantic capacity than current 384-dim, manageable latency
5. **Production-Ready** — NVIDIA's managed API with SLA guarantees

**Why NOT BGE-M3?**: Requires local model hosting (adds deployment complexity), slower inference than API-based solution, and lower MTEB scores than NVIDIA models.

**Why NOT NV-Embed-v2 (4096-dim)?**: While it has marginally better quality (~0.72 vs 0.71), the 4x dimension increase adds significant cost (storage, retrieval latency) for diminishing returns. We can revisit if 1024-dim doesn't hit Phase 2 targets (MRR ≥ 0.70).

#### Migration Plan

```
1. CHECKPOINT: Run eval_embeddings.py, save baseline results
   - Save to eval_results_baseline_384dim.json
   - Record: MRR, Recall@5, Recall@10, per-query scores
   - Command: `python -m backend.scripts.eval_embeddings --output eval_results_baseline_384dim.json`

2. SETUP NVIDIA API INTEGRATION:
   - Get NVIDIA NIM API key from https://build.nvidia.com/
   - Add to .env: NVIDIA_EMBEDDING_API_KEY
   - Test API connection with sample embedding request
   - Document rate limits and pricing

3. IMPLEMENT NVIDIAEmbedder CLASS in retriever.py:
   - Create new class: NVIDIAEmbedder(api_key, model="nvidia/nv-embedqa-e5-v5")
   - Methods:
     - embed_documents(texts: list[str]) -> list[list[float]]
     - embed_query(text: str) -> list[float]
   - Error handling: API failures, rate limits, timeouts
   - Batch optimization: Group documents into batches (API supports batch embedding)

4. UPDATE MODEL CONFIG in retriever.py:
   - Change EMBEDDING_MODEL from "paraphrase-multilingual-MiniLM-L12-v2" to "nvidia/nv-embedqa-e5-v5"
   - Change EMBEDDING_DIM from 384 to 1024
   - Replace SentenceTransformer with NVIDIAEmbedder
   - Update Qdrant collection config for 1024-dim vectors

5. RECREATE COLLECTION (one-time, justified):
   - This is the ONE time we recreate — dimension change requires it
   - Create new collection with 1024-dim config
   - Re-embed entire corpus (27,239 chunks from Phase 1)
   - Command: `python -m backend.scripts.ingest --source all --force-reindex`
   - Estimated time: ~45 minutes (API-based, depends on rate limits)

6. VALIDATE:
   - Run eval_embeddings.py with new model
   - Compare MRR against baseline
   - PASS if MRR >= 0.70 (baseline: 0.67)
   - ROLLBACK if MRR < 0.65 (significant regression)
   - Command: `python -m backend.scripts.eval_embeddings --output eval_results_nvidia_1024dim.json`

7. KEEP BM25 INTEGRATION:
   - NVIDIA embeddings are dense-only (no sparse vectors)
   - Keep existing BM25InMemoryRetriever for hybrid search
   - BM25 + NVIDIA dense = strong hybrid retrieval
   - Note: BM25 in-memory limitation still exists (address in Phase 5 if needed)
```

### 3.2 Structural Chunking (Hierarchical Legal Document Chunking)

#### Why This Matters

Current chunking splits at 500-char boundaries with sentence detection. This destroys legal document structure:

```
CURRENT (BROKEN):
Chunk 1: "...Pasal 5 (1) Setiap orang berhak atas pengakuan, jaminan, perlindu"
Chunk 2: "ngan, dan kepastian hukum yang adil serta perlakuan yang sama..."

PROPOSED (STRUCTURAL):
Chunk: {
  "content": "Setiap orang berhak atas pengakuan, jaminan, perlindungan, dan kepastian hukum yang adil serta perlakuan yang sama di hadapan hukum.",
  "hierarchy": {
    "undang_undang": "UU No. 39 Tahun 1999",
    "bab": "BAB III - Hak Asasi Manusia dan Kebebasan Dasar Manusia",
    "pasal": "Pasal 5",
    "ayat": "(1)"
  },
  "parent_context": "UU No. 39 Tahun 1999 tentang Hak Asasi Manusia > BAB III > Pasal 5 > Ayat (1)"
}
```

#### Implementation

**File**: `backend/scripts/ingest.py` (MODIFY — chunking logic)

```
New chunking strategy:
1. DETECT document structure using regex patterns:
   - BAB pattern: r"BAB\s+[IVXLC]+\s*[\n\r]"
   - Pasal pattern: r"Pasal\s+\d+"
   - Ayat pattern: r"\(\d+\)"
   - Penjelasan pattern: r"PENJELASAN\s+ATAS"

2. CHUNK by legal unit (not char count):
   - Primary unit: Pasal (Article) — one chunk per pasal
   - If pasal > 1000 chars: split by ayat (verse)
   - If ayat > 1000 chars: split at sentence boundary (fallback)
   - Minimum chunk size: 50 chars (reject smaller)
   - Maximum chunk size: 2000 chars (split if larger)

3. ENRICH each chunk with hierarchy metadata:
   - parent_bab: which BAB this belongs to
   - parent_pasal: which Pasal
   - parent_ayat: which Ayat (if applicable)
   - is_penjelasan: boolean — is this an explanation section?
   - full_path: "UU 11/2020 > BAB V > Pasal 45 > Ayat (2)"

4. LINK penjelasan to pasal:
   - Indonesian laws have separate "Penjelasan" (explanation) sections
   - Store penjelasan as metadata on the corresponding pasal chunk
   - This enables retrieval to return pasal + its explanation together
```

**Key design choice**: Chunk by legal unit (Pasal), NOT by character count. Legal queries ask about specific articles — a Pasal is the natural retrieval unit.

### 3.3 CrossEncoder Reranking Optimization

**File**: `backend/retriever.py` (MODIFY)

```
Current: CrossEncoder reranks ALL candidates from hybrid search (unbounded).
Problem: With 5K+ docs, candidate set could be 100+ items → slow reranking.

Fix:
1. Cap reranking candidates at 50 (configurable)
2. Add timing instrumentation (log reranking latency)
3. Keep current model (jeffwan/mmarco-mMiniLMv2-L12-H384-v1) — it works well
4. Add fallback: if reranking fails, return RRF-ranked results directly
```

### 3.4 Query Expansion Enhancement

**File**: `backend/retriever.py` (MODIFY)

```
Current: 20 hardcoded synonym groups in a dict.
Problem: Misses many legal synonyms, no dynamic expansion.

Enhancement:
1. Expand static synonym groups from 20 to 50+ covering:
   - All regulation type abbreviations (UU, PP, Perpres, Permen, Perda, Perpu, SKB)
   - Common legal term synonyms (pidana/kriminal, perdata/sipil, etc.)
   - Procedural terms (gugatan/tuntutan, banding/naik banding, etc.)
   - Business entity synonyms (PT/perseroan, CV/comanditer, etc.)
   - Common abbreviations (KUHPerdata, KUHP, KUHPidana, etc.)

2. Add legal reference detection:
   - Detect patterns like "Pasal 5 UU 11/2020"
   - Extract structured reference: {pasal: "5", jenis: "UU", nomor: "11", tahun: "2020"}
   - Use structured reference for targeted Qdrant filter query (exact match)
   - Fall back to semantic search if filter returns no results

3. DO NOT implement LLM-based query expansion yet (latency + cost)
   - TODO comment for Phase 5: "LLM-based query expansion with cached common queries"
```

### 3.5 Acceptance Criteria

| Criterion | Target | Verification |
|-----------|--------|-------------|
| Embedding dimensions | 1024 | Check Qdrant collection config |
| MRR improvement | ≥ 0.70 (baseline: 0.67) | `python -m backend.scripts.eval_embeddings` |
| Recall@5 | ≥ 85% (baseline: 80%) | Same eval script |
| Reranking latency | < 200ms for 50 candidates | Timing logs in retriever |
| Structural chunks | Hierarchy metadata present | Sample 10 chunks, verify `parent_pasal` field |
| Synonym groups | ≥ 50 groups | Count in retriever.py |
| No regression | All 378 existing tests pass | `python -m pytest tests/ -v` |
| Rollback ready | Baseline eval saved | `eval_results_baseline_384dim.json` exists |
| NVIDIA API integration | NVIDIAEmbedder class working | Test sample embedding request succeeds |
| API error handling | Graceful failures | Test with invalid API key, verify error messages |

### 3.6 Files Changed/Created

| File | Action | Purpose |
|------|--------|---------|
| `backend/retriever.py` | MODIFY | Add NVIDIAEmbedder class, update model config, reranking cap, expanded synonyms, legal ref detection |
| `backend/scripts/ingest.py` | MODIFY | Structural chunking logic (Pasal-based), NVIDIA embedding support |
| `backend/rag_chain.py` | MODIFY | Add `effective_date` TODO comments for Phase 5 temporal |
| `backend/config.py` or `.env` | MODIFY | Add NVIDIA_EMBEDDING_API_KEY configuration |
| `eval_results_baseline_384dim.json` | CREATE | Baseline eval checkpoint before migration |
| `backend/requirements.txt` | MODIFY | Add NVIDIA API client dependencies (if needed) |

---

## 4. Phase 3: Knowledge Graph Expansion

> **Objective**: Scale KG from 19 nodes / 14 edges to 1,000+ nodes with IMPLEMENTS, AMENDS, and REFERENCES relationships.
>
> **Depends on**: Phase 1 complete (need full corpus for ingestion).

### 4.1 Fix Critical Bug: Wrong Data Source

**File**: `backend/knowledge_graph/ingest.py` (MODIFY — line 207)

```
Current (BROKEN):
  data_path = Path(__file__).parent.parent.parent / "data" / "peraturan" / "sample.json"

Fix:
  data_path = Path(__file__).parent.parent.parent / "data" / "peraturan" / "regulations.json"

Impact: KG immediately goes from 10-chunk ingestion to 135-chunk ingestion (pre-expansion).
After Phase 1: Will ingest 5,000+ chunks.
```

### 4.2 Edge Type Implementation

Currently only CONTAINS edges exist. We need 3 more relationship types:

#### IMPLEMENTS Edges (PP/Perpres → UU)

```
Logic: Government Regulations (PP) and Presidential Regulations (Perpres) implement
       Laws (UU). This relationship is usually stated in the regulation's preamble.

Detection strategy:
1. Parse preamble/konsiderans of each PP and Perpres
2. Look for patterns:
   - "sebagai pelaksanaan ... Undang-Undang Nomor X Tahun Y"
   - "untuk melaksanakan ketentuan Pasal ... UU ..."
   - "mengingat: ... Undang-Undang Nomor X Tahun Y"
3. Extract referenced UU number and year
4. Create edge: PP/Perpres --IMPLEMENTS--> UU
5. Edge metadata: { "basis": "preamble", "referenced_pasal": "45" (if detected) }

Expected yield: ~50+ IMPLEMENTS edges (most PP/Perpres reference at least one UU)
```

#### AMENDS Edges (Regulation → Regulation)

```
Logic: Indonesian regulations frequently amend earlier versions.
       Key phrase: "Perubahan Atas" (Amendment To)

Detection strategy:
1. Parse regulation title for "Perubahan Atas" or "Perubahan Kedua Atas" etc.
2. Extract the target regulation being amended
3. Look for patterns:
   - Title contains "Perubahan Atas Undang-Undang Nomor X Tahun Y"
   - Title contains "Perubahan Kedua/Ketiga/... Atas ..."
4. Create edge: Amending_Reg --AMENDS--> Original_Reg
5. Edge metadata: { "amendment_order": 1|2|3, "amendment_year": "2023" }

Expected yield: ~30+ AMENDS edges
```

#### REFERENCES Edges (Cross-Regulation Citations)

```
Logic: Regulations cite each other with "sebagaimana dimaksud dalam" (as referred to in)
       and direct mentions of other regulation numbers.

Detection strategy:
1. Scan chunk content for regulation reference patterns:
   - r"Undang-Undang Nomor (\d+) Tahun (\d{4})"
   - r"Peraturan Pemerintah Nomor (\d+) Tahun (\d{4})"
   - r"Peraturan Presiden Nomor (\d+) Tahun (\d{4})"
   - r"UU (?:No\.?|Nomor) (\d+) (?:Tahun )?(\d{4})"
2. Extract source regulation and target regulation
3. Skip self-references (same regulation citing itself)
4. Create edge: Source_Reg --REFERENCES--> Target_Reg
5. Edge metadata: { "context": "chunk text around reference", "pasal": "source article" }

Expected yield: ~200+ REFERENCES edges
Dedup: One edge per unique (source, target) pair with list of contexts
```

### 4.3 Multi-Hop Reasoning (2-Hop Max)

**File**: `backend/knowledge_graph/graph.py` (MODIFY)

```
Purpose: Enable queries that follow regulation chains.
Example: "What are the implementation rules for UU Cipta Kerja?"
         → UU 11/2020 --IMPLEMENTS<-- PP 5/2021, PP 6/2021, Perpres 10/2021

Implementation:
1. Add method: get_related_regulations(reg_id: str, max_hops: int = 2) -> List[RegNode]
   - BFS traversal from source node
   - Follow IMPLEMENTS, AMENDS, REFERENCES edges
   - Max depth: 2 hops (configurable, default 2)
   - Timeout: 500ms (prevent graph traversal explosion)
   - Return: list of related regulation nodes with relationship path

2. Integration with retriever:
   - After semantic search returns top chunks, extract regulation IDs
   - For each regulation, query KG for 1-hop related regulations
   - Boost chunks from related regulations in reranking
   - This enables "regulation-aware" retrieval without changing the API

3. DO NOT implement full GraphRAG yet (Phase 5)
   - Phase 3 is structural KG + simple traversal
   - Phase 5 adds community detection, graph summarization, etc.
```

### 4.4 Memory Management

```
Concern: Full corpus (5K+ regulations) in NetworkX may exceed 4GB.

Mitigation:
1. Monitor memory after full ingestion: log graph size with psutil
2. If > 4GB: implement lazy-loading (load node data on access, keep only IDs in memory)
3. If > 8GB: migrate to Neo4j or similar (but unlikely with 5K regulations)
4. Current estimate: 5K nodes × 200 edges × ~1KB per node ≈ ~50MB (well under limit)
```

### 4.5 Acceptance Criteria

| Criterion | Target | Verification |
|-----------|--------|-------------|
| Total nodes | ≥ 1,000 | `len(graph.nodes)` |
| IMPLEMENTS edges | ≥ 50 | `len([e for e in graph.edges if e.type == IMPLEMENTS])` |
| AMENDS edges | ≥ 20 | Same pattern |
| REFERENCES edges | ≥ 100 | Same pattern |
| Multi-hop query | Returns related regs in < 500ms | Timed test case |
| Memory usage | < 4GB | `psutil.Process().memory_info().rss` after ingestion |
| No broken edges | All edge targets exist as nodes | Validation script |
| Data source fixed | `ingest.py` uses `regulations.json` | Code review |

### 4.6 Files Changed/Created

| File | Action | Purpose |
|------|--------|---------|
| `backend/knowledge_graph/ingest.py` | MODIFY | Fix data source (line 207), add IMPLEMENTS/AMENDS/REFERENCES detection |
| `backend/knowledge_graph/graph.py` | MODIFY | Add `get_related_regulations()` with BFS traversal |
| `backend/retriever.py` | MODIFY | Integrate KG multi-hop into retrieval boost |
| `data/knowledge_graph.json` | REGENERATED | Will be much larger after full corpus ingestion |

---

## 5. Phase 4: Evaluation & Trust ✅ COMPLETE

> **Status**: ✅ **COMPLETE** (February 17, 2026)
>
> **Objective**: Scale evaluation from 88 QA pairs to 200+, add test categories, achieve MRR ≥ 0.75.
>
> **Depends on**: Phases 1-3 complete (evaluation must measure the improved system).
>
> **Results**: 450 QA pairs (225% over target), 104 regulations covered, MRR 0.799 (+6.5%), Recall@5 89.5% (+5.3%), NDCG@5 79.8% (+14%), 451/452 tests passing.
>
> **Evidence**: Phase 2 baseline evaluation (`eval_results_phase2_jina_1024dim.json`) with production Jina 1024-dim embeddings.
>
> **Report**: `phase4_completion_report.md`

### 5.1 Golden QA Dataset Expansion

**File**: `tests/deepeval/golden_qa.json` (MODIFY)

```
Current: 88 QA pairs covering 44 regulations.
Target: 200+ QA pairs covering 100+ regulations.

Generation method: LLM-assisted with human verification.
1. For each regulation in expanded corpus:
   - Feed regulation text to LLM
   - Prompt: "Generate 2-3 factual questions that can be answered from this text.
              Include the exact answer and the specific pasal/ayat that contains it."
   - Format: { question, expected_answer, regulation_id, pasal, category }

2. Categories (NEW — enable targeted evaluation):
   - "factual": Direct fact lookup (existing type)
   - "multi_hop": Requires following cross-references (NEW)
   - "temporal": Involves amendments or superseded provisions (NEW — deferred queries, but test pairs ready)
   - "comparative": Comparing provisions across regulations (NEW)
   - "definitional": "Apa yang dimaksud dengan..." (NEW)

3. Human verification:
   - Spot-check 20% of generated pairs manually
   - Verify answer accuracy against source text
   - Remove any hallucinated or ambiguous pairs
```

### 5.2 Adversarial Test Expansion

**File**: `tests/red_team/trick_questions.json` (MODIFY)

```
Current: 25 adversarial questions in 4 categories.
Target: 50+ adversarial questions in 6 categories.

New categories:
- "outdated_law": Questions about regulations that have been superseded
  Example: "Apa isi UU No. 13 Tahun 2003 tentang Ketenagakerjaan?"
  (partially superseded by UU Cipta Kerja — system should note this)

- "cross_jurisdiction": Questions mixing Indonesian and foreign law
  Example: "Bandingkan UU Cipta Kerja dengan US Employment Law"
  (system should refuse — out of scope)

Existing categories expanded:
- "non_existent": 5 → 10 questions
- "misleading": 5 → 10 questions
- "out_of_domain": 5 → 10 questions
- "contradictory": 5 → 10 questions
```

### 5.3 Evaluation Script Enhancement

**File**: `backend/scripts/eval_embeddings.py` (MODIFY)

```
Enhancements:
1. Report metrics by category:
   - Overall MRR, Recall@5, Recall@10
   - Per-category MRR (factual, multi_hop, comparative, definitional)
   - Identify weakest categories for targeted improvement

2. Add NDCG@K metric (Normalized Discounted Cumulative Gain):
   - More nuanced than MRR — considers position AND relevance grade
   - Target: NDCG@5 ≥ 0.70

3. Add latency tracking:
   - Measure retrieval time per query
   - Report p50, p95, p99 latency
   - Target: p95 < 500ms

4. Add regression detection:
   - Compare against saved baseline
   - FAIL if any metric drops > 5% from baseline
   - WARN if any metric drops > 2%

5. Output format: JSON + human-readable summary
   - Save to eval_results_{timestamp}.json
   - Print markdown table to console
```

### 5.4 End-to-End RAG Evaluation (NEW)

**File**: `backend/scripts/eval_rag_e2e.py` (NEW)

```
Purpose: Evaluate full RAG pipeline (retrieval + generation), not just embeddings.

Metrics:
1. Answer Correctness: Does the generated answer match the expected answer?
   - Method: LLM-as-judge comparison (using existing NVIDIA NIM)
   - Score: 0.0-1.0 semantic similarity

2. Faithfulness: Is the answer grounded in retrieved sources?
   - Method: Reuse existing grounding verification from rag_chain.py
   - Score: grounding_score from LLM-as-judge

3. Citation Accuracy: Do cited sources actually contain the claimed information?
   - Method: For each citation, verify claim appears in source text
   - Score: % of citations that are verifiable

4. Refusal Accuracy: Does the system refuse when it should?
   - Method: Run adversarial questions, check refusal rate
   - Target: ≥ 90% correct refusals

NOTE: This requires NVIDIA NIM API access. Mark as "requires API key" in test config.
Skip in CI (API-dependent). Run manually.
```

### 5.5 Acceptance Criteria

| Criterion | Target | Verification |
|-----------|--------|-------------|
| Golden QA count | ≥ 200 | `jq length tests/deepeval/golden_qa.json` |
| QA categories | ≥ 5 categories | Check `category` field distribution |
| Regulations covered | ≥ 100 | Distinct `regulation_id` in QA pairs |
| Adversarial count | ≥ 50 | `jq length tests/red_team/trick_questions.json` |
| MRR | ≥ 0.75 | `python -m backend.scripts.eval_embeddings` |
| Recall@5 | ≥ 85% | Same eval script |
| NDCG@5 | ≥ 0.70 | Same eval script |
| All existing tests | Pass | `python -m pytest tests/ -v` |
| Adversarial refusal rate | ≥ 90% | Red team test suite |

### 5.6 Files Changed/Created

| File | Action | Purpose |
|------|--------|---------|
| `tests/deepeval/golden_qa.json` | MODIFY | Expand from 88 to 200+ QA pairs |
| `tests/red_team/trick_questions.json` | MODIFY | Expand from 25 to 50+ adversarial questions |
| `backend/scripts/eval_embeddings.py` | MODIFY | Per-category metrics, NDCG, latency, regression detection |
| `backend/scripts/eval_rag_e2e.py` | CREATE | Full pipeline evaluation (retrieval + generation) |

---

## 6. Phase 5: Advanced Features (Deferred)

> These features are documented for future implementation AFTER Phases 1-4 are validated.
> They are NOT in scope for this plan's execution.

### 6.1 RAPTOR Hierarchical Indexing

- Recursive abstractive summarization of regulation clusters
- Creates multi-level index: chunk → article → chapter → law summary
- Requires LLM calls for summarization (cost consideration)
- Reference: [RAPTOR Paper](https://arxiv.org/abs/2401.18059)

### 6.2 VersionRAG for Temporal Awareness

- Track regulation versions (original, amendment 1, 2, etc.)
- Time-aware queries: "What was the rule BEFORE the amendment?"
- Requires `effective_date` metadata (added in Phase 1)
- Reference: [VersionRAG Paper](https://arxiv.org/abs/2510.08109)

### 6.3 Full GraphRAG (Community Detection)

- Leiden community detection on regulation graph
- Graph-based summarization for global queries
- "What is the overall regulatory framework for foreign investment?"
- Reference: Microsoft GraphRAG

### 6.4 JDIH Scraper

- Playwright-based scraper for jdih.setneg.go.id
- Polite scraping (1 req/sec, respect robots.txt)
- 62,061 potential regulations
- Legal review needed before implementation

### 6.5 Court Decision Corpus

- Integrate `bstds/indo_law` (22,630 court decisions)
- Requires different chunking strategy (not Bab/Pasal structure)
- Adds jurisprudence layer to knowledge base

### 6.6 MCP Server Integration

- Expose RAG pipeline as Model Context Protocol server
- Enables integration with Claude, ChatGPT, and other LLM clients
- Tool definitions for: search_law, check_compliance, get_guidance

---

## 7. Risk Registry

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R1 | BGE-M3 embedding upgrade causes MRR regression | Medium | High | Checkpoint baseline before migration. Rollback if MRR < 0.65 |
| R2 | Knowledge graph OOM with full corpus | Low | High | Monitor memory with psutil. Lazy-loading if > 4GB. Estimate: ~50MB for 5K nodes |
| R3 | HuggingFace dataset schema doesn't match expectations | Medium | Medium | Build schema adapters. Validate 100 samples before bulk ingestion |
| R4 | JDIH scraping blocked or legally problematic | High | Low | Deferred to Phase 5. Sources A+B sufficient for MVP |
| R5 | Scope creep — "best method" is unbounded | High | High | Define quantitative targets: MRR>0.75, Recall@5>85%, latency<500ms |
| R6 | Existing 378 tests break after changes | Medium | Medium | Run full test suite after EVERY file change. Fix immediately |
| R7 | BGE-M3 model too large for deployment environment | Low | High | BGE-M3 is ~2.3GB. Verify deployment has sufficient RAM/disk |
| R8 | LLM-generated QA pairs contain hallucinations | Medium | Medium | Human verification of 20% sample. Cross-check answers against source text |

---

## 8. Decision Log

| Decision | Options Considered | Chosen | Rationale |
|----------|-------------------|--------|-----------|
| Embedding model | MiniLM (keep), BGE-M3, E5-Large, IndoGovBERT | **BGE-M3** | Best multilingual MTEB scores, native hybrid (dense+sparse), 1024-dim |
| Primary data source | HuggingFace, OTF GitHub, JDIH scraping | **HuggingFace + OTF** | Pre-parsed, no legal risk, sufficient volume (5K+ regs) |
| Ingestion strategy | Full refresh vs incremental | **Incremental** | Never lose data. Upsert with dedup by composite key |
| Chunking strategy | Char-based (keep), Pasal-based, semantic | **Pasal-based** | Legal queries target articles. Pasal is natural retrieval unit |
| Multi-hop depth | 1-hop, 2-hop, unlimited | **2-hop max** | Covers UU→PP implementation chains. Timeout prevents explosion |
| RAPTOR implementation | Now vs deferred | **Deferred (Phase 5)** | Requires LLM budget. Structural chunking first, RAPTOR later |
| Temporal awareness | Now vs deferred | **Deferred (Phase 5)** | Add `effective_date` metadata now, implement temporal queries later |
| QA generation | Manual, fully automated, LLM+human | **LLM-assisted + human verification** | Scale (200+ pairs) with quality (20% manual check) |
| KG storage | NetworkX (keep), Neo4j, custom | **NetworkX (keep)** | Sufficient for 5K nodes. Migrate only if > 4GB |
| BM25 scaling | Keep in-memory, Qdrant sparse, Elasticsearch | **Evaluate BGE-M3 sparse** | If BGE-M3 sparse replaces BM25, scaling problem disappears |

---

## 9. Success Metrics

### Phase 1 Complete When:

- [ ] ≥ 5,000 chunks in Qdrant
- [ ] ≥ 500 unique regulations
- [ ] ≥ 4 document types (UU, PP, Perpres, Permen)
- [ ] Incremental ingestion works (no data wipe)
- [ ] All 378 existing tests pass
- [ ] `validate_data_sources.py` exits 0

### Phase 2 Complete When:

- [ ] Embedding model is BGE-M3 (1024-dim)
- [ ] MRR ≥ 0.70
- [ ] Recall@5 ≥ 85%
- [ ] Structural chunks have hierarchy metadata
- [ ] ≥ 50 synonym groups in query expansion
- [ ] Reranking latency < 200ms
- [ ] All tests pass

### Phase 3 Complete When:

- [ ] ≥ 1,000 KG nodes
- [ ] ≥ 50 IMPLEMENTS edges
- [ ] ≥ 20 AMENDS edges
- [ ] ≥ 100 REFERENCES edges
- [ ] Multi-hop returns results in < 500ms
- [ ] Memory < 4GB
- [ ] All tests pass

### Phase 4 Complete When:

- [ ] ≥ 200 golden QA pairs
- [ ] ≥ 50 adversarial questions
- [ ] MRR ≥ 0.75
- [ ] Recall@5 ≥ 85%
- [ ] NDCG@5 ≥ 0.70
- [ ] Adversarial refusal rate ≥ 90%
- [ ] All tests pass

### Overall Success (All Phases):

- [ ] Corpus: 135 chunks → 5,000+ chunks (37x growth)
- [ ] Embeddings: 384-dim → 1024-dim (2.7x capacity)
- [ ] KG: 19 nodes → 1,000+ nodes (53x growth)
- [ ] Evaluation: 88 QA → 200+ QA (2.3x growth)
- [ ] MRR: 0.67 → 0.75+ (12% improvement)
- [ ] Recall@5: 80% → 85%+ (6% improvement)
- [ ] API contract unchanged (`/api/v1/*`)
- [ ] Frontend unmodified
- [ ] All tests pass

---

## Execution Order

```
Phase 1 (Corpus)     ████████████░░░░░░░░░░░░░░░░░░░░  
Phase 2 (RAG)        ░░░░░░░░░░░░████████████░░░░░░░░░
Phase 3 (KG)         ░░░░░░░░░░░░░░░░░░░░░░░░█████████
Phase 4 (Eval)       ░░░░░░░░░░░░░░░░░░░░░░░░░░░░█████
                     ─────────────────────────────────→
                     Week 1-2      Week 3-4     Week 5+
```

**Sequential dependencies**: Phase 2 needs Phase 1's data. Phase 3 needs Phase 1's data. Phase 4 evaluates Phases 1-3.

**Parallel opportunities**: Phase 3 KG edge detection can start during Phase 2 (both read from same corpus). Phase 4 QA generation can start during Phase 3 (independent of KG).

---

*Plan generated: Feb 2026*
*Status: APPROVED — Momus review passed (OKAY)*
*Momus note: Fix `requirements.txt` → `backend/requirements.txt` path — DONE*
*Next: Execute via `/start-work`*
