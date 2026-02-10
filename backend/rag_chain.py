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
TEMPERATURE = 0.2

# Retriever configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "indonesian_legal_docs")
EMBEDDING_MODEL = "intfloat/multilingual-e5-base"


# Chain-of-Thought Legal Reasoning System Prompt
SYSTEM_PROMPT = """Anda adalah asisten hukum Indonesia yang ahli dan terpercaya. Tugas Anda adalah menjawab pertanyaan tentang peraturan perundang-undangan Indonesia.

## CARA MENJAWAB:

1. **Analisis Internal** (jangan tampilkan ke pengguna):
   - Identifikasi jenis pertanyaan (definisi, prosedur, persyaratan, sanksi)
   - Evaluasi relevansi setiap dokumen yang diberikan
   - Prioritaskan: UU > PP > Perpres > Permen

2. **Format Jawaban** (yang ditampilkan ke pengguna):
   - Tulis jawaban dalam paragraf yang mengalir secara alami
   - JANGAN gunakan header markdown (##, ###, dll)
   - Gunakan Bahasa Indonesia formal yang mudah dipahami
   - Setiap klaim penting HARUS disertai nomor sitasi [1], [2], dst dalam teks
   - Buat paragraf terpisah untuk topik berbeda (gunakan baris kosong)
   - Gunakan bullet points (-) atau numbered list hanya jika perlu untuk langkah-langkah

## ATURAN KETAT:

1. HANYA jawab berdasarkan dokumen yang diberikan - JANGAN mengarang
2. Jika informasi tidak ada dalam dokumen, katakan: "Berdasarkan dokumen yang tersedia, informasi tentang [topik] tidak ditemukan."
3. Pastikan setiap paragraf memiliki minimal 2-3 kalimat untuk kejelasan
4. Akhiri dengan satu kalimat tentang tingkat keyakinan jawaban

## CONTOH FORMAT YANG BAIK:

"Pendirian Perseroan Terbatas (PT) di Indonesia diatur dalam Undang-Undang Nomor 40 Tahun 2007 tentang Perseroan Terbatas [1]. Syarat utama pendirian PT meliputi minimal dua orang pendiri yang merupakan Warga Negara Indonesia atau badan hukum [1].

Modal dasar PT minimal sebesar Rp50.000.000 (lima puluh juta rupiah), dimana 25% harus disetor pada saat pendirian [2]. Akta pendirian harus dibuat oleh notaris dalam Bahasa Indonesia [1].

Berdasarkan dokumen yang tersedia, jawaban ini memiliki tingkat keyakinan tinggi karena didukung langsung oleh pasal-pasal dalam UU PT."

## YANG HARUS DIHINDARI:
- Jangan tulis "## JAWABAN UTAMA" atau header serupa
- Jangan tulis "## TINGKAT KEPERCAYAAN" sebagai header
- Jangan buat daftar sumber terpisah di akhir
- Jangan gunakan format yang kaku atau template"""


USER_PROMPT_TEMPLATE = """Berdasarkan dokumen hukum berikut, jawab pertanyaan dengan jelas dan terstruktur.

DOKUMEN HUKUM:
{context}

PERTANYAAN:
{question}

INSTRUKSI:
- Jawab dalam paragraf yang mengalir alami (BUKAN dengan header markdown)
- Sertakan nomor sitasi [1], [2] dst dalam kalimat untuk setiap fakta penting
- Pisahkan paragraf dengan baris kosong untuk keterbacaan
- Gunakan Bahasa Indonesia formal yang mudah dipahami
- Akhiri dengan satu kalimat singkat tentang tingkat keyakinan jawaban

JAWABAN:"""


def classify_query(question: str) -> str:
    """
    Classify legal question into type for prompt routing.
    
    Types: definition, procedure, requirement, sanction, comparison, general
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

    "general": "",
}


@dataclass
class ConfidenceScore:
    """Confidence score with numeric value and text label."""
    
    numeric: float  # 0.0 to 1.0
    label: str  # tinggi, sedang, rendah, tidak ada
    top_score: float  # Best retrieval score
    avg_score: float  # Average retrieval score
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "numeric": float(round(self.numeric, 4)),
            "label": self.label,
            "top_score": float(round(self.top_score, 4)),
            "avg_score": float(round(self.avg_score, 4)),
        }


@dataclass
class ValidationResult:
    """Result of answer validation/self-reflection."""
    
    is_valid: bool
    citation_coverage: float  # 0.0 to 1.0
    warnings: list[str] = field(default_factory=list)
    hallucination_risk: str = "low"  # low, medium, high
    missing_citations: list[int] = field(default_factory=list)
    grounding_score: float | None = None
    ungrounded_claims: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "citation_coverage": float(round(self.citation_coverage, 2)),
            "warnings": self.warnings,
            "hallucination_risk": self.hallucination_risk,
            "missing_citations": self.missing_citations,
            "grounding_score": self.grounding_score,
            "ungrounded_claims": self.ungrounded_claims,
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
    
    def generate_stream(
        self,
        user_message: str,
        system_message: str | None = None,
    ):
        """Generate streaming response from NVIDIA NIM API. Yields chunks of text."""
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
            "stream": True,
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=120,
                stream=True,
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]  # Remove 'data: ' prefix
                        if data == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data)
                            if 'choices' in chunk and len(chunk['choices']) > 0:
                                delta = chunk['choices'][0].get('delta', {})
                                content = delta.get('content', '')
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
        
        except requests.exceptions.RequestException as e:
            logger.error(f"NVIDIA NIM API streaming error: {e}")
            raise RuntimeError(f"Failed to get streaming response from NVIDIA NIM: {e}") from e


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
        
        # HHEM grounding model (lazy-loaded on first use to reduce startup memory)
        self.grounding_model = None
        self._hhem_loaded = False
    
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
                "score": float(round(result.score, 4)),
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
        """
        Assess confidence using multi-factor heuristics:
        1. Retrieval scores (top + average)
        2. Document type authority (UU > PP > Perpres > Permen)
        3. Score distribution (consistency across results)
        4. Number of relevant documents found
        """
        if not results:
            return ConfidenceScore(
                numeric=0.0,
                label="tidak ada",
                top_score=0.0,
                avg_score=0.0,
            )
        
        scores = [r.score for r in results]
        top_score = scores[0]
        avg_score = sum(scores) / len(scores)
        
        # Factor 1: Base retrieval score (40% weight)
        # Normalize and weight top score more heavily
        base_score = (top_score * 0.7) + (avg_score * 0.3)
        
        # Factor 2: Document authority hierarchy (20% weight)
        # Higher authority documents = more confidence
        authority_weights = {
            'UU': 1.0,      # Undang-Undang (highest)
            'PP': 0.9,      # Peraturan Pemerintah
            'Perpres': 0.8, # Peraturan Presiden
            'Permen': 0.7,  # Peraturan Menteri
            'Perda': 0.6,   # Peraturan Daerah
        }
        
        authority_scores = []
        for r in results[:3]:  # Consider top 3 results
            doc_type = r.metadata.get('jenis_dokumen', '')
            authority = authority_weights.get(doc_type, 0.5)
            authority_scores.append(authority * r.score)
        
        authority_factor = sum(authority_scores) / len(authority_scores) if authority_scores else 0.5
        
        # Factor 3: Score distribution / consistency (20% weight)
        # If scores are consistent (low variance), higher confidence
        if len(scores) > 1:
            score_variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
            # Lower variance = higher consistency factor (inverse relationship)
            consistency_factor = max(0.3, 1.0 - (score_variance * 2))
        else:
            consistency_factor = 0.7  # Single result, moderate confidence
        
        # Factor 4: Result count factor (20% weight)
        # More relevant results = higher confidence (up to a point)
        high_quality_results = sum(1 for s in scores if s > 0.3)
        if high_quality_results >= 4:
            count_factor = 1.0
        elif high_quality_results >= 2:
            count_factor = 0.8
        elif high_quality_results >= 1:
            count_factor = 0.6
        else:
            count_factor = 0.3
        
        # Combine all factors with weights
        numeric = (
            base_score * 0.40 +
            authority_factor * 0.20 +
            consistency_factor * 0.20 +
            count_factor * 0.20
        )
        
        # Apply calibration to make scores more realistic
        # Boost mid-range scores, cap very high scores
        if numeric > 0.85:
            numeric = 0.85 + (numeric - 0.85) * 0.5  # Diminishing returns above 85%
        elif numeric < 0.3:
            numeric = numeric * 0.8  # Penalize low scores more
        
        numeric = min(1.0, max(0.0, numeric))  # Clamp to 0-1
        
        # Determine label based on calibrated thresholds
        if numeric >= 0.65:
            label = "tinggi"
        elif numeric >= 0.40:
            label = "sedang"
        else:
            label = "rendah"
        
        logger.debug(
            f"Confidence calculation: base={base_score:.3f}, authority={authority_factor:.3f}, "
            f"consistency={consistency_factor:.3f}, count={count_factor:.3f} -> final={numeric:.3f}"
        )
        
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
    
    def _verify_grounding(
        self,
        answer: str,
        results: list[SearchResult],
    ) -> dict:
        """
        Verify answer grounding using Vectara HHEM model.
        
        Splits answer into sentences, scores each against source passages.
        Returns grounding score and list of potentially ungrounded claims.
        """
        # Lazy-load HHEM on first call
        if not self._hhem_loaded:
            self._hhem_loaded = True
            try:
                from sentence_transformers import CrossEncoder
                logger.info("Loading Vectara HHEM grounding model (lazy)...")
                self.grounding_model = CrossEncoder('vectara/hallucination_evaluation_model', trust_remote_code=True)
                logger.info("HHEM grounding model loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load HHEM model, grounding verification disabled: {e}")
        
        if not self.grounding_model:
            return {"grounding_score": None, "ungrounded_claims": []}
        
        # Split answer into sentences (only meaningful ones)
        sentences = [s.strip() for s in re.split(r'[.!?]\s+', answer) if len(s.strip()) > 20]
        
        if not sentences:
            return {"grounding_score": 1.0, "ungrounded_claims": []}
        
        # Combine source texts
        source_text = " ".join([r.text for r in results[:5]])
        
        # Score each sentence against source
        pairs = [[sentence, source_text] for sentence in sentences]
        
        try:
            scores = self.grounding_model.predict(pairs)
            
            # Identify ungrounded claims (score < 0.5)
            ungrounded = []
            for sentence, score in zip(sentences, scores):
                if float(score) < 0.5:
                    ungrounded.append(sentence[:100])
            
            avg_score = float(sum(scores)) / len(scores) if len(scores) > 0 else 0.0
            
            return {
                "grounding_score": round(avg_score, 4),
                "ungrounded_claims": ungrounded[:3],
            }
        except Exception as e:
            logger.warning(f"Grounding verification failed: {e}")
            return {"grounding_score": None, "ungrounded_claims": []}
    
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
                expand_queries=True,
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
        query_type = classify_query(question)
        type_instructions = QUERY_TYPE_INSTRUCTIONS.get(query_type, "")
        
        user_prompt = USER_PROMPT_TEMPLATE.format(
            context=context,
            question=question,
        )
        
        if type_instructions:
            user_prompt += f"\n\n{type_instructions}"
        
        logger.info(f"Generating answer with NVIDIA NIM {NVIDIA_MODEL}...")
        answer = self.llm_client.generate(
            user_message=user_prompt,
            system_message=SYSTEM_PROMPT,
        )
        
        # Step 4: Validate answer for citation accuracy
        validation = self._validate_answer(answer, citations)
        if validation.warnings:
            logger.warning(f"Answer validation warnings: {validation.warnings}")
        
        # Step 5: Verify grounding
        grounding = self._verify_grounding(answer, results)
        if validation and grounding.get("grounding_score") is not None:
            validation.grounding_score = grounding["grounding_score"]
            validation.ungrounded_claims = grounding["ungrounded_claims"]
        
        # Step 6: Build response
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
    
    def query_stream(
        self,
        question: str,
        filter_jenis_dokumen: str | None = None,
        top_k: int | None = None,
    ):
        """
        Streaming version of query() that yields answer chunks.
        
        Yields tuples of (event_type, data):
        - ("metadata", {citations, sources, confidence_score})
        - ("chunk", "text chunk")
        - ("done", {validation})
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
                expand_queries=True,
            )
        
        # Handle no results
        if not results:
            yield ("metadata", {
                "citations": [],
                "sources": [],
                "confidence_score": {
                    "numeric": 0.0,
                    "label": "tidak ada",
                    "top_score": 0.0,
                    "avg_score": 0.0,
                },
            })
            yield ("chunk", "Maaf, saya tidak menemukan dokumen yang relevan dengan pertanyaan Anda dalam database.")
            yield ("done", {
                "validation": {
                    "is_valid": True,
                    "citation_coverage": 0.0,
                    "warnings": [],
                    "hallucination_risk": "low",
                    "missing_citations": [],
                }
            })
            return
        
        # Step 2: Format context and send metadata first
        context, citations = self._format_context(results)
        sources = self._extract_sources(citations)
        confidence = self._assess_confidence(results)
        
        # Send metadata immediately so frontend can show sources while waiting for answer
        yield ("metadata", {
            "citations": citations,
            "sources": sources,
            "confidence_score": confidence.to_dict(),
        })
        
        # Step 3: Generate answer using streaming LLM
        query_type = classify_query(question)
        type_instructions = QUERY_TYPE_INSTRUCTIONS.get(query_type, "")
        
        user_prompt = USER_PROMPT_TEMPLATE.format(
            context=context,
            question=question,
        )
        
        if type_instructions:
            user_prompt += f"\n\n{type_instructions}"
        
        logger.info(f"Streaming answer with NVIDIA NIM {NVIDIA_MODEL}...")
        
        full_answer = ""
        for chunk in self.llm_client.generate_stream(
            user_message=user_prompt,
            system_message=SYSTEM_PROMPT,
        ):
            full_answer += chunk
            yield ("chunk", chunk)
        
        # Step 4: Validate answer for citation accuracy
        validation = self._validate_answer(full_answer, citations)
        if validation.warnings:
            logger.warning(f"Answer validation warnings: {validation.warnings}")
        
        # Step 5: Verify grounding
        grounding = self._verify_grounding(full_answer, results)
        if grounding.get("grounding_score") is not None:
            validation.grounding_score = grounding["grounding_score"]
            validation.ungrounded_claims = grounding["ungrounded_claims"]
        
        yield ("done", {
            "validation": validation.to_dict(),
        })


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
