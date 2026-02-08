# Draft: Omnibus Legal Compass (Indonesian Legal RAG)

> **Status**: Interview in Progress
> **Created**: 2026-02-09
> **Last Updated**: 2026-02-09

---

## Requirements (Confirmed)

### Core Concept
- RAG system for Indonesian legal documents
- Target users: Business owners, students navigating Indonesian bureaucracy
- Key challenge: UU Cipta Kerja, Perda vs. National UU complexity

### Technical Stack (CONFIRMED ✅)
- **LLM**: NVIDIA NIM with Kimi 2.5 (FREE tier)
- **Embeddings**: NVIDIA NIM Embeddings (via same API)
- **API Integration**: Python (LangChain) with `langchain-nvidia-ai-endpoints`
- **Vector DB**: Qdrant (self-hosted or cloud)
- **Backend**: Python (FastAPI) with LangChain
- **Frontend**: Next.js Web App
- **Data Source**: Open-Technology-Foundation/peraturan.go.id (541K segments!)
- **OCR**: PyMuPDF + Tesseract (for any new PDFs)
- **Auth**: None (Public Access)
- **Testing**: TDD (Test-Driven Development)

### Key Features (Discussed)
1. **JDIH Scraping**: Extract PDFs from JDIH websites
2. **Smart Chunking**: Custom splitter for "Pasal", "Ayat", "Bab" structures
3. **Citation Mode**: AI provides citations with links to source
4. **Hybrid Search**: Semantic + Keyword (BM25)

---

## Open Questions (To Clarify)

### Data Scope (CONFIRMED ✅)
- [x] Source: **peraturan.go.id dataset** (5,817 docs, 541,445 segments)
- [x] Volume: Pre-processed dataset (no scraping needed for MVP!)
- [x] Embedding Model: NVIDIA NIM Embeddings
- [x] Test Strategy: TDD (Test-Driven Development)

### Technical Decisions
- [ ] Cloud-hosted vs Self-hosted preference?
- [ ] LLM choice: GPT-4o (easier, API cost) vs Llama-3 (self-hosted, needs GPU)?
- [ ] Vector DB: Qdrant (self-hosted) vs Pinecone (managed)?

### Feature Priority (CONFIRMED ✅)
- [x] MVP scope: **FULL SUITE** (Q&A + Citations + Compliance Checker + Form Guidance)
- [x] Jurisdiction: National (JDIHN) first, provinces in Phase 2
- [x] Authentication: None (Public Access)
- [x] Compliance Checker: Text Input + PDF Upload (both options)

### Deployment Target
- [ ] Web app? Mobile? API-only?
- [ ] Expected concurrent users?

---

## Research Findings (COMPLETED ✅)

### NVIDIA NIM + Kimi 2.5 Integration
- **Package**: `langchain-nvidia-ai-endpoints` 
- **Model Card**: https://build.nvidia.com/moonshotai/kimi-k2.5/modelcard
- **Capabilities**: 1T multimodal MoE, supports text + image understanding
- **License**: NVIDIA Open Model License (commercial OK)
- **LangChain Integration**: Full support via `ChatNVIDIA` class

### JDIHN Scraping Discovery
- **URL Pattern**: `https://jdihn.go.id/pencarian/detail/{id}` (IDs up to ~1.9M)
- **Reference Scraper**: PHP DiDOM example on dev.to (by Eko Priyanto)
- **Data Schema**: asal_dokumen, jenis_dokumen, nomor, tahun, judul, etc.

### Existing Open-Source Solutions (CRITICAL!)
1. **Open-Technology-Foundation/peraturan.go.id**
   - 5,817 Indonesian legal documents (2001-2025)
   - 541,445 pre-segmented text chunks
   - Could potentially USE this instead of scraping from scratch!
   
2. **JohnAmadeo/indolaw**
   - Python parser for Indonesian law PDFs
   - Understands Pasal/Ayat/Bab structure
   - Next.js + React frontend demo

### Academic Research
- **BRIN Study**: RAG for maritime law Q&A in Indonesia
- **ITK Paper**: "RAG for Indonesian Criminal Law using LLaMA" (2025)
- **ITS Research**: Linked Open Legal Data Indonesia using schema.org/Legislation

### Chunking Best Practices (from research)
1. Context-aware chunking preserves legal structure
2. Semantic chunking for related articles
3. Recursive character splitting as fallback
4. Always prepend metadata: [Source: UU X, Bab Y, Pasal Z]

---

## Technical Decisions (To Be Made)

| Decision | Options | Rationale |
|----------|---------|-----------|
| PDF Processing | Tesseract / Azure Doc AI / Google Vision | Depends on OCR quality needs |
| Embedding Model | OpenAI / IndoBERT / Multilingual-E5 | Depends on Bahasa accuracy |
| Chunking Strategy | Pasal-aware / Recursive / Semantic | Must preserve legal context |
| Search Type | Hybrid (BM25 + Dense) | Legal terms need exact match |

---

## Scope Boundaries (To Confirm)

### IN SCOPE (Proposed)
- JDIH document scraping and processing
- RAG pipeline with citation
- Web-based Q&A interface
- Basic jurisdiction filtering

### OUT OF SCOPE (Proposed)
- [ ] Mobile app (Phase 2?)
- [ ] Document drafting/generation
- [ ] Multi-language support
- [ ] Real-time regulation updates

---

## Notes from Brainstorming Session

### User's Original Vision
> "A RAG system specifically tuned for Bahasa Indonesia Hukum (Legal Indonesian)"
> "The AI doesn't just answer. It provides Citations."

### Key Technical Challenges Identified
1. **OCR Quality**: Many JDIH PDFs are scanned images
2. **Regulatory Conflicts**: Lex superior derogat legi inferiori handling
3. **Legal Language**: "Bahasa Hukum" differs from conversational Indonesian
4. **Context Preservation**: Ayat without Pasal context is useless

### Product Ideas Discussed
- Citation Mode with dual-view (Summary + Original PDF)
- Location/Jurisdiction Awareness
- Legal Compliance Checker (upload business plan)
- Form Generator for NIB/OSS guidance
