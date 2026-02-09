"""
RAG Chain Module for Indonesian Legal Q&A

Uses NVIDIA NIM Kimi K2 as the LLM with custom retriever for legal documents.
Provides citations and "I don't know" guardrails.
"""

from __future__ import annotations

import asyncio
import os
import re
import json
import logging
from dataclasses import dataclass, field
from typing import Any

import requests
from dotenv import load_dotenv

from retriever import HybridRetriever, SearchResult

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_MODEL = "moonshotai/kimi-k2-instruct"  # Correct model name per NVIDIA docs
MAX_TOKENS = 4096
TEMPERATURE = 0.7

# Retriever configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "indonesian_legal_docs")
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


# Chain-of-Thought Legal Reasoning System Prompt
SYSTEM_PROMPT = """Anda adalah asisten hukum Indonesia yang ahli dan terpercaya. Tugas Anda adalah menjawab pertanyaan tentang peraturan perundang-undangan Indonesia menggunakan PENALARAN HUKUM TERSTRUKTUR.

## METODE PENALARAN (WAJIB DIIKUTI):

### LANGKAH 1 - IDENTIFIKASI MASALAH HUKUM
- Klasifikasi jenis pertanyaan: definisi, prosedur, persyaratan, sanksi, atau perbandingan
- Identifikasi bidang hukum yang relevan: perizinan, ketenagakerjaan, perpajakan, dll
- Tentukan kata kunci hukum yang penting

### LANGKAH 2 - ANALISIS SUMBER HUKUM
- Evaluasi setiap dokumen yang diberikan
- Prioritaskan berdasarkan: (1) Relevansi langsung, (2) Hierarki peraturan (UU > PP > Perpres > Permen), (3) Kebaruan tanggal
- Identifikasi pasal atau ketentuan spesifik yang menjawab pertanyaan

### LANGKAH 3 - PENERAPAN LOGIKA HUKUM
- Hubungkan ketentuan hukum dengan pertanyaan
- Jika ada beberapa sumber, jelaskan bagaimana mereka saling melengkapi
- Jika ada pertentangan antar sumber, jelaskan dengan prinsip lex specialis/lex posterior

### LANGKAH 4 - PENILAIAN KEPERCAYAAN
- Tinggi: Jawaban didukung langsung oleh pasal spesifik dalam UU/PP
- Sedang: Jawaban berdasarkan interpretasi atau peraturan pelaksana
- Rendah: Jawaban hanya sebagian didukung atau konteks terbatas
- Tidak Ada: Tidak ada sumber relevan dalam dokumen

### LANGKAH 5 - FORMULASI JAWABAN
- Susun jawaban yang jelas dan terstruktur
- Setiap klaim HARUS disertai sitasi [1], [2], dst
- Gunakan Bahasa Indonesia formal dan profesional

## ATURAN KETAT:
1. HANYA jawab berdasarkan dokumen yang diberikan - JANGAN mengarang
2. Jika informasi tidak ada, katakan dengan jelas: "Berdasarkan dokumen yang tersedia, saya tidak menemukan informasi spesifik tentang [topik]."
3. Jika ada ketidakpastian, nyatakan dengan jujur tingkat kepercayaan Anda
4. Bedakan antara ketentuan wajib (harus/wajib) dan pilihan (dapat/boleh)

## FORMAT OUTPUT:
Setelah melakukan penalaran di atas, berikan:
1. JAWABAN UTAMA dengan sitasi
2. TINGKAT KEPERCAYAAN (Tinggi/Sedang/Rendah) dengan alasan singkat
3. DAFTAR SUMBER yang dikutip"""


USER_PROMPT_TEMPLATE = """Gunakan metode PENALARAN HUKUM TERSTRUKTUR untuk menjawab pertanyaan berikut.

=== DOKUMEN HUKUM YANG TERSEDIA ===
{context}

=== PERTANYAAN ===
{question}

=== INSTRUKSI ===
1. Ikuti 5 LANGKAH penalaran hukum dalam system prompt
2. Berikan jawaban dengan SITASI untuk setiap fakta
3. Sertakan TINGKAT KEPERCAYAAN di akhir jawaban
4. Jika dokumen tidak cukup relevan, nyatakan dengan jelas

=== PENALARAN DAN JAWABAN ==="""


@dataclass
class ConfidenceScore:
    """Confidence score with numeric value and text label."""
    
    numeric: float  # 0.0 to 1.0
    label: str  # tinggi, sedang, rendah, tidak ada
    top_score: float  # Best retrieval score
    avg_score: float  # Average retrieval score
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "numeric": round(self.numeric, 4),
            "label": self.label,
            "top_score": round(self.top_score, 4),
            "avg_score": round(self.avg_score, 4),
        }


@dataclass
class ValidationResult:
    """Result of answer validation/self-reflection."""
    
    is_valid: bool
    citation_coverage: float  # 0.0 to 1.0
    warnings: list[str] = field(default_factory=list)
    hallucination_risk: str = "low"  # low, medium, high
    missing_citations: list[int] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "citation_coverage": round(self.citation_coverage, 2),
            "warnings": self.warnings,
            "hallucination_risk": self.hallucination_risk,
            "missing_citations": self.missing_citations,
        }


@dataclass
class RAGResponse:
    """Response from RAG chain with citations."""
    
    answer: str
    citations: list[dict[str, Any]]
    sources: list[str]
    confidence: str  # Kept for backward compatibility
    confidence_score: ConfidenceScore | None  # Numeric confidence
    raw_context: str
    validation: ValidationResult | None = None  # Answer validation result


class NVIDIANimClient:
    """Client for NVIDIA NIM API with Kimi K2 model (moonshotai/kimi-k2-instruct)."""
    
    def __init__(
        self,
        api_key: str | None = None,
        api_url: str = NVIDIA_API_URL,
        model: str = NVIDIA_MODEL,
        max_tokens: int = MAX_TOKENS,
        temperature: float = TEMPERATURE,
    ):
        self.api_key = api_key or NVIDIA_API_KEY
        if not self.api_key:
            raise ValueError("NVIDIA_API_KEY not found in environment variables")
        
        self.api_url = api_url
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    def generate(
        self,
        user_message: str,
        system_message: str | None = None,
    ) -> str:
        """Generate response from NVIDIA NIM API."""
        messages = []
        
        if system_message:
            messages.append({
                "role": "system",
                "content": system_message,
            })
        
        messages.append({
            "role": "user",
            "content": user_message,
        })
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False,
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            
            result = response.json()
            message = result["choices"][0]["message"]
            
            # Some models may return 'reasoning' or 'reasoning_content' instead of 'content'
            content = (
                message.get("content") 
                or message.get("reasoning") 
                or message.get("reasoning_content") 
                or ""
            )
            
            if not content:
                logger.warning(f"Empty response from model. Full message: {message}")
                
            return content
        
        except requests.exceptions.RequestException as e:
            logger.error(f"NVIDIA NIM API error: {e}")
            raise RuntimeError(f"Failed to get response from NVIDIA NIM: {e}") from e


class LegalRAGChain:
    """RAG Chain for Indonesian Legal Q&A with citations."""
    
    def __init__(
        self,
        retriever: HybridRetriever | None = None,
        llm_client: NVIDIANimClient | None = None,
        top_k: int = 5,
    ):
        # Initialize retriever
        if retriever is None:
            logger.info("Initializing HybridRetriever...")
            self.retriever = HybridRetriever(
                qdrant_url=QDRANT_URL,
                collection_name=COLLECTION_NAME,
                embedding_model=EMBEDDING_MODEL,
            )
        else:
            self.retriever = retriever
        
        # Initialize LLM client
        if llm_client is None:
            logger.info("Initializing NVIDIA NIM client...")
            self.llm_client = NVIDIANimClient()
        else:
            self.llm_client = llm_client
        
        self.top_k = top_k
    
    def _format_context(self, results: list[SearchResult]) -> tuple[str, list[dict]]:
        """Format search results into context with numbered citations."""
        context_parts = []
        citations = []
        
        for i, result in enumerate(results, 1):
            # Build citation info with text snippet included
            citation_info = {
                "number": i,
                "citation_id": result.citation_id,
                "citation": result.citation,
                "score": round(result.score, 4),
                "metadata": {
                    **result.metadata,
                    "text": result.text[:500] if result.text else "",  # Include text snippet
                },
            }
            citations.append(citation_info)
            
            # Format context block
            context_block = f"""[{i}] {result.citation}
{result.text}
---"""
            context_parts.append(context_block)
        
        return "\n\n".join(context_parts), citations
    
    def _extract_sources(self, citations: list[dict]) -> list[str]:
        """Extract formatted source list from citations."""
        sources = []
        for cit in citations:
            sources.append(f"[{cit['number']}] {cit['citation']}")
        return sources
    
    def _assess_confidence(self, results: list[SearchResult]) -> ConfidenceScore:
        """Assess confidence based on retrieval scores with numeric value."""
        if not results:
            return ConfidenceScore(
                numeric=0.0,
                label="tidak ada",
                top_score=0.0,
                avg_score=0.0,
            )
        
        top_score = results[0].score
        avg_score = sum(r.score for r in results) / len(results)
        
        # Calculate numeric confidence (weighted combination)
        # top_score weighted 60%, avg_score weighted 40%
        numeric = (top_score * 0.6) + (avg_score * 0.4)
        numeric = min(1.0, max(0.0, numeric))  # Clamp to 0-1
        
        # Determine label based on thresholds
        if top_score > 0.5 and avg_score > 0.3:
            label = "tinggi"
        elif top_score > 0.3 and avg_score > 0.15:
            label = "sedang"
        else:
            label = "rendah"
        
        return ConfidenceScore(
            numeric=numeric,
            label=label,
            top_score=top_score,
            avg_score=avg_score,
        )
    
    def _validate_answer(
        self,
        answer: str,
        citations: list[dict],
    ) -> ValidationResult:
        """Validate answer for citation accuracy and hallucination risk."""
        warnings: list[str] = []
        
        # Extract citation references from answer [1], [2], etc.
        cited_refs = set(int(m) for m in re.findall(r'\[(\d+)\]', answer))
        available_refs = set(c["number"] for c in citations)
        
        # Check for invalid citations (references that don't exist)
        invalid_refs = cited_refs - available_refs
        if invalid_refs:
            warnings.append(f"Referensi tidak valid: {sorted(invalid_refs)}")
        
        # Check citation coverage (how many available sources were used)
        if available_refs:
            coverage = len(cited_refs & available_refs) / len(available_refs)
        else:
            coverage = 0.0
        
        # Assess hallucination risk based on citation usage
        if not cited_refs:
            risk = "high"
            warnings.append("Jawaban tidak memiliki sitasi sama sekali")
        elif invalid_refs:
            risk = "medium"
        elif coverage < 0.3:
            risk = "medium"
            warnings.append("Hanya sedikit sumber yang dikutip")
        else:
            risk = "low"
        
        return ValidationResult(
            is_valid=len(warnings) == 0,
            citation_coverage=coverage,
            warnings=warnings,
            hallucination_risk=risk,
            missing_citations=sorted(invalid_refs),
        )
    
    def query(
        self,
        question: str,
        filter_jenis_dokumen: str | None = None,
        top_k: int | None = None,
    ) -> RAGResponse:
        """
        Query the RAG chain with a question.
        
        Args:
            question: User question in Indonesian
            filter_jenis_dokumen: Optional filter by document type (UU, PP, Perpres, etc.)
            top_k: Number of documents to retrieve
        
        Returns:
            RAGResponse with answer, citations, and sources
        """
        k = top_k or self.top_k
        
        # Step 1: Retrieve relevant documents
        logger.info(f"Retrieving documents for: {question[:50]}...")
        
        if filter_jenis_dokumen:
            results = self.retriever.search_by_document_type(
                query=question,
                jenis_dokumen=filter_jenis_dokumen,
                top_k=k,
            )
        else:
            results = self.retriever.hybrid_search(
                query=question,
                top_k=k,
            )
        
        # Handle no results
        if not results:
            return RAGResponse(
                answer="Maaf, saya tidak menemukan dokumen yang relevan dengan pertanyaan Anda dalam database.",
                citations=[],
                sources=[],
                confidence="tidak ada",
                confidence_score=ConfidenceScore(
                    numeric=0.0,
                    label="tidak ada",
                    top_score=0.0,
                    avg_score=0.0,
                ),
                raw_context="",
                validation=ValidationResult(
                    is_valid=True,
                    citation_coverage=0.0,
                    warnings=[],
                    hallucination_risk="low",
                    missing_citations=[],
                ),
            )
        
        # Step 2: Format context
        context, citations = self._format_context(results)
        sources = self._extract_sources(citations)
        confidence = self._assess_confidence(results)
        
        # Step 3: Generate answer using LLM
        user_prompt = USER_PROMPT_TEMPLATE.format(
            context=context,
            question=question,
        )
        
        logger.info(f"Generating answer with NVIDIA NIM {NVIDIA_MODEL}...")
        answer = self.llm_client.generate(
            user_message=user_prompt,
            system_message=SYSTEM_PROMPT,
        )
        
        # Step 4: Validate answer for citation accuracy
        validation = self._validate_answer(answer, citations)
        if validation.warnings:
            logger.warning(f"Answer validation warnings: {validation.warnings}")
        
        # Step 5: Build response
        return RAGResponse(
            answer=answer,
            citations=citations,
            sources=sources,
            confidence=confidence.label,  # String label for backward compatibility
            confidence_score=confidence,   # Full ConfidenceScore object
            raw_context=context,
            validation=validation,
        )
    
    def query_with_history(
        self,
        question: str,
        chat_history: list[dict[str, str]] | None = None,
        **kwargs,
    ) -> RAGResponse:
        """
        Query with conversation history for follow-up questions.
        
        Args:
            question: Current question
            chat_history: Previous Q&A pairs [{"question": ..., "answer": ...}, ...]
            **kwargs: Additional args passed to query()
        
        Returns:
            RAGResponse
        """
        # For follow-up questions, prepend context from history
        if chat_history:
            history_context = "\n".join([
                f"Q: {h['question']}\nA: {h['answer'][:200]}..."
                for h in chat_history[-3:]  # Last 3 turns
            ])
            enhanced_question = f"Konteks sebelumnya:\n{history_context}\n\nPertanyaan saat ini: {question}"
        else:
            enhanced_question = question
        
        return self.query(enhanced_question, **kwargs)
    
    async def aquery(
        self,
        question: str,
        filter_jenis_dokumen: str | None = None,
        top_k: int | None = None,
    ) -> RAGResponse:
        """
        Async version of query() for use with FastAPI async endpoints.
        
        Args:
            question: User question in Indonesian
            filter_jenis_dokumen: Optional filter by document type
            top_k: Number of documents to retrieve
        
        Returns:
            RAGResponse with answer, citations, and sources
        """
        # Run synchronous query in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.query(question, filter_jenis_dokumen, top_k)
        )


def main():
    """Test the RAG chain."""
    print("Initializing Legal RAG Chain...")
    
    try:
        rag = LegalRAGChain()
        
        # Test queries
        test_questions = [
            "Apa itu Undang-Undang Cipta Kerja?",
            "Bagaimana aturan tentang pelindungan data pribadi?",
            "Apa yang dimaksud dengan perizinan berusaha terintegrasi?",
        ]
        
        for question in test_questions:
            print(f"\n{'='*60}")
            print(f"PERTANYAAN: {question}")
            print("="*60)
            
            response = rag.query(question)
            
            print(f"\nJAWABAN:\n{response.answer}")
            print(f"\nKONFIDENSI: {response.confidence}")
            if response.confidence_score:
                print(f"  Numeric: {response.confidence_score.numeric:.2%}")
                print(f"  Top Score: {response.confidence_score.top_score:.4f}")
                print(f"  Avg Score: {response.confidence_score.avg_score:.4f}")
            if response.validation:
                print(f"\nVALIDASI:")
                print(f"  Valid: {response.validation.is_valid}")
                print(f"  Citation Coverage: {response.validation.citation_coverage:.0%}")
                print(f"  Hallucination Risk: {response.validation.hallucination_risk}")
                if response.validation.warnings:
                    print(f"  Warnings: {response.validation.warnings}")
            print(f"\nSUMBER:")
            for source in response.sources:
                print(f"  {source}")
    
    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
