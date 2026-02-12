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
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request

from pypdf import PdfReader
import io

from rag_chain import LegalRAGChain, RAGResponse

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


class ConfidenceScoreInfo(BaseModel):
    """Numeric confidence score details."""
    
    numeric: float = Field(description="Nilai kepercayaan 0.0 sampai 1.0")
    label: str = Field(description="Label kepercayaan: tinggi, sedang, rendah, tidak ada")
    top_score: float = Field(description="Skor tertinggi dari retrieval")
    avg_score: float = Field(description="Skor rata-rata dari retrieval")


class ValidationInfo(BaseModel):
    """Answer validation details."""
    
    is_valid: bool = Field(description="Apakah jawaban valid tanpa peringatan")
    citation_coverage: float = Field(description="Persentase sumber yang dikutip 0.0-1.0")
    warnings: list[str] = Field(default=[], description="Daftar peringatan validasi")
    hallucination_risk: str = Field(description="Risiko halusinasi: low, medium, high")


class QuestionResponse(BaseModel):
    """Response model for Q&A endpoint."""

    answer: str = Field(description="Jawaban dalam Bahasa Indonesia dengan sitasi")
    citations: list[CitationInfo] = Field(description="Daftar sitasi terstruktur")
    sources: list[str] = Field(description="Daftar sumber dalam format ringkas")
    confidence: str = Field(
        description="Tingkat kepercayaan: tinggi, sedang, rendah, tidak ada"
    )
    confidence_score: ConfidenceScoreInfo | None = Field(
        default=None, description="Detail skor kepercayaan numerik"
    )
    validation: ValidationInfo | None = Field(
        default=None, description="Hasil validasi jawaban"
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


class GuidanceRequest(BaseModel):
    """Request model for business formation guidance."""

    business_type: str = Field(
        ...,
        description="Jenis badan usaha: PT, CV, UMKM, Koperasi, Yayasan, Firma, Perorangan",
        examples=["PT", "CV", "UMKM"],
    )
    industry: str | None = Field(
        default=None,
        description="Sektor industri: F&B, Retail, Teknologi, Manufaktur, Jasa, dll",
        examples=["F&B", "Retail", "Teknologi"],
    )
    location: str | None = Field(
        default=None,
        description="Lokasi usaha (provinsi/kota)",
        examples=["Jakarta", "Surabaya", "Bandung"],
    )


class GuidanceStep(BaseModel):
    """Single step in business formation guidance."""

    step_number: int = Field(description="Nomor langkah")
    title: str = Field(description="Judul langkah")
    description: str = Field(description="Deskripsi detail langkah")
    requirements: list[str] = Field(default=[], description="Dokumen/syarat yang diperlukan")
    estimated_time: str = Field(description="Estimasi waktu penyelesaian")
    fees: str | None = Field(default=None, description="Estimasi biaya jika ada")


class GuidanceResponse(BaseModel):
    """Response for business formation guidance."""

    business_type: str = Field(description="Jenis badan usaha yang diminta")
    business_type_name: str = Field(description="Nama lengkap jenis badan usaha")
    summary: str = Field(description="Ringkasan panduan pendirian")
    steps: list[GuidanceStep] = Field(description="Langkah-langkah pendirian usaha")
    total_estimated_time: str = Field(description="Total estimasi waktu seluruh proses")
    required_permits: list[str] = Field(description="Daftar izin yang diperlukan")
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

# Rate limiting (in-memory, per IP)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


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
            collection_info = rag_chain.retriever.client.get_collection(
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
@limiter.limit("20/minute")
async def ask_question(request: Request, body: QuestionRequest):
    """
    Tanya jawab hukum Indonesia.

    Ajukan pertanyaan tentang peraturan perundang-undangan Indonesia.
    Jawaban akan disertai dengan sitasi ke dokumen sumber.

    Rate limited: 20 requests per minute per IP

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
            question=body.question,
            filter_jenis_dokumen=body.jenis_dokumen,
            top_k=body.top_k,
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

        # Build confidence score info if available
        confidence_score_info = None
        if response.confidence_score:
            confidence_score_info = ConfidenceScoreInfo(
                numeric=response.confidence_score.numeric,
                label=response.confidence_score.label,
                top_score=response.confidence_score.top_score,
                avg_score=response.confidence_score.avg_score,
            )
        
        # Build validation info if available
        validation_info = None
        if response.validation:
            validation_info = ValidationInfo(
                is_valid=response.validation.is_valid,
                citation_coverage=response.validation.citation_coverage,
                warnings=response.validation.warnings,
                hallucination_risk=response.validation.hallucination_risk,
            )

        return QuestionResponse(
            answer=response.answer,
            citations=citations,
            sources=response.sources,
            confidence=response.confidence,
            confidence_score=confidence_score_info,
            validation=validation_info,
            processing_time_ms=round(processing_time, 2),
        )

    except Exception as e:
        logger.error(f"Error processing question: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process question: {str(e)}",
        )


@app.post("/api/ask/stream", tags=["Q&A"])
@limiter.limit("20/minute")
async def ask_question_stream(request: Request, body: QuestionRequest):
    """
    Streaming version of Q&A endpoint using Server-Sent Events.

    Rate limited: 20 requests per minute per IP
    
    Returns a stream of events:
    - metadata: Citations and sources (sent first)
    - chunk: Text chunks of the answer
    - done: Final validation info
    
    ## Example Usage (JavaScript)
    
    ```javascript
    const response = await fetch('/api/ask/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: 'Apa itu PT?' })
    });
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const text = decoder.decode(value);
        // Parse SSE events
    }
    ```
    """
    global rag_chain

    if rag_chain is None:
        raise HTTPException(
            status_code=503,
            detail="RAG chain not initialized. Please check system health.",
        )

    import json

    def event_generator():
        start_time = time.perf_counter()
        
        try:
            for event_type, data in rag_chain.query_stream(
                question=body.question,
                filter_jenis_dokumen=body.jenis_dokumen,
                top_k=body.top_k,
            ):
                if event_type == "metadata":
                    yield f"event: metadata\ndata: {json.dumps(data)}\n\n"
                elif event_type == "chunk":
                    yield f"event: chunk\ndata: {json.dumps({'text': data})}\n\n"
                elif event_type == "done":
                    processing_time = (time.perf_counter() - start_time) * 1000
                    data["processing_time_ms"] = round(processing_time, 2)
                    yield f"event: done\ndata: {json.dumps(data)}\n\n"
        except Exception as e:
            logger.error(f"Error in stream: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/ask/followup", response_model=QuestionResponse, tags=["Q&A"])
@limiter.limit("20/minute")
async def ask_followup(request: Request, body: FollowUpRequest):
    """
    Pertanyaan lanjutan dengan konteks percakapan.

    Gunakan endpoint ini untuk pertanyaan lanjutan yang membutuhkan
    konteks dari percakapan sebelumnya.

    Rate limited: 20 requests per minute per IP

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
            question=body.question,
            chat_history=body.chat_history,
            filter_jenis_dokumen=body.jenis_dokumen,
            top_k=body.top_k,
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

        # Build confidence score info if available
        confidence_score_info = None
        if response.confidence_score:
            confidence_score_info = ConfidenceScoreInfo(
                numeric=response.confidence_score.numeric,
                label=response.confidence_score.label,
                top_score=response.confidence_score.top_score,
                avg_score=response.confidence_score.avg_score,
            )
        
        # Build validation info if available
        validation_info = None
        if response.validation:
            validation_info = ValidationInfo(
                is_valid=response.validation.is_valid,
                citation_coverage=response.validation.citation_coverage,
                warnings=response.validation.warnings,
                hallucination_risk=response.validation.hallucination_risk,
            )

        return QuestionResponse(
            answer=response.answer,
            citations=citations,
            sources=response.sources,
            confidence=response.confidence,
            confidence_score=confidence_score_info,
            validation=validation_info,
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
@limiter.limit("10/minute")
async def check_compliance(
    request: Request,
    business_description: str = Form(None),
    pdf_file: UploadFile = File(None),
):
    """
    Periksa kepatuhan bisnis terhadap peraturan Indonesia.

    Dapat menerima deskripsi teks **ATAU** file PDF.

    Rate limited: 10 requests per minute per IP

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


# =============================================================================
# Guidance Endpoint - Business Formation Guide
# =============================================================================

# Business type mappings
BUSINESS_TYPE_NAMES = {
    "PT": "Perseroan Terbatas",
    "CV": "Commanditaire Vennootschap (Persekutuan Komanditer)",
    "UMKM": "Usaha Mikro, Kecil, dan Menengah",
    "Koperasi": "Koperasi",
    "Yayasan": "Yayasan",
    "Firma": "Persekutuan Firma",
    "Perorangan": "Usaha Perorangan / UD",
}


def parse_guidance_steps(answer: str) -> list[GuidanceStep]:
    """Parse LLM response into structured guidance steps."""
    steps = []
    lines = answer.split("\n")
    current_step = None
    step_number = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Detect step headers (numbered items or "Langkah X")
        is_step_header = False
        if line.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.")):
            is_step_header = True
        elif "langkah" in line.lower() and any(c.isdigit() for c in line[:20]):
            is_step_header = True
        elif line.startswith("**") and any(c.isdigit() for c in line[:10]):
            is_step_header = True

        if is_step_header:
            # Save previous step if exists
            if current_step:
                steps.append(current_step)

            step_number += 1
            # Clean up the title
            title = line.lstrip("0123456789.-) ").strip()
            title = title.replace("**", "").strip()
            if title.lower().startswith("langkah"):
                title = title.split(":", 1)[-1].strip() if ":" in title else title

            current_step = GuidanceStep(
                step_number=step_number,
                title=title[:100] if title else f"Langkah {step_number}",
                description="",
                requirements=[],
                estimated_time="1-2 minggu",
                fees=None,
            )
        elif current_step:
            # Add content to current step
            if "waktu" in line.lower() or "hari" in line.lower() or "minggu" in line.lower():
                # Extract time estimate
                current_step.estimated_time = line[:50]
            elif "biaya" in line.lower() or "rp" in line.lower():
                # Extract fee info
                current_step.fees = line[:100]
            elif line.startswith("-") or line.startswith("•"):
                # Requirement item
                req = line.lstrip("-• ").strip()
                if req and len(req) > 3:
                    current_step.requirements.append(req[:150])
            else:
                # Add to description
                current_step.description += " " + line
                current_step.description = current_step.description.strip()[:500]

    # Add last step
    if current_step:
        steps.append(current_step)

    # Ensure at least one step exists
    if not steps:
        steps.append(
            GuidanceStep(
                step_number=1,
                title="Konsultasi Awal",
                description="Konsultasikan rencana pendirian usaha dengan notaris atau konsultan hukum untuk mendapatkan panduan yang sesuai dengan kondisi Anda.",
                requirements=["KTP", "NPWP", "Dokumen identitas lainnya"],
                estimated_time="1-2 minggu",
                fees="Bervariasi tergantung notaris",
            )
        )

    return steps


def extract_permits(answer: str) -> list[str]:
    """Extract required permits from the answer."""
    permits = []
    permit_keywords = [
        "NIB", "SIUP", "TDP", "NPWP", "SKT", "SKDP", "IMB", "Izin Usaha",
        "Izin Lokasi", "Izin Lingkungan", "AMDAL", "UKL-UPL", "Sertifikat",
        "OSS", "Akta Pendirian", "SK Kemenkumham", "Izin Prinsip",
    ]

    for keyword in permit_keywords:
        if keyword.lower() in answer.lower():
            permits.append(keyword)

    # Add mandatory permits based on common requirements
    if "NIB" not in permits:
        permits.insert(0, "NIB (Nomor Induk Berusaha)")

    return list(set(permits))[:10]  # Limit to 10 unique permits


@app.post("/api/guidance", response_model=GuidanceResponse, tags=["Guidance"])
@limiter.limit("20/minute")
async def get_business_guidance(request: Request, body: GuidanceRequest):
    """
    Panduan pendirian usaha berdasarkan jenis badan usaha.

    Endpoint ini memberikan panduan langkah demi langkah untuk mendirikan
    berbagai jenis badan usaha di Indonesia, termasuk persyaratan dokumen,
    estimasi waktu, dan biaya yang diperlukan.

    Rate limited: 20 requests per minute per IP

    **Jenis Badan Usaha yang Didukung:**
    - PT (Perseroan Terbatas)
    - CV (Commanditaire Vennootschap)
    - UMKM (Usaha Mikro, Kecil, dan Menengah)
    - Koperasi
    - Yayasan
    - Firma (Persekutuan Firma)
    - Perorangan (Usaha Perorangan / UD)

    Returns:
        GuidanceResponse dengan langkah-langkah pendirian dan sitasi peraturan
    """
    import time

    start_time = time.time()

    if rag_chain is None:
        raise HTTPException(
            status_code=503,
            detail="RAG chain belum diinisialisasi. Silakan coba lagi nanti.",
        )

    # Validate business type
    business_type = body.business_type.upper()
    if business_type not in BUSINESS_TYPE_NAMES and body.business_type not in BUSINESS_TYPE_NAMES:
        # Try to match common variations
        type_mapping = {
            "PERSEROAN": "PT",
            "PERSEROAN TERBATAS": "PT",
            "KOMANDITER": "CV",
            "PERSEKUTUAN": "Firma",
            "USAHA PERORANGAN": "Perorangan",
            "UD": "Perorangan",
        }
        business_type = type_mapping.get(business_type, body.business_type)

    business_type_name = BUSINESS_TYPE_NAMES.get(
        business_type, BUSINESS_TYPE_NAMES.get(body.business_type, body.business_type)
    )

    # Build the query for RAG
    industry_context = f" di sektor {body.industry}" if body.industry else ""
    location_context = f" di {body.location}" if body.location else ""

    query = f"""Berikan panduan lengkap langkah demi langkah untuk mendirikan {business_type_name} ({business_type}){industry_context}{location_context}.

Jelaskan secara detail:
1. Langkah-langkah pendirian dari awal sampai selesai
2. Dokumen yang diperlukan untuk setiap langkah
3. Estimasi waktu untuk setiap langkah
4. Estimasi biaya jika ada
5. Izin-izin yang diperlukan
6. Dasar hukum dan peraturan yang berlaku

Gunakan format bernomor untuk setiap langkah."""

    try:
        # Query the RAG chain
        response = await rag_chain.aquery(query)

        # Parse the response into structured steps
        steps = parse_guidance_steps(response.answer)

        # Extract required permits
        required_permits = extract_permits(response.answer)

        # Calculate total estimated time
        total_weeks = len(steps) * 2  # Rough estimate: 2 weeks per step
        if total_weeks <= 4:
            total_estimated_time = f"{total_weeks} minggu"
        else:
            total_estimated_time = f"{total_weeks // 4}-{(total_weeks // 4) + 1} bulan"

        # Build citations (matching CitationInfo model structure)
        citations = [
            CitationInfo(
                number=c["number"],
                citation_id=c["citation_id"],
                citation=c["citation"],
                score=c["score"],
                metadata=c.get("metadata", {}),
            )
            for c in response.citations[:5]  # Limit to 5 citations
        ]

        # Build summary
        summary = response.answer[:400] + "..." if len(response.answer) > 400 else response.answer
        # Clean up summary
        summary = summary.split("\n")[0] if "\n" in summary[:200] else summary

        processing_time = (time.time() - start_time) * 1000

        return GuidanceResponse(
            business_type=business_type,
            business_type_name=business_type_name,
            summary=summary,
            steps=steps,
            total_estimated_time=total_estimated_time,
            required_permits=required_permits,
            citations=citations,
            processing_time_ms=round(processing_time, 2),
        )

    except Exception as e:
        logger.error(f"Error processing guidance request: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Gagal memproses permintaan panduan: {str(e)}",
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
