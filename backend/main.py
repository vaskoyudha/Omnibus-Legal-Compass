"""
FastAPI Backend for Omnibus Legal Compass

Indonesian Legal Q&A API with RAG using NVIDIA NIM Llama 3.1.
Provides legal document search, Q&A with citations, and health checks.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from pypdf import PdfReader
import io

from backend.rag_chain import LegalRAGChain, RAGResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global RAG chain instance (initialized on startup)
rag_chain: LegalRAGChain | None = None


# =============================================================================
# Pydantic Models
# =============================================================================


class QuestionRequest(BaseModel):
    """Request model for asking questions."""

    question: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Pertanyaan tentang peraturan Indonesia",
        examples=["Apa itu Undang-Undang Cipta Kerja?"],
    )
    jenis_dokumen: str | None = Field(
        default=None,
        description="Filter berdasarkan jenis dokumen (UU, PP, Perpres, Perda, dll)",
        examples=["UU", "PP"],
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Jumlah dokumen yang diambil untuk konteks",
    )


class FollowUpRequest(BaseModel):
    """Request model for follow-up questions with history."""

    question: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Pertanyaan lanjutan",
    )
    chat_history: list[dict[str, str]] = Field(
        default=[],
        description="Riwayat percakapan sebelumnya",
        examples=[[{"question": "Apa itu UU Cipta Kerja?", "answer": "..."}]],
    )
    jenis_dokumen: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class CitationInfo(BaseModel):
    """Citation information for a source."""

    number: int
    citation_id: str
    citation: str
    score: float
    metadata: dict[str, Any] = {}


class QuestionResponse(BaseModel):
    """Response model for Q&A endpoint."""

    answer: str = Field(description="Jawaban dalam Bahasa Indonesia dengan sitasi")
    citations: list[CitationInfo] = Field(description="Daftar sitasi terstruktur")
    sources: list[str] = Field(description="Daftar sumber dalam format ringkas")
    confidence: str = Field(
        description="Tingkat kepercayaan: tinggi, sedang, rendah, tidak ada"
    )
    processing_time_ms: float = Field(description="Waktu pemrosesan dalam milidetik")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    qdrant_connected: bool
    llm_configured: bool
    collection_count: int | None
    version: str


class ComplianceIssue(BaseModel):
    """Single compliance issue detected."""

    issue: str = Field(description="Deskripsi masalah kepatuhan")
    severity: str = Field(
        description="Tingkat keparahan: tinggi, sedang, rendah"
    )
    regulation: str = Field(description="Peraturan terkait")
    pasal: str | None = Field(default=None, description="Pasal spesifik jika ada")
    recommendation: str = Field(description="Rekomendasi perbaikan")


class ComplianceRequest(BaseModel):
    """Request model for compliance check via JSON."""

    business_description: str = Field(
        ...,
        min_length=10,
        max_length=10000,
        description="Deskripsi bisnis atau kegiatan yang akan diperiksa",
        examples=["Saya ingin membuka usaha restoran di Jakarta"],
    )


class ComplianceResponse(BaseModel):
    """Response for compliance check."""

    compliant: bool = Field(description="Apakah bisnis kemungkinan patuh")
    risk_level: str = Field(
        description="Tingkat risiko keseluruhan: tinggi, sedang, rendah"
    )
    summary: str = Field(description="Ringkasan hasil pemeriksaan kepatuhan")
    issues: list[ComplianceIssue] = Field(
        default=[], description="Daftar masalah kepatuhan yang terdeteksi"
    )
    recommendations: list[str] = Field(
        default=[], description="Rekomendasi umum untuk kepatuhan"
    )
    citations: list[CitationInfo] = Field(
        default=[], description="Sitasi peraturan terkait"
    )
    processing_time_ms: float = Field(description="Waktu pemrosesan dalam milidetik")


# =============================================================================
# Lifespan Event Handler
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup, cleanup on shutdown."""
    global rag_chain

    logger.info("Starting up Omnibus Legal Compass API...")

    try:
        # Initialize RAG chain (this also initializes retriever and LLM client)
        rag_chain = LegalRAGChain()
        logger.info("RAG chain initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RAG chain: {e}")
        # Don't raise - allow app to start for health checks
        rag_chain = None

    yield

    # Cleanup
    logger.info("Shutting down Omnibus Legal Compass API...")
    rag_chain = None


# =============================================================================
# FastAPI Application
# =============================================================================


app = FastAPI(
    title="Omnibus Legal Compass API",
    description="""
    API untuk sistem Q&A hukum Indonesia menggunakan RAG (Retrieval-Augmented Generation).
    
    ## Fitur Utama
    
    - **Tanya Jawab Hukum**: Ajukan pertanyaan tentang peraturan Indonesia dan dapatkan jawaban dengan sitasi
    - **Filter Dokumen**: Filter berdasarkan jenis dokumen (UU, PP, Perpres, dll)
    - **Percakapan Lanjutan**: Dukung pertanyaan lanjutan dengan konteks percakapan
    
    ## Teknologi
    
    - NVIDIA NIM dengan Llama 3.1 8B Instruct
    - Qdrant Vector Database dengan Hybrid Search
    - HuggingFace Embeddings (paraphrase-multilingual-MiniLM-L12-v2)
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# CORS Middleware - allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Exception Handlers
# =============================================================================


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "Terjadi kesalahan internal. Silakan coba lagi.",
        },
    )


# =============================================================================
# API Endpoints
# =============================================================================


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Health check endpoint for monitoring.

    Returns system status including Qdrant connection and LLM configuration.
    """
    global rag_chain

    qdrant_connected = False
    collection_count = None
    llm_configured = False

    if rag_chain is not None:
        try:
            # Check Qdrant connection
            collection_info = rag_chain.retriever.qdrant_client.get_collection(
                rag_chain.retriever.collection_name
            )
            qdrant_connected = True
            collection_count = collection_info.points_count
        except Exception as e:
            logger.warning(f"Qdrant health check failed: {e}")

        # Check LLM client
        llm_configured = rag_chain.llm_client is not None

    return HealthResponse(
        status="healthy" if (qdrant_connected and llm_configured) else "degraded",
        qdrant_connected=qdrant_connected,
        llm_configured=llm_configured,
        collection_count=collection_count,
        version="1.0.0",
    )


@app.post("/api/ask", response_model=QuestionResponse, tags=["Q&A"])
async def ask_question(request: QuestionRequest):
    """
    Tanya jawab hukum Indonesia.

    Ajukan pertanyaan tentang peraturan perundang-undangan Indonesia.
    Jawaban akan disertai dengan sitasi ke dokumen sumber.

    ## Contoh Request

    ```json
    {
        "question": "Apa itu Undang-Undang Cipta Kerja?",
        "jenis_dokumen": null,
        "top_k": 5
    }
    ```

    ## Response

    - **answer**: Jawaban dalam Bahasa Indonesia dengan sitasi [1], [2], dll
    - **citations**: Detail sitasi terstruktur
    - **sources**: Daftar sumber ringkas
    - **confidence**: Tingkat kepercayaan berdasarkan kualitas retrieval
    """
    global rag_chain

    if rag_chain is None:
        raise HTTPException(
            status_code=503,
            detail="RAG chain not initialized. Please check system health.",
        )

    start_time = time.perf_counter()

    try:
        # Query RAG chain
        response: RAGResponse = rag_chain.query(
            question=request.question,
            filter_jenis_dokumen=request.jenis_dokumen,
            top_k=request.top_k,
        )

        processing_time = (time.perf_counter() - start_time) * 1000

        # Convert citations to Pydantic models
        citations = [
            CitationInfo(
                number=c["number"],
                citation_id=c["citation_id"],
                citation=c["citation"],
                score=c["score"],
                metadata=c.get("metadata", {}),
            )
            for c in response.citations
        ]

        return QuestionResponse(
            answer=response.answer,
            citations=citations,
            sources=response.sources,
            confidence=response.confidence,
            processing_time_ms=round(processing_time, 2),
        )

    except Exception as e:
        logger.error(f"Error processing question: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process question: {str(e)}",
        )


@app.post("/api/ask/followup", response_model=QuestionResponse, tags=["Q&A"])
async def ask_followup(request: FollowUpRequest):
    """
    Pertanyaan lanjutan dengan konteks percakapan.

    Gunakan endpoint ini untuk pertanyaan lanjutan yang membutuhkan
    konteks dari percakapan sebelumnya.

    ## Contoh Request

    ```json
    {
        "question": "Bagaimana dengan sanksinya?",
        "chat_history": [
            {
                "question": "Apa itu UU Cipta Kerja?",
                "answer": "UU Cipta Kerja adalah..."
            }
        ]
    }
    ```
    """
    global rag_chain

    if rag_chain is None:
        raise HTTPException(
            status_code=503,
            detail="RAG chain not initialized. Please check system health.",
        )

    start_time = time.perf_counter()

    try:
        response: RAGResponse = rag_chain.query_with_history(
            question=request.question,
            chat_history=request.chat_history,
            filter_jenis_dokumen=request.jenis_dokumen,
            top_k=request.top_k,
        )

        processing_time = (time.perf_counter() - start_time) * 1000

        citations = [
            CitationInfo(
                number=c["number"],
                citation_id=c["citation_id"],
                citation=c["citation"],
                score=c["score"],
                metadata=c.get("metadata", {}),
            )
            for c in response.citations
        ]

        return QuestionResponse(
            answer=response.answer,
            citations=citations,
            sources=response.sources,
            confidence=response.confidence,
            processing_time_ms=round(processing_time, 2),
        )

    except Exception as e:
        logger.error(f"Error processing followup: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process followup: {str(e)}",
        )


@app.get("/api/document-types", tags=["Metadata"])
async def get_document_types():
    """
    Daftar jenis dokumen yang tersedia untuk filter.

    Returns daftar jenis dokumen (UU, PP, Perpres, dll) yang dapat
    digunakan sebagai filter pada endpoint /api/ask.
    """
    return {
        "document_types": [
            {"code": "UU", "name": "Undang-Undang"},
            {"code": "PP", "name": "Peraturan Pemerintah"},
            {"code": "Perpres", "name": "Peraturan Presiden"},
            {"code": "Perda", "name": "Peraturan Daerah"},
            {"code": "Permen", "name": "Peraturan Menteri"},
            {"code": "Kepmen", "name": "Keputusan Menteri"},
            {"code": "Pergub", "name": "Peraturan Gubernur"},
            {"code": "Perbup", "name": "Peraturan Bupati"},
            {"code": "Perwal", "name": "Peraturan Walikota"},
        ]
    }


@app.post("/api/compliance/check", response_model=ComplianceResponse, tags=["Compliance"])
async def check_compliance(
    business_description: str = Form(None),
    pdf_file: UploadFile = File(None),
):
    """
    Periksa kepatuhan bisnis terhadap peraturan Indonesia.

    Dapat menerima deskripsi teks **ATAU** file PDF.

    ## Input Options

    1. **Teks**: Kirim `business_description` sebagai form field
    2. **PDF**: Upload file PDF yang berisi deskripsi bisnis

    ## Contoh Use Cases

    - Memeriksa kepatuhan usaha restoran
    - Menganalisis dokumen bisnis untuk compliance
    - Identifikasi izin yang diperlukan

    ## Response

    - **compliant**: Apakah bisnis kemungkinan patuh
    - **risk_level**: tinggi / sedang / rendah
    - **issues**: Daftar masalah kepatuhan yang terdeteksi
    - **recommendations**: Rekomendasi perbaikan
    - **citations**: Sitasi ke peraturan terkait
    """
    global rag_chain

    if rag_chain is None:
        raise HTTPException(
            status_code=503,
            detail="RAG chain not initialized. Please check system health.",
        )

    start_time = time.perf_counter()

    # Get text content from either source
    text_content: str | None = None

    # Option 1: PDF file uploaded
    if pdf_file and pdf_file.filename:
        try:
            logger.info(f"Processing PDF file: {pdf_file.filename}")
            pdf_content = await pdf_file.read()
            pdf_reader = PdfReader(io.BytesIO(pdf_content))
            
            extracted_texts = []
            for page_num, page in enumerate(pdf_reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    extracted_texts.append(page_text)
            
            text_content = "\n".join(extracted_texts)
            logger.info(f"Extracted {len(extracted_texts)} pages, {len(text_content)} characters")
            
        except Exception as e:
            logger.error(f"Failed to parse PDF: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Gagal membaca file PDF: {str(e)}",
            )

    # Option 2: Text description provided
    elif business_description:
        text_content = business_description

    # Validate we have content
    if not text_content or len(text_content.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Deskripsi bisnis diperlukan. Kirim 'business_description' atau upload file PDF.",
        )

    # Truncate if too long (to fit in LLM context)
    max_chars = 8000
    if len(text_content) > max_chars:
        text_content = text_content[:max_chars] + "..."
        logger.warning(f"Truncated input to {max_chars} characters")

    try:
        # Build compliance analysis prompt
        compliance_prompt = f"""Anda adalah ahli hukum Indonesia yang menganalisis kepatuhan bisnis.

Analisis deskripsi bisnis berikut terhadap peraturan Indonesia yang relevan:

---
{text_content}
---

Berikan analisis kepatuhan dengan format berikut:

1. **KESIMPULAN**: Apakah bisnis ini kemungkinan PATUH atau TIDAK PATUH
2. **TINGKAT RISIKO**: tinggi / sedang / rendah
3. **RINGKASAN**: Ringkasan singkat hasil analisis (2-3 kalimat)
4. **MASALAH YANG TERDETEKSI** (jika ada):
   - Masalah 1: [deskripsi], Peraturan: [nama peraturan], Pasal: [nomor], Tingkat: [tinggi/sedang/rendah], Rekomendasi: [saran]
   - Masalah 2: ...
5. **REKOMENDASI UMUM**: Daftar langkah-langkah yang harus diambil

Jika informasi tidak cukup untuk memberikan analisis yang akurat, sampaikan keterbatasan tersebut.
Selalu kutip sumber peraturan yang relevan."""

        # Query RAG chain
        response = rag_chain.query(
            question=compliance_prompt,
            top_k=5,
        )

        processing_time = (time.perf_counter() - start_time) * 1000

        # Parse the response to extract structured data
        answer_lower = response.answer.lower()
        
        # Determine compliance status
        is_compliant = "patuh" in answer_lower and "tidak patuh" not in answer_lower
        
        # Determine risk level
        if "tingkat risiko: tinggi" in answer_lower or "risiko tinggi" in answer_lower:
            risk_level = "tinggi"
        elif "tingkat risiko: rendah" in answer_lower or "risiko rendah" in answer_lower:
            risk_level = "rendah"
        else:
            risk_level = "sedang"

        # Extract recommendations from the answer
        recommendations = []
        if "rekomendasi" in answer_lower:
            # Simple extraction - lines after "rekomendasi"
            lines = response.answer.split("\n")
            in_recommendations = False
            for line in lines:
                if "rekomendasi" in line.lower():
                    in_recommendations = True
                    continue
                if in_recommendations and line.strip().startswith("-"):
                    rec = line.strip().lstrip("-").strip()
                    if rec and len(rec) > 5:
                        recommendations.append(rec)
                elif in_recommendations and line.strip() and not line.strip().startswith("-"):
                    if "masalah" in line.lower() or "**" in line:
                        in_recommendations = False

        # Build citations
        citations = [
            CitationInfo(
                number=c["number"],
                citation_id=c["citation_id"],
                citation=c["citation"],
                score=c["score"],
                metadata=c.get("metadata", {}),
            )
            for c in response.citations
        ]

        # Extract issues (simplified - could be enhanced with more parsing)
        issues: list[ComplianceIssue] = []
        if "masalah" in answer_lower and "tidak" in answer_lower:
            # There are likely issues - create a generic one based on risk
            if risk_level == "tinggi":
                issues.append(
                    ComplianceIssue(
                        issue="Potensi pelanggaran terdeteksi berdasarkan analisis",
                        severity="tinggi",
                        regulation="Lihat sitasi untuk detail peraturan",
                        pasal=None,
                        recommendation="Konsultasikan dengan ahli hukum untuk detail lebih lanjut",
                    )
                )

        return ComplianceResponse(
            compliant=is_compliant,
            risk_level=risk_level,
            summary=response.answer[:500] + "..." if len(response.answer) > 500 else response.answer,
            issues=issues,
            recommendations=recommendations[:5],  # Limit to 5 recommendations
            citations=citations,
            processing_time_ms=round(processing_time, 2),
        )

    except Exception as e:
        logger.error(f"Error processing compliance check: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Gagal memproses pemeriksaan kepatuhan: {str(e)}",
        )


@app.get("/", tags=["System"])
async def root():
    """Root endpoint - API info."""
    return {
        "name": "Omnibus Legal Compass API",
        "version": "1.0.0",
        "description": "Indonesian Legal Q&A API with RAG",
        "docs": "/docs",
        "health": "/health",
    }


# =============================================================================
# Main Entry Point
# =============================================================================


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
