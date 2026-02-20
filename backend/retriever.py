"""
Hybrid Search Retriever for Indonesian Legal Documents.

Combines dense vector search (HuggingFace embeddings via Qdrant) with
sparse BM25 retrieval for optimal recall on Bahasa Indonesia legal text.

Uses Reciprocal Rank Fusion (RRF) to merge results:
    score = sum(1 / (k + rank)) where k=60 (standard constant)
"""
import os
import re
import time
from typing import Any
from dataclasses import dataclass
import logging

import requests
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from langchain_huggingface import HuggingFaceEmbeddings
from rank_bm25 import BM25Okapi

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Constants - must match ingest.py
COLLECTION_NAME = "indonesian_legal_docs"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")  # For Qdrant Cloud
RRF_K = 60  # Standard RRF constant
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"  # Multilingual cross-encoder (upgraded from mMiniLMv2)

# NVIDIA NIM embedding configuration
USE_NVIDIA_EMBEDDINGS = os.getenv("USE_NVIDIA_EMBEDDINGS", "false").lower() == "true"
NVIDIA_EMBEDDING_MODEL = "nvidia/nv-embedqa-e5-v5"
NVIDIA_EMBEDDING_DIM = 1024
NVIDIA_API_KEY = os.getenv("NVIDIA_EMBEDDING_API_KEY") or os.getenv("NVIDIA_API_KEY")
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/embeddings"

# Jina AI embedding configuration
USE_JINA_EMBEDDINGS = os.getenv("USE_JINA_EMBEDDINGS", "true").lower() == "true"
JINA_EMBEDDING_MODEL = os.getenv("JINA_EMBEDDING_MODEL", "jina-embeddings-v3")
JINA_EMBEDDING_DIM = int(os.getenv("JINA_EMBEDDING_DIM", "1024"))
JINA_API_KEY = os.getenv("JINA_API_KEY")
JINA_API_URL = "https://api.jina.ai/v1/embeddings"


class NVIDIAEmbedder:
    """
    NVIDIA NIM API embeddings client for nv-embedqa-e5-v5 model.
    
    Supports batch embedding with automatic retry and exponential backoff
    for rate limit handling.
    """
    
    def __init__(
        self,
        api_key: str | None = None,
        model: str = NVIDIA_EMBEDDING_MODEL,
        max_retries: int = 3,
        timeout: int = 30,
        max_tokens: int = 512,
    ):
        """
        Initialize NVIDIA embedder.
        
        Args:
            api_key: NVIDIA API key (defaults to env var)
            model: NVIDIA model name
            max_retries: Maximum retry attempts for failed requests
            timeout: Request timeout in seconds
            max_tokens: Maximum token limit for input text (nv-embedqa-e5-v5 has 512 token limit)
        """
        self.api_key = api_key or NVIDIA_API_KEY
        if not self.api_key:
            raise ValueError(
                "NVIDIA API key not found. Set NVIDIA_EMBEDDING_API_KEY or NVIDIA_API_KEY environment variable."
            )
        
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout
        self.dimension = NVIDIA_EMBEDDING_DIM
        self.max_tokens = max_tokens
        
        logger.info(f"Initialized NVIDIA embedder with model: {model} (max_tokens: {max_tokens})")
    
    def _truncate_to_token_limit(self, text: str) -> str:
        """
        Truncate text to fit within the token limit.
        
        Uses a conservative character-based heuristic: ~2 chars per token.
        This is very conservative to handle worst-case scenarios (dense tokens, special characters).
        
        Args:
            text: Input text
        
        Returns:
            Truncated text that fits within max_tokens
        """
        # Very conservative estimate: 2 characters per token (handles dense tokenization)
        max_chars = self.max_tokens * 2
        
        if len(text) > max_chars:
            logger.warning(f"Truncating text from {len(text)} to {max_chars} characters (estimated {self.max_tokens} tokens)")
            return text[:max_chars]
        
        return text
    
    def _make_request(
        self,
        texts: list[str],
        input_type: str = "query",
        retry_count: int = 0,
    ) -> dict[str, Any]:
        """
        Make API request with exponential backoff retry logic.
        
        Args:
            texts: List of texts to embed
            input_type: "query" or "passage"
            retry_count: Current retry attempt
        
        Returns:
            API response as dict
        
        Raises:
            Exception: After max retries exceeded or non-retryable error
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        # Truncate all texts to fit within token limit
        truncated_texts = [self._truncate_to_token_limit(text) for text in texts]
        
        data = {
            "input": truncated_texts,
            "model": self.model,
            "encoding_format": "float",
            "input_type": input_type,
        }
        
        try:
            response = requests.post(
                NVIDIA_API_URL,
                headers=headers,
                json=data,
                timeout=self.timeout,
            )
            
            # Handle rate limiting with exponential backoff
            if response.status_code == 429:
                if retry_count < self.max_retries:
                    wait_time = 2 ** retry_count  # 1s, 2s, 4s, ...
                    logger.warning(f"Rate limit hit, retrying in {wait_time}s (attempt {retry_count + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    return self._make_request(texts, input_type, retry_count + 1)
                else:
                    raise Exception(f"Rate limit exceeded after {self.max_retries} retries")
            
            # Handle other errors
            if response.status_code != 200:
                raise Exception(f"NVIDIA API error {response.status_code}: {response.text}")
            
            return response.json()
        
        except requests.exceptions.Timeout:
            if retry_count < self.max_retries:
                wait_time = 2 ** retry_count
                logger.warning(f"Request timeout, retrying in {wait_time}s (attempt {retry_count + 1}/{self.max_retries})")
                time.sleep(wait_time)
                return self._make_request(texts, input_type, retry_count + 1)
            else:
                raise Exception(f"Request timeout after {self.max_retries} retries")
        
        except Exception as e:
            logger.error(f"NVIDIA API request failed: {e}")
            raise
    
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a batch of documents (passages).
        
        Args:
            texts: List of document texts
        
        Returns:
            List of embedding vectors (1024-dim each)
        """
        if not texts:
            return []
        
        # NVIDIA API supports batch embedding, but we'll batch in chunks of 100 for safety
        batch_size = 100
        all_embeddings: list[list[float]] = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            result = self._make_request(batch, input_type="passage")
            
            # Extract embeddings in order
            embeddings = [item["embedding"] for item in sorted(result["data"], key=lambda x: x["index"])]
            all_embeddings.extend(embeddings)
        
        return all_embeddings
    
    def embed_query(self, text: str) -> list[float]:
        """
        Embed a single query.
        
        Args:
            text: Query text
        
        Returns:
            Embedding vector (1024-dim)
        """
        result = self._make_request([text], input_type="query")
        return result["data"][0]["embedding"]


class JinaEmbedder:
    """
    Jina AI embeddings client for jina-embeddings-v3 model.
    
    Supports batch embedding with automatic retry and exponential backoff
    for rate limit handling.  Uses task-specific embedding types
    (retrieval.passage for documents, retrieval.query for queries).
    
    API: POST https://api.jina.ai/v1/embeddings
    Token limit: 8192 (server-side truncation via truncate=true)
    """
    
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_retries: int = 10,
        timeout: int = 60,
        dimensions: int | None = None,
    ):
        """
        Initialize Jina embedder.
        
        Args:
            api_key: Jina API key (defaults to JINA_API_KEY env var)
            model: Jina model name (defaults to JINA_EMBEDDING_MODEL)
            max_retries: Maximum retry attempts for failed requests (10 for aggressive rate limit handling)
            timeout: Request timeout in seconds
            dimensions: Output embedding dimensions (defaults to JINA_EMBEDDING_DIM)
        """
        self.api_key = api_key or JINA_API_KEY
        if not self.api_key:
            raise ValueError(
                "Jina API key not found. Set JINA_API_KEY environment variable."
            )
        
        self.model = model or JINA_EMBEDDING_MODEL
        self.max_retries = max_retries
        self.timeout = timeout
        self.dimension = dimensions or JINA_EMBEDDING_DIM
        
        logger.info(f"Initialized Jina embedder with model: {self.model} (dim: {self.dimension})")
    
    def _make_request(
        self,
        texts: list[str],
        task: str = "retrieval.query",
        retry_count: int = 0,
    ) -> dict[str, Any]:
        """
        Make API request with exponential backoff retry logic.
        
        Args:
            texts: List of texts to embed
            task: Jina task type — "retrieval.query" or "retrieval.passage"
            retry_count: Current retry attempt
        
        Returns:
            API response as dict
        
        Raises:
            Exception: After max retries exceeded or non-retryable error
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        data = {
            "model": self.model,
            "input": texts,
            "embedding_type": "float",
            "task": task,
            "dimensions": self.dimension,
            "normalized": True,
            "truncate": True,
        }
        
        try:
            response = requests.post(
                JINA_API_URL,
                headers=headers,
                json=data,
                timeout=self.timeout,
            )
            
            # Handle rate limiting with aggressive exponential backoff
            if response.status_code == 429:
                if retry_count < self.max_retries:
                    # Retry-After header takes priority if present
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        wait_time = int(retry_after) + 1
                    else:
                        wait_time = 2 ** (retry_count + 1)  # 2s, 4s, 8s, 16s, 32s, 64s, 128s, 256s, 512s, 1024s
                    logger.warning(f"Rate limit hit, retrying in {wait_time}s (attempt {retry_count + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    return self._make_request(texts, task, retry_count + 1)
                else:
                    raise Exception(f"Rate limit exceeded after {self.max_retries} retries")
            
            # Handle server errors with retry (5xx)
            if response.status_code >= 500:
                if retry_count < self.max_retries:
                    wait_time = 2 ** (retry_count + 1)
                    logger.warning(f"Server error {response.status_code}, retrying in {wait_time}s (attempt {retry_count + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    return self._make_request(texts, task, retry_count + 1)
            
            # Handle other errors
            if response.status_code != 200:
                raise Exception(f"Jina API error {response.status_code}: {response.text}")
            
            return response.json()
        
        except requests.exceptions.Timeout:
            if retry_count < self.max_retries:
                wait_time = 2 ** (retry_count + 1)
                logger.warning(f"Request timeout, retrying in {wait_time}s (attempt {retry_count + 1}/{self.max_retries})")
                time.sleep(wait_time)
                return self._make_request(texts, task, retry_count + 1)
            else:
                raise Exception(f"Request timeout after {self.max_retries} retries")
        
        except Exception as e:
            logger.error(f"Jina API request failed: {e}")
            raise
    
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a batch of documents (passages).
        
        Args:
            texts: List of document texts
        
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        # Jina API supports batch embedding; batch in chunks of 100 for safety
        batch_size = 100
        all_embeddings: list[list[float]] = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            result = self._make_request(batch, task="retrieval.passage")
            
            # Extract embeddings in order
            embeddings = [item["embedding"] for item in sorted(result["data"], key=lambda x: x["index"])]
            all_embeddings.extend(embeddings)
        
        return all_embeddings
    
    def embed_query(self, text: str) -> list[float]:
        """
        Embed a single query.
        
        Args:
            text: Query text
        
        Returns:
            Embedding vector
        """
        result = self._make_request([text], task="retrieval.query")
        return result["data"][0]["embedding"]


@dataclass
class SearchResult:
    """Single search result with score and metadata."""
    id: int
    text: str
    citation: str
    citation_id: str
    score: float
    metadata: dict[str, Any]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "text": self.text,
            "citation": self.citation,
            "citation_id": self.citation_id,
            "score": self.score,
            "metadata": self.metadata,
        }


def tokenize_indonesian(text: str) -> list[str]:
    """
    Enhanced tokenizer for Indonesian legal text.
    
    Handles:
    - Lowercase
    - Split on whitespace and punctuation
    - Expanded Indonesian stopwords (50+)
    - Legal abbreviation expansion (PT, CV, UU, etc.)
    - Bigram generation for common legal phrases
    
    For production, consider using Sastrawi or similar.
    """
    import re
    
    # Legal abbreviation expansion
    legal_abbrevs = {
        r'\bpt\b': 'perseroan terbatas',
        r'\bcv\b': 'commanditaire vennootschap',
        r'\buu\b': 'undang undang',
        r'\bpp\b': 'peraturan pemerintah',
        r'\bperpres\b': 'peraturan presiden',
        r'\bperda\b': 'peraturan daerah',
        r'\bphk\b': 'pemutusan hubungan kerja',
        r'\bnib\b': 'nomor induk berusaha',
        r'\bkuhp\b': 'kitab undang hukum pidana',
        r'\bkuhap\b': 'kitab undang hukum acara pidana',
        r'\bkuhper\b': 'kitab undang hukum perdata',
    }
    
    # Lowercase and expand abbreviations
    text = text.lower()
    for abbrev, expansion in legal_abbrevs.items():
        text = re.sub(abbrev, expansion, text)
    
    # Extract words
    tokens = re.findall(r'\b[a-zA-Z0-9]+\b', text)
    
    # Expanded Indonesian stopwords (50+ common function words)
    stopwords = {
        # Original 24
        "dan", "atau", "yang", "di", "ke", "dari", "untuk",
        "dengan", "pada", "ini", "itu", "adalah", "sebagai",
        "dalam", "oleh", "tidak", "akan", "dapat", "telah",
        "tersebut", "bahwa", "jika", "maka", "atas", "setiap",
        # Additional 26 common function words
        "ada", "bagi", "bisa", "hal", "hingga", "jadi", "juga",
        "karena", "kita", "lebih", "lain", "masih", "mereka",
        "oleh", "saat", "sangat", "saya", "se", "suatu", "sudah",
        "tanpa", "tapi", "telah", "tetapi", "untuk", "yaitu",
    }
    
    # Filter stopwords and short tokens
    filtered_tokens = [t for t in tokens if t not in stopwords and len(t) > 1]
    
    # Generate bigrams for legal phrases
    bigrams = []
    for i in range(len(filtered_tokens) - 1):
        bigram = f"{filtered_tokens[i]}_{filtered_tokens[i+1]}"
        bigrams.append(bigram)
    
    # Combine unigrams + bigrams
    return filtered_tokens + bigrams


class HybridRetriever:
    """
    Hybrid retriever combining dense vector search with BM25 sparse retrieval.
    
    Usage:
        retriever = HybridRetriever()
        results = retriever.hybrid_search("Apa itu Undang-Undang Cipta Kerja?", top_k=5)
    """

    # National law intent keywords — used by _is_national_law_query() to detect
    # queries about national legislation so Perda chunks can be deprioritized.
    _NATIONAL_LAW_KEYWORDS: list[str] = [
        # PT/company formation
        "mendirikan pt", "pendirian pt", "syarat pt", "badan hukum",
        "perseroan terbatas", "modal dasar", "akta pendirian",
        # Employment/labor (national UU 13/2003)
        "phk", "pesangon", "upah minimum", "hubungan kerja",
        "perjanjian kerja",
        # National regulations explicitly mentioned
        "undang-undang", "peraturan pemerintah",
        "hukum nasional",
    ]

    def __init__(
        self,
        qdrant_url: str = QDRANT_URL,
        qdrant_api_key: str | None = QDRANT_API_KEY,
        collection_name: str = COLLECTION_NAME,
        embedding_model: str = EMBEDDING_MODEL,
        use_reranker: bool = True,
        use_nvidia: bool = USE_NVIDIA_EMBEDDINGS,
        use_jina: bool = USE_JINA_EMBEDDINGS,
        knowledge_graph: Any | None = None,
    ):
        """
        Initialize the hybrid retriever.
        
        Embedding provider precedence: Jina > NVIDIA > HuggingFace.
        When multiple providers are enabled, the highest-precedence one wins.
        
        Args:
            qdrant_url: Qdrant server URL
            qdrant_api_key: API key for Qdrant Cloud (optional for local)
            collection_name: Name of the Qdrant collection
            embedding_model: HuggingFace model for embeddings (ignored if use_jina/use_nvidia=True)
            use_reranker: Whether to use CrossEncoder for re-ranking
            use_nvidia: Whether to use NVIDIA NIM API embeddings (1024-dim)
            use_jina: Whether to use Jina AI embeddings (jina-embeddings-v3)
            knowledge_graph: Optional LegalKnowledgeGraph instance for KG-aware boosting
        """
        self.collection_name = collection_name
        self.qdrant_url = qdrant_url
        self.use_reranker = use_reranker
        self.use_nvidia = use_nvidia
        self.use_jina = use_jina
        self.knowledge_graph = knowledge_graph
        
        # Initialize Qdrant client (with API key for cloud)
        if qdrant_api_key:
            self.client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=10)
        else:
            self.client = QdrantClient(url=qdrant_url, timeout=10)
        
        # Initialize embeddings — precedence: Jina > NVIDIA > HuggingFace
        if use_jina:
            logger.info(f"Using Jina embeddings: {JINA_EMBEDDING_MODEL} (precedence: Jina > NVIDIA > HuggingFace)")
            self.embedder = JinaEmbedder()
            self.embedding_dim = JINA_EMBEDDING_DIM
        elif use_nvidia:
            logger.info(f"Using NVIDIA embeddings: {NVIDIA_EMBEDDING_MODEL}")
            self.embedder = NVIDIAEmbedder()
            self.embedding_dim = NVIDIA_EMBEDDING_DIM
        else:
            logger.info(f"Using HuggingFace embeddings: {embedding_model}")
            self.embedder = HuggingFaceEmbeddings(model_name=embedding_model)
            self.embedding_dim = EMBEDDING_DIM
        
        # Initialize CrossEncoder for re-ranking (optional but recommended)
        # Set USE_DUMMY_RERANKER=1 to skip loading (useful when paging file/memory is low)
        self.reranker = None
        _skip_reranker = os.environ.get("USE_DUMMY_RERANKER", "0") == "1"
        if use_reranker and not _skip_reranker:
            try:
                from sentence_transformers import CrossEncoder
                logger.info(f"Loading CrossEncoder reranker: {RERANKER_MODEL}")
                self.reranker = CrossEncoder(RERANKER_MODEL)
                logger.info("CrossEncoder reranker loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load CrossEncoder, continuing without re-ranking: {e}")
                self.reranker = None
        elif _skip_reranker:
            logger.info("CrossEncoder reranker skipped (USE_DUMMY_RERANKER=1)")
        
        # Load corpus for BM25
        self._corpus: list[dict[str, Any]] = []
        self._bm25: BM25Okapi | None = None
        self._load_corpus()
    
    def _load_corpus(self) -> None:
        """Load all documents from Qdrant for BM25 indexing."""
        # Get collection info
        collection_info = self.client.get_collection(self.collection_name)
        total_points = collection_info.points_count
        if total_points is None or total_points == 0:
            self._corpus = []
            self._bm25 = None
            return
        
        # Scroll through all points
        records, _ = self.client.scroll(
            collection_name=self.collection_name,
            limit=total_points,
            with_payload=True,
            with_vectors=False,  # Don't need vectors for BM25
        )
        
        # Build corpus
        self._corpus = []
        tokenized_corpus = []
        
        for record in records:
            payload = record.payload
            if payload is None:
                continue
            text = payload.get("text", "")
            doc = {
                "id": record.id,
                "text": text,
                "citation": payload.get("citation", ""),
                "citation_id": payload.get("citation_id", ""),
                "metadata": {
                    k: v for k, v in payload.items()
                    if k not in ("text", "citation", "citation_id")
                },
            }
            self._corpus.append(doc)
            tokenized_corpus.append(tokenize_indonesian(str(text)))
        
        # Initialize BM25 index
        if tokenized_corpus:
            self._bm25 = BM25Okapi(tokenized_corpus)
    
    # Indonesian legal term synonym groups for query expansion.
    #
    # 55 groups covering:
    #   - Regulation type abbreviations (UU, PP, Perpres, Permen, Perda, Perpu, SKB)
    #   - Common legal term synonyms (pidana/kriminal, perdata/sipil, etc.)
    #   - Procedural terms (gugatan/tuntutan, banding/naik banding, etc.)
    #   - Business entity synonyms (PT/perseroan, CV/comanditer, etc.)
    #   - Common abbreviations (KUHPerdata, KUHP, etc.)
    #
    # TODO Phase 5: Replace/augment with LLM-based query expansion using
    # cached common queries for dynamic synonym discovery.
    _SYNONYM_GROUPS: list[list[str]] = [
        # === Business entity & corporate terms (1-10) ===
        ["PT", "Perseroan Terbatas", "perusahaan"],
        ["CV", "Commanditaire Vennootschap", "persekutuan komanditer"],
        ["firma", "Fa", "persekutuan firma"],
        ["koperasi", "badan usaha koperasi"],
        ["BUMN", "Badan Usaha Milik Negara", "perusahaan negara"],
        ["BUMD", "Badan Usaha Milik Daerah", "perusahaan daerah"],
        ["yayasan", "badan hukum yayasan", "organisasi nirlaba"],
        ["direksi", "direktur", "pengurus perseroan"],
        ["komisaris", "dewan komisaris", "pengawas"],
        ["RUPS", "Rapat Umum Pemegang Saham"],
        # === Employment & labor terms (11-20) ===
        ["karyawan", "pekerja", "buruh", "tenaga kerja"],
        ["PHK", "Pemutusan Hubungan Kerja", "pemberhentian kerja"],
        ["PKWT", "Perjanjian Kerja Waktu Tertentu", "kontrak kerja"],
        ["PKWTT", "Perjanjian Kerja Waktu Tidak Tertentu", "karyawan tetap"],
        ["gaji", "upah", "penghasilan", "remunerasi"],
        ["UMR", "UMK", "UMP", "upah minimum", "upah minimum regional"],
        ["pesangon", "uang pesangon", "kompensasi PHK"],
        ["lembur", "kerja lembur", "waktu kerja tambahan"],
        ["cuti", "cuti tahunan", "istirahat kerja", "hak istirahat"],
        ["serikat pekerja", "serikat buruh", "organisasi pekerja"],
        # === Licensing & permits (21-27) ===
        ["NIB", "Nomor Induk Berusaha", "izin berusaha"],
        ["izin", "perizinan", "lisensi", "permit"],
        ["OSS", "Online Single Submission", "perizinan daring"],
        ["UMKM", "Usaha Mikro Kecil Menengah", "usaha kecil"],
        ["TDP", "Tanda Daftar Perusahaan"],
        ["SIUP", "Surat Izin Usaha Perdagangan", "izin usaha"],
        ["IMB", "Izin Mendirikan Bangunan", "PBG", "Persetujuan Bangunan Gedung"],
        # === Tax & fiscal terms (28-33) ===
        ["pajak", "perpajakan", "fiskal"],
        ["NPWP", "Nomor Pokok Wajib Pajak"],
        ["PPN", "Pajak Pertambahan Nilai", "VAT"],
        ["PPh", "Pajak Penghasilan", "income tax"],
        ["Bea Cukai", "kepabeanan", "cukai"],
        ["retribusi", "pungutan daerah", "retribusi daerah"],
        # === Investment & capital (34-36) ===
        ["modal", "investasi", "penanaman modal"],
        ["PMA", "Penanaman Modal Asing", "investasi asing"],
        ["PMDN", "Penanaman Modal Dalam Negeri", "investasi domestik"],
        # === Land & environment (37-40) ===
        ["tanah", "agraria", "pertanahan"],
        ["lingkungan", "lingkungan hidup", "ekologi"],
        ["Amdal", "Analisis Mengenai Dampak Lingkungan", "kajian lingkungan"],
        ["HGU", "Hak Guna Usaha", "hak atas tanah"],
        # === Regulation type abbreviations (41-47) ===
        ["UU", "Undang-Undang", "undang undang"],
        ["PP", "Peraturan Pemerintah"],
        ["Perpres", "Peraturan Presiden"],
        ["Permen", "Peraturan Menteri"],
        ["Perda", "Peraturan Daerah"],
        ["Perpu", "Peraturan Pemerintah Pengganti Undang-Undang"],
        ["SKB", "Surat Keputusan Bersama"],
        # === Legal code abbreviations (48-50) ===
        ["KUHPerdata", "Kitab Undang-Undang Hukum Perdata", "BW", "Burgerlijk Wetboek"],
        ["KUHP", "Kitab Undang-Undang Hukum Pidana", "KUHPidana"],
        ["KUHAP", "Kitab Undang-Undang Hukum Acara Pidana"],
        # === Legal domain terms (51-55) ===
        ["pidana", "kriminal", "hukum pidana"],
        ["perdata", "sipil", "hukum perdata", "hukum privat"],
        ["kontrak", "perjanjian", "perikatan"],
        ["gugatan", "tuntutan", "dakwaan"],
        ["banding", "naik banding", "upaya hukum banding"],
        # === Specific regulations & programs (56-60) ===
        ["Cipta Kerja", "Omnibus Law", "UU 11/2020"],
        ["data pribadi", "privasi", "PDP", "pelindungan data"],
        ["CSR", "Tanggung Jawab Sosial", "tanggung jawab sosial dan lingkungan", "TJSL"],
        ["BPJS", "Badan Penyelenggara Jaminan Sosial", "jaminan sosial"],
        ["PKB", "Perjanjian Kerja Bersama", "kesepakatan kerja bersama"],
    ]
    
    def expand_query(self, query: str) -> list[str]:
        """
        Generate query variants using rule-based synonym expansion.
        
        Returns the original query plus up to 2 expanded variants:
        1. Original query (always)
        2. Synonym-expanded variant (if synonyms found)
        3. Abbreviation-expanded variant (if abbreviations found)
        
        Args:
            query: Original search query
        
        Returns:
            List of unique query strings (1-3 items)
        """
        queries = [query]
        query_lower = query.lower()
        
        # Find matching synonym groups
        expanded_terms = []
        for group in self._SYNONYM_GROUPS:
            for term in group:
                if term.lower() in query_lower:
                    # Add other terms from the same group
                    alternatives = [t for t in group if t.lower() != term.lower()]
                    if alternatives:
                        expanded_terms.append((term, alternatives))
                    break  # Only match first term per group
        
        if expanded_terms:
            # Variant 1: Replace first matched term with its primary synonym
            variant1 = query
            for original_term, alternatives in expanded_terms[:2]:
                # Case-insensitive replacement with first alternative
                pattern = re.compile(re.escape(original_term), re.IGNORECASE)
                variant1 = pattern.sub(alternatives[0], variant1, count=1)
            if variant1 != query and variant1 not in queries:
                queries.append(variant1)
            
            # Variant 2: Append additional synonym terms as keywords
            extra_keywords = []
            for _, alternatives in expanded_terms:
                extra_keywords.extend(alternatives[:1])
            if extra_keywords:
                variant2 = query + " " + " ".join(extra_keywords[:3])
                if variant2 not in queries:
                    queries.append(variant2)
        
        return queries[:3]  # Max 3 variants
    
    # Compiled regex patterns for legal reference detection.
    #
    # Detects structured Indonesian legal references in queries, such as:
    #   "Pasal 5 UU 11/2020"          → {pasal: "5", jenis_dokumen: "UU", nomor: "11", tahun: "2020"}
    #   "Pasal 12 PP No. 35 Tahun 2021" → {pasal: "12", jenis_dokumen: "PP", nomor: "35", tahun: "2021"}
    #   "UU Nomor 13 Tahun 2003"       → {jenis_dokumen: "UU", nomor: "13", tahun: "2003"}
    #   "PP 5/2021"                     → {jenis_dokumen: "PP", nomor: "5", tahun: "2021"}
    #
    # The detected reference is used to build Qdrant filter_conditions for
    # targeted exact-match retrieval. If the filter returns no results, the
    # caller falls back to normal semantic search (see hybrid_search).
    _LEGAL_REF_PATTERNS: list[re.Pattern[str]] = [
        # Pattern 1: "Pasal X UU/PP/Perpres No. Y Tahun Z" or "Pasal X UU Y/Z"
        re.compile(
            r"[Pp]asal\s+(\d+)"                               # Pasal number
            r"\s+(?:ayat\s+\((\d+)\)\s+)?"                    # Optional ayat
            r"(UU|PP|Perpres|Permen|Perda|Perpu)"              # Regulation type
            r"\s+(?:(?:No(?:mor)?\.?\s*)?(\d+)"                # Nomor
            r"(?:\s+[Tt]ahun\s+|\s*/\s*)(\d{4}))",            # Tahun
            re.IGNORECASE,
        ),
        # Pattern 2: "UU/PP/Perpres No. Y Tahun Z" (no Pasal prefix)
        re.compile(
            r"(UU|PP|Perpres|Permen|Perda|Perpu)"
            r"\s+(?:No(?:mor)?\.?\s*)?(\d+)"
            r"(?:\s+[Tt]ahun\s+|\s*/\s*)(\d{4})",
            re.IGNORECASE,
        ),
        # Pattern 3: "Pasal X UU/PP Y/Z" (compact slash form)
        re.compile(
            r"[Pp]asal\s+(\d+)"
            r"\s+(?:ayat\s+\((\d+)\)\s+)?"
            r"(UU|PP|Perpres|Permen|Perda|Perpu)"
            r"\s+(\d+)/(\d{4})",
            re.IGNORECASE,
        ),
    ]
    
    # Map of full/variant regulation type names to their canonical jenis_dokumen value.
    _JENIS_CANONICAL: dict[str, str] = {
        "uu": "UU",
        "undang-undang": "UU",
        "pp": "PP",
        "peraturan pemerintah": "PP",
        "perpres": "Perpres",
        "peraturan presiden": "Perpres",
        "permen": "Permen",
        "peraturan menteri": "Permen",
        "perda": "Perda",
        "peraturan daerah": "Perda",
        "perpu": "Perpu",
    }
    
    def detect_legal_references(self, query: str) -> dict[str, Any] | None:
        """
        Detect structured Indonesian legal references in a query string.
        
        Scans the query for patterns like "Pasal 5 UU 11/2020" and extracts
        a structured filter_conditions dict suitable for passing directly to
        ``dense_search(filter_conditions=...)``.
        
        Supported patterns:
            - "Pasal 12 PP No. 35 Tahun 2021"
            - "Pasal 5 UU 11/2020"
            - "UU Nomor 13 Tahun 2003"
            - "PP 5/2021"
            - "Pasal 3 ayat (2) Perpres 82/2023"
        
        Returns:
            Dict of Qdrant-filterable field→value pairs, e.g.:
            ``{"jenis_dokumen": "UU", "nomor": "11", "tahun": 2020, "pasal": "5"}``
            Returns ``None`` if no structured reference is detected.
        """
        # Try Pattern 1 / Pattern 3 first (with Pasal)
        for pattern in [self._LEGAL_REF_PATTERNS[0], self._LEGAL_REF_PATTERNS[2]]:
            m = pattern.search(query)
            if m:
                groups = m.groups()
                pasal = groups[0]
                ayat = groups[1]  # May be None
                jenis_raw = groups[2]
                nomor = groups[3]
                tahun = groups[4]
                
                jenis = self._JENIS_CANONICAL.get(jenis_raw.lower(), jenis_raw)
                
                conditions: dict[str, Any] = {
                    "jenis_dokumen": jenis,
                    "nomor": str(nomor),
                    "tahun": int(tahun),
                    "pasal": str(pasal),
                }
                if ayat:
                    conditions["ayat"] = str(ayat)
                
                logger.info(
                    "Legal reference detected: %s → filter %s",
                    m.group(), conditions,
                )
                return conditions
        
        # Try Pattern 2 (regulation without Pasal)
        m = self._LEGAL_REF_PATTERNS[1].search(query)
        if m:
            jenis_raw, nomor, tahun = m.groups()
            jenis = self._JENIS_CANONICAL.get(jenis_raw.lower(), jenis_raw)
            
            conditions = {
                "jenis_dokumen": jenis,
                "nomor": str(nomor),
                "tahun": int(tahun),
            }
            
            logger.info(
                "Legal reference detected: %s → filter %s",
                m.group(), conditions,
            )
            return conditions
        
        return None
    
    def dense_search(
        self,
        query: str,
        top_k: int = 10,
        filter_conditions: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """
        Perform dense vector search using Qdrant.
        
        Args:
            query: Search query in natural language
            top_k: Number of results to return
            filter_conditions: Optional Qdrant filter conditions
        
        Returns:
            List of SearchResult objects sorted by score (descending)
        """
        # Generate query embedding
        query_embedding = self.embedder.embed_query(query)
        
        # Build filter if provided
        search_filter = None
        if filter_conditions:
            conditions = []
            for key, value in filter_conditions.items():
                conditions.append(
                    FieldCondition(key=key, match=MatchValue(value=value))
                )
            search_filter = Filter(must=conditions)
        
        # Search Qdrant (using query_points API for qdrant-client 1.16+)
        from qdrant_client.models import QueryRequest
        
        query_response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=top_k,
            query_filter=search_filter,
            with_payload=True,
        )
        
        # Convert to SearchResult
        search_results = []
        for hit in query_response.points:
            payload = hit.payload
            if payload is None:
                continue
            search_results.append(SearchResult(
                id=int(hit.id),
                text=payload.get("text", ""),
                citation=payload.get("citation", ""),
                citation_id=payload.get("citation_id", ""),
                score=hit.score,
                metadata={
                    k: v for k, v in payload.items()
                    if k not in ("text", "citation", "citation_id")
                },
            ))
        
        return search_results
    
    def sparse_search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[SearchResult]:
        """
        Perform BM25 sparse search over the corpus.
        
        Args:
            query: Search query in natural language
            top_k: Number of results to return
        
        Returns:
            List of SearchResult objects sorted by BM25 score (descending)
        """
        if not self._bm25 or not self._corpus:
            return []
        
        # Tokenize query
        query_tokens = tokenize_indonesian(query)
        
        if not query_tokens:
            return []
        
        # Get BM25 scores
        scores = self._bm25.get_scores(query_tokens)
        
        # Get top-k indices
        scored_indices = [(i, score) for i, score in enumerate(scores)]
        scored_indices.sort(key=lambda x: x[1], reverse=True)
        top_indices = scored_indices[:top_k]
        
        # Build results
        results = []
        for idx, score in top_indices:
            if score > 0:  # Only include non-zero scores
                doc = self._corpus[idx]
                results.append(SearchResult(
                    id=doc["id"],
                    text=doc["text"],
                    citation=doc["citation"],
                    citation_id=doc["citation_id"],
                    score=score,
                    metadata=doc["metadata"],
                ))
        
        return results
    
    def _rrf_fusion(
        self,
        dense_results: list[SearchResult],
        sparse_results: list[SearchResult],
        k: int = RRF_K,
    ) -> list[tuple[SearchResult, float]]:
        """
        Apply Reciprocal Rank Fusion to combine results.
        
        RRF Score = sum(1 / (k + rank)) for each list where document appears
        
        Args:
            dense_results: Results from dense search
            sparse_results: Results from sparse search
            k: RRF constant (default 60)
        
        Returns:
            List of (SearchResult, rrf_score) tuples sorted by RRF score
        """
        # Build ID to result mapping and accumulate RRF scores
        rrf_scores: dict[int, float] = {}
        result_map: dict[int, SearchResult] = {}
        
        # Process dense results
        for rank, result in enumerate(dense_results, start=1):
            doc_id = result.id
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k + rank)
            if doc_id not in result_map:
                result_map[doc_id] = result
        
        # Process sparse results
        for rank, result in enumerate(sparse_results, start=1):
            doc_id = result.id
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k + rank)
            if doc_id not in result_map:
                result_map[doc_id] = result
        
        # Sort by RRF score
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        
        return [(result_map[doc_id], rrf_scores[doc_id]) for doc_id in sorted_ids]
    
    def _rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int,
    ) -> list[SearchResult]:
        """
        Re-rank results using CrossEncoder for improved relevance.
        
        Args:
            query: Original search query
            results: Initial search results to re-rank
            top_k: Number of results to return after re-ranking
        
        Returns:
            Re-ranked list of SearchResult objects
        """
        if not self.reranker or not results:
            return results[:top_k]
        
        # Prepare query-document pairs for CrossEncoder
        pairs = [(query, result.text) for result in results]
        
        try:
            # Get cross-encoder scores
            start = time.perf_counter()
            scores = self.reranker.predict(pairs)
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info(f"CrossEncoder reranked {len(pairs)} candidates in {elapsed_ms:.1f}ms")
            
            # Create scored results and sort by cross-encoder score
            scored_results = list(zip(results, scores))
            scored_results.sort(key=lambda x: x[1], reverse=True)
            
            # Return top_k with updated scores
            reranked = []
            for result, ce_score in scored_results[:top_k]:
                # Normalize cross-encoder score to 0-1 range
                # mMiniLMv2 CE scores typically fall in [-5, +5] range
                normalized_score = max(0.0, min(1.0, (ce_score + 5) / 10))
                reranked.append(SearchResult(
                    id=result.id,
                    text=result.text,
                    citation=result.citation,
                    citation_id=result.citation_id,
                    score=normalized_score,
                    metadata=result.metadata,
                ))
            
            logger.debug(f"Re-ranked {len(results)} results to top {len(reranked)}")
            return reranked
            
        except Exception as e:
            logger.warning(f"Re-ranking failed, returning original results: {e}")
            return results[:top_k]
    
    def _extract_regulation_ids(self, results: list[SearchResult]) -> set[str]:
        """Extract unique regulation IDs from search result payloads.

        Builds canonical ``{jenis}_{nomor}_{tahun}`` IDs from the metadata
        fields typically stored in Qdrant payloads.
        """
        reg_ids: set[str] = set()
        for r in results:
            jenis = r.metadata.get("jenis_dokumen", "")
            nomor = r.metadata.get("nomor", "")
            tahun = r.metadata.get("tahun", "")
            if jenis and nomor and tahun:
                reg_ids.add(f"{jenis.lower()}_{nomor}_{tahun}")
        return reg_ids

    def _boost_with_kg(
        self,
        candidates: list[SearchResult],
        boost_factor: float = 1.15,
    ) -> list[SearchResult]:
        """Boost scores of candidates whose regulation is KG-related to top results.

        Workflow:
        1. Extract regulation IDs from the top candidates.
        2. Query the knowledge graph for 1-hop related regulations.
        3. For every candidate whose regulation appears in the related set,
           multiply its score by *boost_factor*.

        This enables "regulation-aware" retrieval without changing the response
        schema — only score ordering is affected.

        Args:
            candidates: Current search candidates with RRF scores.
            boost_factor: Multiplicative boost (default 1.15 = +15%).

        Returns:
            Candidates with boosted scores, re-sorted by score descending.
        """
        if not self.knowledge_graph:
            return candidates

        # Step 1: Extract regulation IDs from top candidates
        source_reg_ids = self._extract_regulation_ids(candidates[:5])
        if not source_reg_ids:
            return candidates

        # Step 2: Query KG for related regulations (1-hop for speed)
        related_reg_ids: set[str] = set()
        for reg_id in source_reg_ids:
            try:
                related = self.knowledge_graph.get_related_regulations(
                    reg_id, max_hops=1, timeout_ms=200
                )
                for node in related:
                    node_id = node.get("id", "")
                    if node_id:
                        related_reg_ids.add(node_id)
            except Exception as e:
                logger.debug(f"KG traversal failed for {reg_id}: {e}")

        if not related_reg_ids:
            return candidates

        logger.debug(
            "KG boost: %d source regs → %d related regs",
            len(source_reg_ids), len(related_reg_ids),
        )

        # Step 3: Boost candidates from related regulations
        boosted: list[SearchResult] = []
        for r in candidates:
            jenis = r.metadata.get("jenis_dokumen", "")
            nomor = r.metadata.get("nomor", "")
            tahun = r.metadata.get("tahun", "")
            cand_reg_id = f"{jenis.lower()}_{nomor}_{tahun}" if (jenis and nomor and tahun) else ""

            if cand_reg_id and cand_reg_id in related_reg_ids:
                boosted.append(SearchResult(
                    id=r.id,
                    text=r.text,
                    citation=r.citation,
                    citation_id=r.citation_id,
                    score=r.score * boost_factor,
                    metadata=r.metadata,
                ))
            else:
                boosted.append(r)

        # Re-sort by boosted score
        boosted.sort(key=lambda x: x.score, reverse=True)
        return boosted

    def _boost_with_authority(
        self,
        candidates: list[SearchResult],
    ) -> list[SearchResult]:
        """Boost/penalize candidates based on document type authority hierarchy.

        UU (Undang-Undang) is the highest legal authority; Perda (regional
        regulations) are lowest.  Without a CrossEncoder reranker, this
        prevents regional Perda chunks from outranking national UU/PP chunks
        that have nearly identical cosine similarity scores.

        Multipliers:
            UU      ×1.50  — national statute, highest authority
            PP      ×1.20  — government regulation
            Perpres ×1.10  — presidential regulation
            Permen  ×1.05  — ministerial regulation
            Perda   ×0.60  — regional regulation (heavy penalty for national queries)
            other   ×1.00  — unknown/neutral

        Returns:
            Candidates re-sorted by authority-boosted score.
        """
        AUTHORITY_MULTIPLIERS: dict[str, float] = {
            "UU": 1.50,
            "PP": 1.20,
            "Perpres": 1.10,
            "Permen": 1.05,
            "Perda": 0.60,
        }

        boosted: list[SearchResult] = []
        for r in candidates:
            jenis = r.metadata.get("jenis_dokumen", "")
            multiplier = AUTHORITY_MULTIPLIERS.get(jenis, 1.00)
            boosted.append(SearchResult(
                id=r.id,
                text=r.text,
                citation=r.citation,
                citation_id=r.citation_id,
                score=r.score * multiplier,
                metadata=r.metadata,
            ))

        boosted.sort(key=lambda x: x.score, reverse=True)
        logger.debug(
            "Authority boost applied: %d candidates, top jenis=%s",
            len(boosted),
            boosted[0].metadata.get("jenis_dokumen", "?") if boosted else "none",
        )
        return boosted
    
    def _is_national_law_query(self, query: str) -> bool:
        """Return True if query is clearly about national legislation, not regional."""
        q = query.lower()
        return any(kw in q for kw in self._NATIONAL_LAW_KEYWORDS)

    def _prioritize_national_docs(
        self,
        candidates: list[SearchResult],
        top_k: int,
    ) -> list[SearchResult]:
        """When no reranker and query is national-law, put UU/PP/Perpres/Permen first.

        Perda chunks are only included if there are fewer than top_k national docs.
        """
        national_types = {"UU", "PP", "Perpres", "Permen"}
        national = [r for r in candidates if r.metadata.get("jenis_dokumen") in national_types]
        regional = [r for r in candidates if r.metadata.get("jenis_dokumen") not in national_types]

        # Combine: national first, then regional as fallback
        prioritized = national + regional
        logger.debug(
            "National-law query: %d national, %d regional candidates",
            len(national), len(regional),
        )
        return prioritized[:top_k * 2]  # Return wider pool, caller slices to top_k

    def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        dense_weight: float = 0.6,
        dense_top_k: int | None = None,
        sparse_top_k: int | None = None,
        filter_conditions: dict[str, Any] | None = None,
        use_reranking: bool = True,
        expand_queries: bool = True,
        min_score: float | None = None,
    ) -> list[SearchResult]:
        """
        Perform hybrid search combining dense and sparse retrieval.
        
        Uses Reciprocal Rank Fusion (RRF) to merge results from both methods,
        optionally followed by CrossEncoder re-ranking for improved relevance.
        
        Supports query expansion: generates synonym variants of the query
        to improve recall for Indonesian legal abbreviations.
        
        Legal reference detection (auto-filter):
            When ``filter_conditions`` is not provided, the query is scanned for
            structured legal references (e.g. "Pasal 5 UU 11/2020").  If found,
            the extracted fields are used as Qdrant filter conditions for targeted
            retrieval.  If the filtered search returns zero results, the filter is
            discarded and a normal unfiltered search is performed as fallback.
        
        Args:
            query: Search query in natural language
            top_k: Number of final results to return
            dense_weight: Weight for dense results (0-1, currently unused with RRF)
            dense_top_k: Number of dense results to retrieve (default: 2 * top_k)
            sparse_top_k: Number of sparse results to retrieve (default: 2 * top_k)
            filter_conditions: Optional filter for dense search.  When ``None``,
                legal reference auto-detection is used instead.
            use_reranking: Whether to apply CrossEncoder re-ranking (default: True)
            expand_queries: Whether to expand query with synonyms (default: True)
            min_score: Minimum score threshold to filter results (default: None)
        
        Returns:
            List of SearchResult objects with RRF-fused (and optionally re-ranked) scores
        """
        # Default retrieval counts - fetch more if reranking
        # Without a reranker, use a larger candidate pool to improve RRF recall
        if use_reranking and self.reranker:
            rerank_multiplier = 3   # CrossEncoder will filter from larger pool
        elif not self.reranker:
            rerank_multiplier = 4   # No reranker: fetch more, authority boost sorts them
        else:
            rerank_multiplier = 2
        if dense_top_k is None:
            dense_top_k = top_k * rerank_multiplier
        if sparse_top_k is None:
            sparse_top_k = top_k * rerank_multiplier
        
        # --- Legal reference auto-detection ---
        # When no explicit filter_conditions are provided, attempt to detect
        # structured references (e.g. "Pasal 5 UU 11/2020") and build a
        # targeted Qdrant filter.  The filter is used optimistically: if it
        # yields zero dense results we fall back to unfiltered search.
        auto_detected_filter: dict[str, Any] | None = None
        if filter_conditions is None:
            auto_detected_filter = self.detect_legal_references(query)
            if auto_detected_filter:
                filter_conditions = auto_detected_filter
                logger.debug(
                    "Auto-detected legal reference filter: %s", filter_conditions
                )
        
        # Get query variants
        if expand_queries:
            queries = self.expand_query(query)
            logger.debug(f"Expanded query into {len(queries)} variants: {queries}")
        else:
            queries = [query]
        
        # Collect results from all query variants
        all_dense_results: list[SearchResult] = []
        all_sparse_results: list[SearchResult] = []
        
        for q in queries:
            dense_results = self.dense_search(
                q, top_k=dense_top_k, filter_conditions=filter_conditions
            )
            sparse_results = self.sparse_search(q, top_k=sparse_top_k)
            all_dense_results.extend(dense_results)
            all_sparse_results.extend(sparse_results)
        
        # --- Filter fallback ---
        # If the auto-detected filter produced zero dense results, retry
        # without the filter so the user still gets semantic search results.
        if auto_detected_filter and not all_dense_results:
            logger.info(
                "Auto-detected filter returned 0 dense results; "
                "falling back to unfiltered search."
            )
            filter_conditions = None
            all_dense_results = []
            for q in queries:
                dense_results = self.dense_search(
                    q, top_k=dense_top_k, filter_conditions=None
                )
                all_dense_results.extend(dense_results)
        
        # Deduplicate by ID, keeping highest score per source
        def dedup(results: list[SearchResult]) -> list[SearchResult]:
            best: dict[int, SearchResult] = {}
            for r in results:
                if r.id not in best or r.score > best[r.id].score:
                    best[r.id] = r
            return sorted(best.values(), key=lambda x: x.score, reverse=True)
        
        dense_deduped = dedup(all_dense_results)
        sparse_deduped = dedup(all_sparse_results)
        
        # Fuse with RRF
        fused = self._rrf_fusion(dense_deduped, sparse_deduped)
        
        # Get candidates for potential re-ranking
        candidates = []
        for result, rrf_score in fused[:top_k * 2]:  # Get more candidates for reranking
            candidates.append(SearchResult(
                id=result.id,
                text=result.text,
                citation=result.citation,
                citation_id=result.citation_id,
                score=rrf_score,
                metadata=result.metadata,
            ))
        
        # Apply KG-aware boosting (before reranking so reranker sees adjusted order)
        candidates = self._boost_with_kg(candidates)

        # Apply document authority boosting (UU > PP > Perpres > Permen > Perda)
        candidates = self._boost_with_authority(candidates)

        # Hard-prioritize national docs for national-law queries (when no reranker)
        if not self.reranker and self._is_national_law_query(query):
            candidates = self._prioritize_national_docs(candidates, top_k)
        
        # Apply CrossEncoder re-ranking if enabled (always re-rank against original query)
        # Apply minimum score filtering if specified
        if min_score is not None:
            candidates = [r for r in candidates if r.score >= min_score]
            logger.debug(f"Filtered to {len(candidates)} results with min_score={min_score}")
        
        if use_reranking and self.reranker:
            return self._rerank(query, candidates, top_k)
        
        # Return top_k without re-ranking
        return candidates[:top_k]
    
    def search_by_document_type(
        self,
        query: str,
        jenis_dokumen: str,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """
        Search within a specific document type.
        
        Args:
            query: Search query
            jenis_dokumen: Document type (UU, PP, Perpres, etc.)
            top_k: Number of results
        
        Returns:
            Filtered search results
        """
        return self.hybrid_search(
            query=query,
            top_k=top_k,
            filter_conditions={"jenis_dokumen": jenis_dokumen},
        )
    
    def get_stats(self) -> dict[str, Any]:
        """Get retriever statistics."""
        collection_info = self.client.get_collection(self.collection_name)
        return {
            "collection_name": self.collection_name,
            "total_documents": collection_info.points_count,
            "corpus_loaded": len(self._corpus),
            "bm25_initialized": self._bm25 is not None,
            "embedding_model": EMBEDDING_MODEL,
            "embedding_dim": EMBEDDING_DIM,
        }

    def get_chunk_counts_by_regulation(self) -> dict[str, int]:
        """Count Qdrant chunks grouped by citation_id prefix.

        Uses the already-loaded corpus (self._corpus) to aggregate counts.
        Returns: {"uu_11_2020": 145, "pp_35_2021": 67, ...}
        Falls back to empty dict on any error.
        """
        try:
            counts: dict[str, int] = {}
            for doc in self._corpus:
                cid = doc.get("citation_id", "")
                if cid:
                    # Normalize: lowercase, strip to base regulation ID
                    # citation_id may be "uu_11_2020" or "uu_11_2020_pasal_5"
                    parts = cid.lower().split("_pasal_")
                    base_id = parts[0]
                    counts[base_id] = counts.get(base_id, 0) + 1
            return counts
        except Exception:
            return {}


# Convenience function for quick access
def get_retriever(
    qdrant_url: str = QDRANT_URL,
    collection_name: str = COLLECTION_NAME,
) -> HybridRetriever:
    """Factory function to get a configured retriever instance."""
    return HybridRetriever(
        qdrant_url=qdrant_url,
        collection_name=collection_name,
    )


if __name__ == "__main__":
    # Quick test
    print("Initializing HybridRetriever...")
    retriever = get_retriever()
    
    stats = retriever.get_stats()
    print(f"Stats: {stats}")
    
    # Test query
    query = "Apa itu Undang-Undang Cipta Kerja?"
    print(f"\nQuery: {query}")
    
    results = retriever.hybrid_search(query, top_k=3)
    print(f"Found {len(results)} results:")
    for i, r in enumerate(results, 1):
        print(f"\n{i}. {r.citation}")
        print(f"   Score: {r.score:.4f}")
        print(f"   Text: {r.text[:100]}...")
