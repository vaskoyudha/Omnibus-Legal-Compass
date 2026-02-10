# ML Pipeline Upgrade Plan — Omnibus Legal Compass

## Goal
Upgrade the ML pipeline of the Indonesian Legal RAG system with 6 improvements to significantly boost answer quality, retrieval accuracy, and confidence scores. All changes must be **free, local, zero budget**.

## Constraints
- Zero budget — all models must be free/open-source HuggingFace models
- LLM: NVIDIA NIM with `moonshotai/kimi-k2-instruct` (unchanged)
- Vector DB: Local Qdrant via Docker on port 6333
- Must not break existing API contract (backward compatible)
- Must re-ingest all 200 documents after embedding/chunking changes

## Current State
- Embedding: `paraphrase-multilingual-MiniLM-L12-v2` (384-dim, paraphrase model — wrong type for search)
- BM25 tokenizer: naive regex split + stopword removal (no stemming)
- LLM temperature: 0.7 (too creative for legal answers)
- Chunking: character-based 500-char with 100-char overlap (ignores legal structure)
- Single prompt template for all question types
- No answer grounding verification
- Confidence: 71-75%

## Success Criteria
- [ ] Confidence scores consistently above 80%
- [ ] All 6 improvements implemented and working end-to-end
- [ ] Backend starts without errors
- [ ] Frontend displays grounding score
- [ ] All existing API endpoints still functional
- [ ] Tests pass
- [ ] Git committed and pushed

---

## Phase 1: Quick Wins (Temperature + Sastrawi Stemmer)

### Task 1.1: Lower LLM Temperature
- **File**: `backend/rag_chain.py` line 35
- **Change**: `TEMPERATURE = 0.7` → `TEMPERATURE = 0.2`
- **Why**: Legal answers need precision, not creativity. Lower temperature = more deterministic, factual outputs.
- **Risk**: None. Simple constant change.
- **Verify**: Backend starts, answers are more focused and less rambling.

### Task 1.2: Install PySastrawi
- **Command**: `pip install PySastrawi` in backend venv
- **File**: `backend/requirements.txt` — add `PySastrawi>=1.0.1`
- **Why**: Indonesian morphology is agglutinative. "mempekerjakan" → "kerja" improves BM25 recall.
- **Risk**: None. MIT license, lightweight, no conflicts.

### Task 1.3: Integrate Sastrawi into BM25 Tokenizer
- **File**: `backend/retriever.py` lines 60-85
- **Change**: Replace `tokenize_indonesian()` function body:
  ```python
  from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
  
  # Module-level singleton (CachedStemmer is thread-safe)
  _stemmer_factory = StemmerFactory()
  _stemmer = _stemmer_factory.create_stemmer()
  
  def tokenize_indonesian(text: str) -> list[str]:
      text = text.lower()
      tokens = re.findall(r'\b[a-zA-Z0-9]+\b', text)
      stopwords = {
          "dan", "atau", "yang", "di", "ke", "dari", "untuk",
          "dengan", "pada", "ini", "itu", "adalah", "sebagai",
          "dalam", "oleh", "tidak", "akan", "dapat", "telah",
          "tersebut", "bahwa", "jika", "maka", "atas", "setiap",
      }
      filtered = [t for t in tokens if t not in stopwords and len(t) > 1]
      return [_stemmer.stem(t) for t in filtered]
  ```
- **Why**: Stemmed tokens match better across morphological variants. "mempekerjakan", "pekerja", "pekerjaan" all → "kerja".
- **Risk**: Slight startup time increase (~1s for stemmer factory initialization). Negligible at runtime due to CachedStemmer.
- **Verify**: BM25 search returns more relevant results for queries with affixed words.

---

## Phase 2: Embedding Model Upgrade (E5-base)

### Task 2.1: Update Embedding Constants
- **File**: `backend/retriever.py` lines 30-31
- **Change**:
  ```python
  EMBEDDING_MODEL = "intfloat/multilingual-e5-base"
  EMBEDDING_DIM = 768
  ```
- **File**: `backend/scripts/ingest.py` lines 23-24
- **Change**: Same constants update.
- **File**: `backend/rag_chain.py` line 40
- **Change**: Same model name update.
- **Why**: E5 models are specifically trained for retrieval (contrastive learning on query-passage pairs). MiniLM is a paraphrase model — optimized for similarity, not search. E5-base scores significantly higher on MTEB retrieval benchmarks for multilingual text.
- **Specs**: 768-dim, ~1.1GB, MIT license, supports 100+ languages including Indonesian.

### Task 2.2: Add E5 Query/Passage Prefix Wrapper
- **File**: `backend/retriever.py` — new class after imports
- **Change**: Create `E5Embeddings` wrapper:
  ```python
  class E5Embeddings:
      """Wrapper for E5 models that adds required query:/passage: prefixes."""
      
      def __init__(self, model_name: str):
          self._embedder = HuggingFaceEmbeddings(model_name=model_name)
      
      def embed_query(self, text: str) -> list[float]:
          return self._embedder.embed_query(f"query: {text}")
      
      def embed_documents(self, texts: list[str]) -> list[list[float]]:
          prefixed = [f"passage: {t}" for t in texts]
          return self._embedder.embed_documents(prefixed)
  ```
- **Why**: E5 models REQUIRE "query: " prefix for queries and "passage: " prefix for documents. Without prefixes, retrieval quality drops dramatically (confirmed by intfloat docs and multiple production codebases).
- **Risk**: Must ensure BOTH retriever and ingest use prefixes consistently. Mismatched prefixes = broken search.

### Task 2.3: Update Retriever Embedder Initialization
- **File**: `backend/retriever.py` line 126
- **Change**:
  ```python
  # Old: self.embedder = HuggingFaceEmbeddings(model_name=embedding_model)
  # New:
  if "e5" in embedding_model.lower():
      self.embedder = E5Embeddings(model_name=embedding_model)
  else:
      self.embedder = HuggingFaceEmbeddings(model_name=embedding_model)
  ```
- **Why**: Backward-compatible — if someone switches back to a non-E5 model, it still works.

### Task 2.4: Update Ingest Pipeline for E5 Prefixes
- **File**: `backend/scripts/ingest.py` lines 290, 314-316
- **Change**:
  ```python
  # Line 290: Initialize E5-aware embedder
  embedder = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
  
  # Lines 314-316: Add passage prefix during embedding
  texts = [f"passage: {chunk['text']}" for chunk in chunks]
  embeddings = embedder.embed_documents(texts)
  ```
- **Why**: Documents must be embedded with "passage: " prefix to match queries embedded with "query: " prefix.
- **Note**: We use raw `HuggingFaceEmbeddings` here (not wrapper) and manually add prefix, since ingest only does documents.

### Task 2.5: Re-ingest All Documents
- **Command**: `cd backend && python scripts/ingest.py`
- **Why**: Collection must be recreated with 768-dim vectors. Old 384-dim vectors are incompatible.
- **Verify**: Qdrant collection has 768-dim config, ~227 points ingested, search returns results.

---

## Phase 3: Structure-Aware Legal Chunking

### Task 3.1: Create Legal Structure Parser
- **File**: `backend/scripts/ingest.py` — new function
- **Change**: Add `parse_legal_structure()` function:
  ```python
  import re
  
  def parse_legal_structure(text: str, metadata: dict) -> list[dict]:
      """
      Parse Indonesian legal text into structural chunks.
      
      Splits by Pasal/Ayat boundaries while preserving parent context.
      Falls back to character-based chunking if no structure detected.
      """
      # Regex patterns for Indonesian legal structure
      pasal_pattern = r'(?=Pasal\s+(\d+))'
      ayat_pattern = r'(?=\((\d+)\)\s)'
      
      # Try to split by Pasal first
      pasal_splits = re.split(pasal_pattern, text)
      
      if len(pasal_splits) <= 1:
          # No Pasal structure found — fall back to chunk_text()
          return None  # Signal to use fallback
      
      chunks = []
      # Build parent context prefix
      doc_title = metadata.get("judul", "")
      doc_type = metadata.get("jenis_dokumen", "")
      doc_nomor = metadata.get("nomor", "")
      doc_tahun = metadata.get("tahun", "")
      parent_prefix = f"{doc_type} No. {doc_nomor} Tahun {doc_tahun}"
      if doc_title:
          parent_prefix += f" tentang {doc_title}"
      
      # Process each Pasal
      i = 1  # Skip preamble (index 0)
      while i < len(pasal_splits) - 1:
          pasal_num = pasal_splits[i]
          pasal_text = pasal_splits[i + 1].strip()
          
          # Inject parent context
          chunk_text = f"[{parent_prefix}, Pasal {pasal_num}]\n\n{pasal_text}"
          
          chunk_meta = {**metadata, "pasal": pasal_num}
          chunks.append({
              "text": chunk_text,
              "metadata": chunk_meta,
          })
          i += 2
      
      return chunks
  ```
- **Why**: Legal documents have natural semantic boundaries (Pasal = article, Ayat = clause). Chunking by structure preserves meaning better than arbitrary character splits. Parent context injection ("UU 40/2007 Pasal 7") helps the model understand which law each chunk belongs to.
- **Risk**: Not all documents have clean Pasal structure. Fallback to character-based chunking handles this.

### Task 3.2: Integrate Structure Parser into create_document_chunks()
- **File**: `backend/scripts/ingest.py` — modify `create_document_chunks()` function
- **Change**: Try structure-aware parsing first, fall back to character-based:
  ```python
  def create_document_chunks(documents):
      chunks = []
      for doc in documents:
          text = doc.get("text", "")
          if not text:
              continue
          
          metadata = {
              "jenis_dokumen": doc.get("jenis_dokumen", ""),
              "nomor": doc.get("nomor", ""),
              "tahun": doc.get("tahun", 0),
              "judul": doc.get("judul", ""),
              "tentang": doc.get("tentang", ""),
          }
          for field in ["bab", "pasal", "ayat"]:
              if field in doc:
                  metadata[field] = doc[field]
          
          # Try structure-aware parsing first
          structured = parse_legal_structure(text, metadata)
          
          if structured:
              # Use structure-aware chunks
              for chunk_data in structured:
                  cid = generate_citation_id(chunk_data["metadata"])
                  cit = format_citation(chunk_data["metadata"])
                  # If chunk is too long, sub-split it
                  sub_chunks = chunk_text(chunk_data["text"], chunk_size=500, overlap=100)
                  for idx, sub in enumerate(sub_chunks):
                      suffix = f"_chunk{idx+1}" if len(sub_chunks) > 1 else ""
                      part_label = f" (bagian {idx+1})" if len(sub_chunks) > 1 else ""
                      chunks.append({
                          "text": sub,
                          "citation_id": f"{cid}{suffix}",
                          "citation": f"{cit}{part_label}",
                          "metadata": chunk_data["metadata"],
                      })
          else:
              # Fallback to character-based chunking
              base_cid = generate_citation_id(metadata)
              base_cit = format_citation(metadata)
              text_chunks = chunk_text(text, chunk_size=500, overlap=100)
              for idx, piece in enumerate(text_chunks):
                  suffix = f"_chunk{idx+1}" if len(text_chunks) > 1 else ""
                  part_label = f" (bagian {idx+1})" if len(text_chunks) > 1 else ""
                  chunks.append({
                      "text": piece,
                      "citation_id": f"{base_cid}{suffix}",
                      "citation": f"{base_cit}{part_label}",
                      "metadata": metadata,
                  })
      return chunks
  ```

### Task 3.3: Re-ingest with New Chunking
- **Command**: `cd backend && python scripts/ingest.py`
- **Note**: This combines with Phase 2 re-ingestion — only need to run once after both Phase 2 + 3 are done.
- **Verify**: Check chunk count (should be different from 227), verify chunks have parent context prefixes.

---

## Phase 4: Query Classification + Per-Type Prompts

### Task 4.1: Create Query Classifier
- **File**: `backend/rag_chain.py` — new function after constants
- **Change**: Add keyword-based `classify_query()`:
  ```python
  def classify_query(question: str) -> str:
      """
      Classify legal question into type for prompt routing.
      
      Types:
      - 'definition': "Apa itu...", "Apa yang dimaksud..."
      - 'procedure': "Bagaimana cara...", "Langkah-langkah..."
      - 'requirement': "Apa syarat...", "Persyaratan..."
      - 'sanction': "Apa sanksi...", "Hukuman...", "Denda..."
      - 'comparison': "Apa perbedaan...", "Bandingkan..."
      - 'general': default fallback
      """
      q = question.lower().strip()
      
      if any(p in q for p in ["apa itu", "apa yang dimaksud", "definisi", "pengertian", "maksud dari"]):
          return "definition"
      elif any(p in q for p in ["bagaimana cara", "langkah", "prosedur", "proses", "tahapan", "cara mendirikan", "cara membuat"]):
          return "procedure"
      elif any(p in q for p in ["syarat", "persyaratan", "ketentuan", "wajib", "harus", "perlu"]):
          return "requirement"
      elif any(p in q for p in ["sanksi", "hukuman", "denda", "pidana", "pelanggaran", "ancaman"]):
          return "sanction"
      elif any(p in q for p in ["perbedaan", "bandingkan", "dibandingkan", "versus", "beda"]):
          return "comparison"
      else:
          return "general"
  ```
- **Why**: Different question types benefit from different prompt structures. A definition question should produce a concise explanation, while a procedure question should produce step-by-step instructions.
- **Risk**: Low. Keyword matching is simple and predictable. Misclassification just falls back to general prompt.

### Task 4.2: Create Per-Type Prompt Templates
- **File**: `backend/rag_chain.py` — after SYSTEM_PROMPT
- **Change**: Add type-specific instruction suffixes:
  ```python
  QUERY_TYPE_INSTRUCTIONS = {
      "definition": """
  Fokus jawaban:
  - Berikan definisi resmi dari peraturan yang relevan
  - Jelaskan ruang lingkup dan batasan definisi tersebut
  - Sebutkan pasal yang memuat definisi tersebut""",
  
      "procedure": """
  Fokus jawaban:
  - Jelaskan langkah-langkah secara berurutan (gunakan numbered list)
  - Sebutkan dokumen/persyaratan yang diperlukan di setiap langkah
  - Cantumkan estimasi waktu jika tersedia dalam dokumen
  - Sebutkan instansi yang bertanggung jawab""",
  
      "requirement": """
  Fokus jawaban:
  - Daftar semua persyaratan yang disebutkan dalam dokumen
  - Kelompokkan persyaratan wajib vs opsional jika ada
  - Sebutkan konsekuensi jika persyaratan tidak dipenuhi""",
  
      "sanction": """
  Fokus jawaban:
  - Sebutkan jenis sanksi (administratif, pidana, perdata)
  - Cantumkan besaran denda atau hukuman secara spesifik
  - Jelaskan kondisi/pelanggaran yang memicu sanksi tersebut
  - Sebutkan pasal yang mengatur sanksi""",
  
      "comparison": """
  Fokus jawaban:
  - Jelaskan setiap konsep secara terpisah terlebih dahulu
  - Identifikasi persamaan dan perbedaan utama
  - Gunakan struktur yang jelas untuk memudahkan perbandingan""",
  
      "general": "",  # No additional instructions
  }
  ```

### Task 4.3: Route Query to Appropriate Prompt
- **File**: `backend/rag_chain.py` — modify `query()` method (line ~562) and `query_stream()` method (line ~711)
- **Change**: In both methods, before building user_prompt:
  ```python
  # Classify query and add type-specific instructions
  query_type = classify_query(question)
  type_instructions = QUERY_TYPE_INSTRUCTIONS.get(query_type, "")
  
  user_prompt = USER_PROMPT_TEMPLATE.format(
      context=context,
      question=question,
  )
  
  # Append type-specific instructions if available
  if type_instructions:
      user_prompt += f"\n\n{type_instructions}"
  ```
- **Verify**: Different question types produce appropriately structured answers.

---

## Phase 5: Answer Grounding Verification (HHEM)

### Task 5.1: Load Vectara HHEM Model
- **File**: `backend/rag_chain.py` — in `LegalRAGChain.__init__()`
- **Change**: Add HHEM model loading:
  ```python
  # In __init__, after self.top_k = top_k:
  self.grounding_model = None
  try:
      from sentence_transformers import CrossEncoder
      logger.info("Loading Vectara HHEM grounding model...")
      self.grounding_model = CrossEncoder('vectara/hallucination_evaluation_model')
      logger.info("HHEM grounding model loaded successfully")
  except Exception as e:
      logger.warning(f"Failed to load HHEM model, grounding verification disabled: {e}")
  ```
- **Why**: HHEM (Hughes Hallucination Evaluation Model) checks if each claim in the answer is actually supported by the source passages. This is NLI-based verification, not just citation counting.
- **Risk**: Model is ~500MB download on first load. May add ~1-2s to first request. Graceful fallback if loading fails.

### Task 5.2: Create Grounding Verification Function
- **File**: `backend/rag_chain.py` — new method in `LegalRAGChain`
- **Change**:
  ```python
  def _verify_grounding(
      self,
      answer: str,
      citations: list[dict],
      results: list[SearchResult],
  ) -> dict:
      """
      Verify answer grounding using Vectara HHEM model.
      
      Splits answer into sentences, scores each against source passages.
      Returns grounding score and list of potentially ungrounded claims.
      """
      if not self.grounding_model:
          return {"grounding_score": None, "ungrounded_claims": []}
      
      import re
      # Split answer into sentences
      sentences = [s.strip() for s in re.split(r'[.!?]\s+', answer) if len(s.strip()) > 20]
      
      if not sentences:
          return {"grounding_score": 1.0, "ungrounded_claims": []}
      
      # Combine all source texts
      source_text = " ".join([r.text for r in results[:5]])
      
      # Score each sentence against source
      pairs = [[sentence, source_text] for sentence in sentences]
      
      try:
          scores = self.grounding_model.predict(pairs)
          
          # Identify ungrounded claims (score < 0.5)
          ungrounded = []
          for sentence, score in zip(sentences, scores):
              if float(score) < 0.5:
                  ungrounded.append(sentence[:100])  # Truncate for display
          
          avg_score = float(sum(scores)) / len(scores) if scores.any() else 0.0
          
          return {
              "grounding_score": round(avg_score, 4),
              "ungrounded_claims": ungrounded[:3],  # Max 3 warnings
          }
      except Exception as e:
          logger.warning(f"Grounding verification failed: {e}")
          return {"grounding_score": None, "ungrounded_claims": []}
  ```

### Task 5.3: Integrate Grounding into query() and query_stream()
- **File**: `backend/rag_chain.py`
- **Change in query()**: After `_validate_answer()`, add:
  ```python
  grounding = self._verify_grounding(answer, citations, results)
  ```
  Store grounding data in the RAGResponse (extend dataclass or add to validation dict).

- **Change in query_stream()**: After streaming completes and full_answer is assembled, add:
  ```python
  grounding = self._verify_grounding(full_answer, citations, results)
  # Include in "done" event
  yield ("done", {
      "validation": validation.to_dict(),
      "grounding": grounding,
  })
  ```

### Task 5.4: Update API Models for Grounding Data
- **File**: `backend/main.py`
- **Change**: Add grounding fields to `ValidationInfo`:
  ```python
  class ValidationInfo(BaseModel):
      is_valid: bool
      citation_coverage: float
      warnings: list[str] = []
      hallucination_risk: str
      grounding_score: float | None = Field(default=None, description="Skor grounding NLI 0.0-1.0")
      ungrounded_claims: list[str] = Field(default=[], description="Klaim yang tidak didukung sumber")
  ```

### Task 5.5: Display Grounding Score in Frontend
- **File**: `frontend/src/components/StreamingAnswerCard.tsx`
- **Change**: Add grounding score display near the confidence bar:
  ```tsx
  {grounding?.grounding_score != null && (
    <div className="flex items-center gap-2">
      <span className="text-sm text-gray-500">Grounding:</span>
      <div className="flex-1 bg-gray-200 rounded-full h-2">
        <div
          className={`h-2 rounded-full ${
            grounding.grounding_score >= 0.7 ? 'bg-green-500' :
            grounding.grounding_score >= 0.5 ? 'bg-yellow-500' : 'bg-red-500'
          }`}
          style={{ width: `${grounding.grounding_score * 100}%` }}
        />
      </div>
      <span className="text-sm font-medium">
        {(grounding.grounding_score * 100).toFixed(0)}%
      </span>
    </div>
  )}
  ```
- **Also show warnings if ungrounded claims exist.**

---

## Phase 6: Testing & Commit

### Task 6.1: Verify Backend Starts
- **Command**: `cd backend && uvicorn main:app --reload --port 8000`
- **Check**: No import errors, all models loaded, Qdrant connected.

### Task 6.2: End-to-End Test
- **Test queries** (one per query type):
  1. Definition: "Apa itu NIB?"
  2. Procedure: "Bagaimana cara mendirikan PT?"
  3. Requirement: "Apa syarat pendirian PT?"
  4. Sanction: "Apa sanksi pelanggaran UU Cipta Kerja?"
  5. General: "Jelaskan tentang OSS"
- **Verify per query**: Streaming works, confidence > 70%, grounding score shown, citations present.

### Task 6.3: Run pytest
- **Command**: `cd backend && pytest tests/ -v`
- **Fix any failures** caused by model/constant changes.

### Task 6.4: LSP Diagnostics
- Run `lsp_diagnostics` on all changed Python files.

### Task 6.5: Git Commit & Push
- Stage all changes.
- Commit: `feat: upgrade ML pipeline with E5 embeddings, Sastrawi stemmer, query classification, and HHEM grounding`
- Push to origin/main.

---

## Execution Order

```
Phase 1 (Quick Wins)     →  1.1, 1.2, 1.3
Phase 4 (Query Class.)   →  4.1, 4.2, 4.3    (can be done in parallel with Phase 2/3)
Phase 2 (Embedding)      →  2.1, 2.2, 2.3, 2.4
Phase 3 (Chunking)       →  3.1, 3.2
                         →  Re-ingest (2.5 + 3.3 combined — single run)
Phase 5 (Grounding)      →  5.1, 5.2, 5.3, 5.4, 5.5
Phase 6 (Test & Commit)  →  6.1, 6.2, 6.3, 6.4, 6.5
```

**Rationale for order**: Phase 1 and 4 are code-only (no re-ingestion needed). Phase 2 and 3 both require re-ingestion, so do them together and re-ingest once. Phase 5 is independent of retrieval changes. Phase 6 validates everything.

## Files Modified (Summary)

| File | Changes |
|------|---------|
| `backend/retriever.py` | E5Embeddings wrapper, model constants, Sastrawi tokenizer |
| `backend/rag_chain.py` | Temperature, query classifier, per-type prompts, HHEM grounding |
| `backend/scripts/ingest.py` | Model constants, passage prefix, structure-aware chunking |
| `backend/main.py` | ValidationInfo grounding fields |
| `backend/requirements.txt` | Add `PySastrawi>=1.0.1` |
| `frontend/src/components/StreamingAnswerCard.tsx` | Grounding score display |

## New Dependencies
| Package | Version | License | Size | Purpose |
|---------|---------|---------|------|---------|
| `PySastrawi` | >=1.0.1 | MIT | ~2MB | Indonesian stemmer for BM25 |
| `intfloat/multilingual-e5-base` | - | MIT | ~1.1GB | Search-tuned embeddings (auto-downloaded by HuggingFace) |
| `vectara/hallucination_evaluation_model` | - | Apache 2.0 | ~500MB | NLI grounding verification (auto-downloaded by sentence-transformers) |
