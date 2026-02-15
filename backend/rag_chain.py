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
import time
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
TEMPERATURE = 0.15

# Retriever configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "indonesian_legal_docs")
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


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


# Verbatim mode - direct quotes without synthesis
VERBATIM_SYSTEM_PROMPT = """Anda adalah asisten hukum Indonesia. Tugas Anda adalah memberikan KUTIPAN LANGSUNG dari peraturan perundang-undangan.

## ATURAN KHUSUS MODE VERBATIM:

1. JANGAN membuat jawaban sendiri - hanya kutipkan teks dari dokumen yang diberikan
2. Untuk setiap fakta, gunakan format: "[nomor sumber] Kutipan teks asli dari dokumen"
3. Jika ada beberapa sumber yang mendukung fakta yang sama, cantumkan semua nomor: [1], [2]
4. Pertahankan bahasa asli dalam dokumen - jangan ubah kata-kata
5. Jika dokumen tidak memiliki informasi yang ditanyakan, katakan: "Tidak ditemukan informasi tentang [topik] dalam dokumen yang tersedia."

## CONTOH OUTPUT VERBATIM:

"Menurut Pasal 1 ayat (1) Undang-Undang Nomor 40 Tahun 2007 tentang Perseroan Terbatas, Perseroan Terbatas adalah badan hukum yang didirikan berdasarkan perjanjian... [1]

Pasal 7 ayat (1) menyatakan bahwa Pendirian Perseroan требует minimum dua pendiri... [1]"

## YANG HARUS DIHINDARI:
- Jangan menambahkan interpretasi atau penjelasan sendiri
- Jangan menggunakan kata "menurut saya" atau "analisis saya"
- Jangan menyimpang dari teks asli dalam dokumen"""


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
- PENTING: Setelah jawaban selesai, WAJIB tambahkan blok JSON metadata di baris baru terpisah dengan format:
```json
{{"cited_sources": [1, 2, 3]}}
```
  Isi cited_sources dengan nomor-nomor sumber yang benar-benar dikutip dalam jawaban.

JAWABAN:"""


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
    hallucination_risk: str = "low"  # low, medium, high, refused
    missing_citations: list[int] = field(default_factory=list)
    grounding_score: float | None = None  # LLM-as-judge grounding score 0-1
    ungrounded_claims: list[str] = field(default_factory=list)  # Claims not supported by sources
    
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
        
        max_retries = 3
        last_exception: Exception | None = None
        for attempt in range(max_retries):
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
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    logger.warning(
                        f"NVIDIA NIM API attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"NVIDIA NIM API error after {max_retries} attempts: {e}")
        
        raise RuntimeError(
            "Gagal mendapatkan respons dari layanan AI. Silakan coba lagi nanti."
        ) from last_exception
    
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
        
        max_retries = 3
        last_exception: Exception | None = None
        for attempt in range(max_retries):
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
                return  # Success — exit retry loop
            
            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    logger.warning(
                        f"NVIDIA NIM API streaming attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"NVIDIA NIM API streaming error after {max_retries} attempts: {e}")
        
        raise RuntimeError(
            "Gagal mendapatkan respons streaming dari layanan AI. Silakan coba lagi nanti."
        ) from last_exception


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
    
    @staticmethod
    def _extract_json_metadata(raw_answer: str) -> tuple[str, dict[str, Any] | None]:
        """
        Extract JSON metadata block from the end of an LLM response.
        
        The LLM is instructed to append a JSON block like:
        ```json
        {"cited_sources": [1, 2, 3]}
        ```
        
        Returns:
            Tuple of (clean_answer_text, parsed_json_or_None)
        """
        # Try to find JSON block at the end (with or without ```json wrapper)
        # Pattern 1: ```json\n{...}\n```
        json_block_match = re.search(
            r'```json\s*\n?\s*(\{[^`]*?\})\s*\n?\s*```\s*$',
            raw_answer,
            re.DOTALL,
        )
        if json_block_match:
            json_str = json_block_match.group(1)
            clean_answer = raw_answer[:json_block_match.start()].rstrip()
            try:
                parsed = json.loads(json_str)
                logger.info(f"Successfully parsed JSON metadata from LLM response: {list(parsed.keys())}")
                return clean_answer, parsed
            except json.JSONDecodeError as e:
                logger.warning(f"Found JSON block but failed to parse: {e}")
                return clean_answer, None
        
        # Pattern 2: bare JSON object at the end (no code fence)
        bare_json_match = re.search(
            r'\n\s*(\{"cited_sources"\s*:\s*\[[\d,\s]*\]\})\s*$',
            raw_answer,
        )
        if bare_json_match:
            json_str = bare_json_match.group(1)
            clean_answer = raw_answer[:bare_json_match.start()].rstrip()
            try:
                parsed = json.loads(json_str)
                logger.info(f"Successfully parsed bare JSON metadata from LLM response")
                return clean_answer, parsed
            except json.JSONDecodeError as e:
                logger.warning(f"Found bare JSON but failed to parse: {e}")
                return clean_answer, None
        
        # No JSON found — return original answer
        logger.debug("No JSON metadata block found in LLM response, will use regex fallback")
        return raw_answer, None

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
        json_cited_sources: list[int] | None = None,
    ) -> ValidationResult:
        """Validate answer for citation accuracy and hallucination risk.
        
        Args:
            answer: The LLM-generated answer text.
            citations: List of citation dicts with 'number' keys.
            json_cited_sources: If provided (from structured JSON output),
                use these directly instead of regex extraction. Falls back
                to regex if None.
        """
        warnings: list[str] = []
        
        # Extract citation references — prefer JSON-extracted, fallback to regex
        if json_cited_sources is not None:
            cited_refs = set(json_cited_sources)
            logger.debug(f"Using JSON-extracted cited_sources: {cited_refs}")
        else:
            # Fallback: regex extraction from answer text [1], [2], etc.
            cited_refs = set(int(m) for m in re.findall(r'\[(\d+)\]', answer))
            logger.debug(f"Using regex-extracted cited_sources: {cited_refs}")
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
        citations: list[dict[str, Any]],
    ) -> tuple[float | None, list[str]]:
        """
        Use LLM-as-judge to verify that answer claims are grounded in cited sources.
        
        Returns:
            Tuple of (grounding_score, ungrounded_claims)
        """
        if not citations:
            return None, ["Tidak ada sumber untuk diverifikasi"]
        
        # Format sources for grounding prompt
        sources_text = "\n\n".join([
            f"[{c.get('number', i+1)}] {c.get('citation', c.get('text', ''))[:500]}"
            for i, c in enumerate(citations[:5])  # Limit to top 5 sources
        ])
        
        grounding_prompt = f"""Anda adalah hakim yang mengevaluasi kualitas jawaban hukum.

Sumber hukum:
{sources_text}

Jawaban yang akan dievaluasi:
{answer}

Tugas Anda: Evaluasi setiap klaim dalam jawaban apakah didukung oleh sumber hukum di atas.

Instruksi:
1. Identifikasi klaim-klaim utama dalam jawaban
2. Untuk setiap klaim, tentukan apakah didukung oleh sumber yang diberikan
3. Jika ada klaim yang TIDAK didukung oleh sumber,cantumkan

Respons dalam format JSON:
{{
  "grounding_score": <skor 0.0-1.0 indicating percentage of claims fully supported>,
  "ungrounded_claims": [<list of claim descriptions that are not supported by sources>],
  "grounded_claims": [<list of claim descriptions that ARE supported>]
}}

JSON:"""

        try:
            import json
            import time
            
            start_time = time.time()
            timeout = 5.0  # 5 second timeout
            
            response = self.llm_client.generate(
                user_message=grounding_prompt,
                system_message="Anda adalah evaluasi jawaban hukum yang objektif. Selalu respond dengan JSON yang valid.",
            )
            
            elapsed = time.time() - start_time
            logger.info(f"Grounding verification took {elapsed:.2f}s")
            
            # Parse JSON response
            # Find JSON in response (in case there's extra text
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                
                grounding_score = float(result.get('grounding_score', 0.5))
                ungrounded = result.get('ungrounded_claims', [])
                
                # Clamp score to 0-1
                grounding_score = max(0.0, min(1.0, grounding_score))
                
                logger.info(f"Grounding score: {grounding_score:.2f}, ungrounded claims: {len(ungrounded)}")
                return grounding_score, ungrounded
            else:
                logger.warning("Could not parse JSON from grounding response")
                return None, []
                
        except Exception as e:
            error_type = type(e).__name__
            logger.warning(f"Grounding verification failed ({error_type}): {e}")
            return None, []
    
    def query(
        self,
        question: str,
        filter_jenis_dokumen: str | None = None,
        top_k: int | None = None,
        mode: str = "synthesized",
    ) -> RAGResponse:
        """
        Query the RAG chain with a question.
        
        Args:
            question: User question in Indonesian
            filter_jenis_dokumen: Optional filter by document type (UU, PP, Perpres, etc.)
            top_k: Number of documents to retrieve
            mode: Response mode - "synthesized" for AI answer, "verbatim" for direct quotes
        
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
        
        # Step 2.5: Check confidence threshold - refuse if too low
        CONFIDENCE_THRESHOLD = 0.30
        if confidence.numeric < CONFIDENCE_THRESHOLD:
            refusal_text = "Maaf, saya tidak memiliki cukup informasi hukum untuk menjawab pertanyaan ini dengan akurat. Silakan konsultasikan dengan ahli hukum."
            logger.info(f"Low confidence ({confidence.numeric:.3f} < {CONFIDENCE_THRESHOLD}) - refusing to answer")
            return RAGResponse(
                answer=refusal_text,
                citations=citations,
                sources=sources,
                confidence="rendah",
                confidence_score=confidence,
                raw_context=context,
                validation=ValidationResult(
                    is_valid=True,
                    citation_coverage=0.0,
                    warnings=["Pertanyaan di luar jangkauan basis pengetahuan"],
                    hallucination_risk="refused",
                    missing_citations=[],
                ),
            )
        
        # Step 3: Generate answer using LLM
        user_prompt = USER_PROMPT_TEMPLATE.format(
            context=context,
            question=question,
        )
        
        logger.info(f"Generating answer with NVIDIA NIM {NVIDIA_MODEL} (mode: {mode})...")
        # Use different system prompt based on mode
        system_msg = VERBATIM_SYSTEM_PROMPT if mode == "verbatim" else SYSTEM_PROMPT
        raw_answer = self.llm_client.generate(
            user_message=user_prompt,
            system_message=system_msg,
        )
        
        # Step 3.5: Extract structured JSON metadata from LLM response
        answer, json_metadata = self._extract_json_metadata(raw_answer)
        
        # Step 4: Validate answer for citation accuracy
        # If JSON metadata has cited_sources, pass them to validation; otherwise regex fallback
        json_cited_sources: list[int] | None = None
        if json_metadata and "cited_sources" in json_metadata:
            try:
                json_cited_sources = [int(s) for s in json_metadata["cited_sources"]]
                logger.info(f"Using JSON-extracted cited_sources: {json_cited_sources}")
            except (TypeError, ValueError) as e:
                logger.warning(f"Invalid cited_sources in JSON metadata: {e}")
                json_cited_sources = None
        
        validation = self._validate_answer(answer, citations, json_cited_sources=json_cited_sources)
        if validation.warnings:
            logger.warning(f"Answer validation warnings: {validation.warnings}")
        
        # Step 5: LLM-as-judge grounding verification
        grounding_score, ungrounded_claims = self._verify_grounding(answer, citations)
        validation.grounding_score = grounding_score
        validation.ungrounded_claims = ungrounded_claims
        
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
        
        # Step 2.5: Check confidence threshold - refuse if too low
        CONFIDENCE_THRESHOLD = 0.30
        if confidence.numeric < CONFIDENCE_THRESHOLD:
            refusal_text = "Maaf, saya tidak memiliki cukup informasi hukum untuk menjawab pertanyaan ini dengan akurat. Silakan konsultasikan dengan ahli hukum."
            logger.info(f"Low confidence ({confidence.numeric:.3f} < {CONFIDENCE_THRESHOLD}) - refusing to answer (streaming)")
            yield ("metadata", {
                "citations": citations,
                "sources": sources,
                "confidence_score": confidence.to_dict(),
            })
            yield ("chunk", refusal_text)
            yield ("done", {
                "validation": {
                    "is_valid": True,
                    "citation_coverage": 0.0,
                    "warnings": ["Pertanyaan di luar jangkauan basis pengetahuan"],
                    "hallucination_risk": "refused",
                    "missing_citations": [],
                }
            })
            return
        
        # Send metadata immediately so frontend can show sources while waiting for answer
        yield ("metadata", {
            "citations": citations,
            "sources": sources,
            "confidence_score": confidence.to_dict(),
        })
        
        # Step 3: Generate answer using streaming LLM
        user_prompt = USER_PROMPT_TEMPLATE.format(
            context=context,
            question=question,
        )
        
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
        
        # Step 5: LLM-as-judge grounding verification (streaming post-generation)
        logger.info("Performing grounding verification for streaming response...")
        grounding_score, ungrounded_claims = self._verify_grounding(full_answer, citations)
        validation.grounding_score = grounding_score
        validation.ungrounded_claims = ungrounded_claims
        
        if grounding_score is not None and grounding_score < 0.5:
            logger.warning(f"Low grounding score ({grounding_score:.2f}) detected in streaming response")
        
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
