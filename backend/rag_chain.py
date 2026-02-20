"""
RAG Chain Module for Indonesian Legal Q&A

Uses GitHub Copilot Chat API as the default LLM provider (GPT-4o).
Also supports NVIDIA NIM as an alternative provider.
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

from dotenv import load_dotenv

from retriever import HybridRetriever, SearchResult

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LLM client (moved to llm_client.py — re-export for backward compatibility)
from llm_client import (  # noqa: E402
    LLMClient,
    NVIDIANimClient,
    CopilotChatClient,
    GroqClient,
    GeminiClient,
    MistralClient,
    FallbackChain,
    CircuitBreaker,
    create_llm_client,
    NVIDIA_API_KEY,
    NVIDIA_API_URL,
    NVIDIA_MODEL,
    MAX_TOKENS,
    TEMPERATURE,
)
from prompts import (  # noqa: E402
    SYSTEM_PROMPT_COT,
    QUESTION_TYPE_PROMPTS,
    PROVIDER_TUNING,
    detect_question_type,
)
from hyde import HyDE  # noqa: E402
from query_planner import QueryPlanner  # noqa: E402
from multi_query import MultiQueryFusion  # noqa: E402
from crag import CRAG  # noqa: E402
from parent_child import ParentChildRetriever  # noqa: E402
from agentic_rag import AgenticRAG  # noqa: E402
# NOTE: semantic_chunker is indexing-time only, not imported here

# Retriever configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "indonesian_legal_docs")
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Fallback chain configuration
# Provider order: cheapest/fastest first → most reliable last
FALLBACK_PROVIDER_ORDER = ["groq", "gemini", "mistral", "copilot", "nvidia"]


def create_fallback_chain(
    primary_provider: str = "copilot",
    fallback_providers: list[str] | None = None,
) -> FallbackChain:
    """Create a FallbackChain with multiple LLM providers.
    
    Args:
        primary_provider: The first provider to try (default: "copilot").
        fallback_providers: List of fallback providers in order. If None, uses
            all available providers in FALLBACK_PROVIDER_ORDER, starting with
            primary_provider.
    
    Returns:
        A FallbackChain instance that tries providers in order.
    
    Example:
        # Use copilot with fallbacks to groq, gemini, mistral, nvidia
        chain = create_fallback_chain("copilot")
        
        # Use only groq and gemini as fallbacks
        chain = create_fallback_chain("copilot", ["groq", "gemini"])
    """
    if fallback_providers is None:
        # Use all providers, starting with primary
        providers = [primary_provider]
        for p in FALLBACK_PROVIDER_ORDER:
            if p != primary_provider:
                providers.append(p)
    else:
        providers = [primary_provider] + fallback_providers
    
    # Create clients for each provider (skip those without API keys)
    provider_clients: list[tuple[str, LLMClient]] = []
    for provider in providers:
        try:
            client = create_llm_client(provider)
            provider_clients.append((provider, client))
            logger.info(f"FallbackChain: Added {provider} to chain")
        except Exception as e:
            logger.warning(f"FallbackChain: Skipping {provider} (not available: {e})")
    
    if not provider_clients:
        raise RuntimeError("No LLM providers available for fallback chain")
    
    return FallbackChain(provider_clients)


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


class LegalRAGChain:
    """RAG Chain for Indonesian Legal Q&A with citations."""
    
    def __init__(
        self,
        retriever: HybridRetriever | None = None,
        llm_client: LLMClient | NVIDIANimClient | None = None,
        top_k: int = 5,
        use_fallback: bool = False,
        fallback_providers: list[str] | None = None,
        primary_provider: str = "copilot",
    ):
        """Initialize the RAG chain.
        
        Args:
            retriever: HybridRetriever instance. If None, creates a new one.
            llm_client: LLM client instance. If None, creates based on other params.
            top_k: Number of documents to retrieve.
            use_fallback: If True, wrap LLM client in FallbackChain for resilience.
            fallback_providers: List of fallback providers (only used if use_fallback=True).
                If None, uses all available providers.
            primary_provider: Primary LLM provider (default: "copilot").
        """
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
        
        # Initialize LLM client with optional fallback chain
        if llm_client is None:
            if use_fallback:
                logger.info(f"Initializing FallbackChain with primary={primary_provider}...")
                self.llm_client = create_fallback_chain(primary_provider, fallback_providers)
            else:
                logger.info(f"Initializing {primary_provider} client...")
                self.llm_client = create_llm_client(primary_provider)
        else:
            self.llm_client = llm_client
        
        self.top_k = top_k
        self.use_fallback = use_fallback
        
        # Expose .search() as alias for .hybrid_search() (used by HyDE and QueryPlanner)
        if not hasattr(self.retriever, 'search'):
            self.retriever.search = self.retriever.hybrid_search  # type: ignore[attr-defined]
        
        # Initialize Advanced RAG components
        self.hyde = HyDE(self.llm_client)
        self.query_planner = QueryPlanner(self.llm_client)
        
        # Initialize new Advanced RAG techniques
        self.multi_query = MultiQueryFusion()
        self.crag = CRAG(self.llm_client)
        
        # Parent-child: load parent_store if available, else empty dict
        parent_store_path = os.path.join(os.path.dirname(__file__), "parent_store.json")
        parent_store = {}
        if os.path.exists(parent_store_path):
            with open(parent_store_path, "r", encoding="utf-8") as f:
                parent_store = json.load(f)
            logger.info(f"Loaded parent store with {len(parent_store)} entries")
        else:
            logger.warning(f"Parent store not found at {parent_store_path} — parent-child retrieval disabled")
        self.parent_child = ParentChildRetriever(parent_store=parent_store)
        
        # Agentic orchestrator (composes all techniques)
        self.agentic = AgenticRAG(
            llm_client=self.llm_client,
            retriever=self.retriever,
            hyde=self.hyde,
            crag=self.crag,
            multi_query=self.multi_query,
            query_planner=self.query_planner,
        )
        logger.info("Advanced RAG v2 components initialized: MultiQuery + CRAG + ParentChild + Agentic")
    
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
        Assess confidence using multi-factor heuristics calibrated for RRF scores.
        RRF scores (k=60): max = 2/61 ≈ 0.033, typical good = 0.016–0.033

        Factors:
        1. Normalized retrieval quality (40% weight)
        2. Document type authority (20% weight)
        3. Score distribution / consistency (20% weight)
        4. Number of relevant documents found (20% weight)
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

        # RRF score constants (k=60)
        RRF_MAX = 2 / 61        # ≈ 0.0328 — rank #1 in BOTH BM25 and dense
        RRF_GOOD = 1 / 61       # ≈ 0.0164 — rank #1 in one search
        RRF_QUALITY_THRESHOLD = RRF_GOOD * 0.8  # ≈ 0.013 — meaningful retrieval

        # Factor 1: Normalized retrieval quality (40% weight)
        # Normalize relative to RRF max so top score ≈ 0.033 maps to ≈ 1.0
        norm_top = min(1.0, top_score / RRF_MAX)
        norm_avg = min(1.0, avg_score / RRF_MAX)
        base_score = (norm_top * 0.7) + (norm_avg * 0.3)

        # Factor 2: Document authority hierarchy (20% weight)
        # Authority reflects document type quality. Retrieved presence = relevance.
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
            # Weight by normalized score so higher-ranked retrieved docs matter more
            norm_score = min(1.0, r.score / RRF_MAX)
            authority_scores.append(authority * (0.5 + 0.5 * norm_score))

        authority_factor = sum(authority_scores) / len(authority_scores) if authority_scores else 0.5

        # Factor 3: Score distribution / consistency (20% weight)
        # Scale-invariant variance: consistent scores = higher confidence
        if len(scores) > 1:
            score_variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
            relative_variance = score_variance / (avg_score ** 2) if avg_score > 0 else 1.0
            consistency_factor = max(0.3, 1.0 - min(1.0, relative_variance * 0.5))
        else:
            consistency_factor = 0.7  # Single result, moderate confidence

        # Factor 4: Result count factor (20% weight)
        # Use RRF-appropriate threshold instead of cosine-similarity threshold of 0.3
        high_quality_results = sum(1 for s in scores if s > RRF_QUALITY_THRESHOLD)
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

        # Apply calibration: cap very high scores with diminishing returns
        if numeric > 0.85:
            numeric = 0.85 + (numeric - 0.85) * 0.5
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
        skip_grounding: bool = False,
        use_hyde: bool = True,
        use_decomposition: bool = True,
        use_crag: bool = False,           # NEW (off by default — enable for quality gate)
        use_multi_query: bool = False,    # NEW (off by default)
        use_parent_child: bool = False,   # NEW (off by default)
        use_agentic: bool = False,        # NEW (off by default)
    ) -> RAGResponse:
        """
        Query the RAG chain with a question.
        
        Args:
            question: User question in Indonesian
            filter_jenis_dokumen: Optional filter by document type (UU, PP, Perpres, etc.)
            top_k: Number of documents to retrieve
            mode: Response mode - "synthesized" for AI answer, "verbatim" for direct quotes
            skip_grounding: If True, skip the LLM-as-judge grounding verification call
                (saves ~30% time per query). Grounding fields will be None/empty.
            use_hyde: If True, use HyDE enhanced search for better retrieval (default True)
            use_decomposition: If True, decompose complex questions into sub-queries (default True)
            use_crag: If True, apply CRAG quality grading post-retrieval (default False, enable for quality gate)
            use_multi_query: If True, use Multi-Query Fusion (template-based variants, default False)
            use_parent_child: If True, expand child chunks to parent context (default False, requires parent_store)
            use_agentic: If True, use Agentic RAG orchestration (default False, overrides cascade)
        
        Returns:
            RAGResponse with answer, citations, and sources
        """
        k = top_k or self.top_k
        
        # Step 1: Retrieve relevant documents (Advanced RAG pipeline)
        logger.info(f"Retrieving documents for: {question[:50]}...")
        
        if filter_jenis_dokumen:
            # Filtered search — bypass advanced RAG
            results = self.retriever.search_by_document_type(
                query=question,
                jenis_dokumen=filter_jenis_dokumen,
                top_k=k,
            )
        else:
            # Advanced RAG retrieval pipeline with feature flags
            
            # Priority cascade (highest priority first):
            if use_agentic:
                # Agentic mode: orchestrator picks strategy dynamically
                results = self.agentic.enhanced_search(question, self.retriever, top_k=k)
                logger.info("Agentic RAG orchestration applied")
            elif use_decomposition and self.query_planner.should_decompose(question):
                # Complex compound questions
                results = self.query_planner.multi_hop_search(question, self.retriever, top_k=k)
                logger.info("Query decomposition applied")
            elif use_multi_query:
                # Vague/ambiguous questions
                results = self.multi_query.enhanced_search(question, self.retriever, top_k=k)
                logger.info("Multi-Query Fusion applied")
            elif use_hyde:
                # Definition/concept questions
                results = self.hyde.enhanced_search(question, self.retriever, top_k=k)
                logger.info("HyDE applied")
            else:
                # Direct search fallback
                results = self.retriever.hybrid_search(query=question, top_k=k, expand_queries=True)
            
            # Post-retrieval correction with CRAG (applied after any retrieval strategy)
            if use_crag and results:
                grade = self.crag.grade_retrieval(question, results)
                if grade != "correct":
                    logger.info(f"CRAG quality gate: {grade} — re-retrieving")
                    corrected = self.crag.enhanced_search(question, self.retriever, top_k=k)
                    if corrected:
                        results = corrected
                    else:
                        logger.info("CRAG re-retrieval returned empty — keeping original results")
                else:
                    logger.info("CRAG quality gate: correct — keeping results")
            
            # Parent-child expansion (applied after retrieval + correction)
            if use_parent_child and self.parent_child.parent_store:
                results = self.parent_child.enhanced_search(question, self.retriever, top_k=k)
                logger.info("Parent-child expansion applied")
        
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
        CONFIDENCE_THRESHOLD = 0.15
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
        
        # Step 3: Generate answer using LLM with Advanced RAG prompts
        user_prompt = USER_PROMPT_TEMPLATE.format(
            context=context,
            question=question,
        )
        
        # Detect question type and get specialized instruction
        question_type = detect_question_type(question)
        type_specific_instruction = QUESTION_TYPE_PROMPTS.get(question_type, "")
        logger.info(f"Detected question type: {question_type}")
        
        # Select system prompt based on mode
        if mode == "verbatim":
            system_msg = VERBATIM_SYSTEM_PROMPT
        else:
            # Use CoT prompt + type-specific instruction for synthesized mode
            system_msg = SYSTEM_PROMPT_COT
            if type_specific_instruction:
                system_msg = system_msg + "\n\n" + type_specific_instruction
        
        # Get provider-specific tuning (temperature, max_tokens)
        provider_name = getattr(self.llm_client, 'provider_name', None)
        if not provider_name:
            # Detect from class name
            class_name = self.llm_client.__class__.__name__.lower()
            if 'groq' in class_name:
                provider_name = 'groq'
            elif 'gemini' in class_name:
                provider_name = 'gemini'
            elif 'mistral' in class_name:
                provider_name = 'mistral'
            elif 'nvidia' in class_name or 'nim' in class_name:
                provider_name = 'nvidia'
            else:
                provider_name = 'copilot'
        tuning = PROVIDER_TUNING.get(provider_name, PROVIDER_TUNING['copilot'])
        
        # Apply provider-specific tuning to LLM client
        original_max_tokens = getattr(self.llm_client, 'max_tokens', None)
        original_temperature = getattr(self.llm_client, 'temperature', None)
        try:
            if hasattr(self.llm_client, 'max_tokens'):
                setattr(self.llm_client, 'max_tokens', tuning['max_tokens'])
            if hasattr(self.llm_client, 'temperature'):
                setattr(self.llm_client, 'temperature', tuning['temperature'])
            
            logger.info(
                f"Generating answer (mode: {mode}, question_type: {question_type}, "
                f"provider: {provider_name}, temp: {tuning['temperature']}, "
                f"max_tokens: {tuning['max_tokens']})..."
            )
            raw_answer = self.llm_client.generate(
                user_message=user_prompt,
                system_message=system_msg,
            )
        finally:
            # Restore original LLM client settings
            if original_max_tokens is not None and hasattr(self.llm_client, 'max_tokens'):
                setattr(self.llm_client, 'max_tokens', original_max_tokens)
            if original_temperature is not None and hasattr(self.llm_client, 'temperature'):
                setattr(self.llm_client, 'temperature', original_temperature)
        
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
        if skip_grounding:
            grounding_score = None
            ungrounded_claims: list[str] = []
            validation.grounding_score = grounding_score
            validation.ungrounded_claims = ungrounded_claims
            validation.hallucination_risk = "skipped"
        else:
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
        CONFIDENCE_THRESHOLD = 0.15
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
