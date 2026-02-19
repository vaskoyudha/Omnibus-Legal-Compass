"""
Qdrant ingestion pipeline with HuggingFace embeddings.
Ingests Indonesian legal documents for RAG retrieval.

Uses sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 for
multilingual support (including Bahasa Indonesia).

Supports incremental ingestion with deduplication by composite key
``(jenis_dokumen, nomor, tahun, pasal, ayat)`` so that re-running the
script does **not** wipe existing data unless ``--force-reindex`` is
explicitly passed.
"""
import json
import os
import hashlib
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Set, Tuple

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_huggingface import HuggingFaceEmbeddings
from tqdm import tqdm

# Future integration hook — adapters from format_converter.py are
# available for use when external data sources are integrated (Phase 2).
# from backend.scripts.format_converter import RegulationChunk, ManualAdapter

# Load environment variables
load_dotenv()

# Constants - HuggingFace multilingual model (free, local, supports Indonesian)
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384  # paraphrase-multilingual-MiniLM-L12-v2 dimension
COLLECTION_NAME = "indonesian_legal_docs"

# NVIDIA NIM embedding configuration (mirrors retriever.py)
USE_NVIDIA_EMBEDDINGS = os.getenv("USE_NVIDIA_EMBEDDINGS", "false").lower() == "true"
NVIDIA_EMBEDDING_MODEL = "nvidia/nv-embedqa-e5-v5"
NVIDIA_EMBEDDING_DIM = 1024

# Jina AI embedding configuration (mirrors retriever.py)
USE_JINA_EMBEDDINGS = os.getenv("USE_JINA_EMBEDDINGS", "false").lower() == "true"
JINA_EMBEDDING_MODEL = os.getenv("JINA_EMBEDDING_MODEL", "jina-embeddings-v3")
JINA_EMBEDDING_DIM = int(os.getenv("JINA_EMBEDDING_DIM", "1024"))

# Document type mappings for citations
DOC_TYPE_NAMES = {
    "UU": "UU",
    "PP": "PP",
    "Perpres": "Perpres",
    "Perda": "Perda",
    "Permen": "Permen",
}

# Regex patterns for penjelasan (explanation) section detection
_PENJELASAN_PATTERNS = [
    re.compile(r"PENJELASAN\s+ATAS", re.IGNORECASE),
    re.compile(r"^PENJELASAN$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"[Pp]enjelasan\s+[Pp]asal", re.IGNORECASE),
    re.compile(r"[Pp]enjelasan\s+[Uu]mum", re.IGNORECASE),
]

# Minimum and maximum chunk sizes for structural chunking
MIN_CHUNK_SIZE = 50
MAX_CHUNK_SIZE = 2000

# ---------------------------------------------------------------------------
# Structure-aware chunking patterns for Indonesian legal documents
# ---------------------------------------------------------------------------
# Legal hierarchy: BAB (chapter) → Pasal (article) → Ayat (verse/paragraph)
# These patterns detect structural boundaries in raw text blocks that were
# not pre-split into individual Pasal/Ayat entries.

_BAB_BOUNDARY = re.compile(
    r"(?:^|\n)\s*BAB\s+([IVXLCDM]+)",
    re.IGNORECASE,
)
_PASAL_BOUNDARY = re.compile(
    # Negative lookbehind avoids matching cross-references like "dalam Pasal 5"
    r"(?:^|\n)\s*(?<!dalam\s)(?<!ke\s)Pasal\s+(\d+[A-Z]?)\b",
)
_AYAT_BOUNDARY = re.compile(
    r"(?:^|\n)\s*\((\d+)\)\s",
)
_BAGIAN_BOUNDARY = re.compile(
    r"(?:^|\n)\s*Bagian\s+(?:Kesatu|Kedua|Ketiga|Keempat|Kelima|Keenam|Ketujuh|Kedelapan|Kesembilan|Kesepuluh)\b",
    re.IGNORECASE,
)
_PARAGRAF_BOUNDARY = re.compile(
    r"(?:^|\n)\s*Paragraf\s+\d+",
    re.IGNORECASE,
)


def _split_by_legal_boundaries(text: str) -> list[str]:
    """Split a raw text block along BAB / Pasal / Ayat structural boundaries.

    The function scans *text* for structural markers (BAB, Pasal, Ayat,
    Bagian, Paragraf) and splits at those positions so that each resulting
    segment starts at a boundary marker.  If no boundaries are found, the
    original text is returned as a single-element list.

    The split preserves the boundary marker text in the resulting segment
    (it becomes the first line of that segment), so downstream consumers
    can identify which structural unit the segment belongs to.

    Returns:
        List of text segments, each starting at a structural boundary
        (except possibly the first segment which contains any preamble
        text before the first boundary).
    """
    # Collect all boundary match positions, preferring higher-level markers
    boundaries: list[int] = []
    for pattern in (_BAB_BOUNDARY, _PASAL_BOUNDARY, _BAGIAN_BOUNDARY,
                    _PARAGRAF_BOUNDARY, _AYAT_BOUNDARY):
        for m in pattern.finditer(text):
            # Use the start of the overall match (includes leading newline)
            pos = m.start()
            # Advance past the leading newline if present
            while pos < len(text) and text[pos] in ("\n", "\r", " "):
                # Stop at the first non-whitespace to keep the marker text
                if text[pos] not in ("\n", "\r"):
                    break
                pos += 1
            boundaries.append(pos)

    if not boundaries:
        return [text]

    # Deduplicate and sort
    boundaries = sorted(set(boundaries))

    segments: list[str] = []
    # Preamble text before first boundary
    if boundaries[0] > 0:
        preamble = text[: boundaries[0]].strip()
        if preamble:
            segments.append(preamble)

    for i, start in enumerate(boundaries):
        end = boundaries[i + 1] if i + 1 < len(boundaries) else len(text)
        segment = text[start:end].strip()
        if segment:
            segments.append(segment)

    return segments if segments else [text]


def detect_penjelasan(doc: dict[str, Any]) -> bool:
    """
    Detect whether a document chunk is from a Penjelasan (explanation) section.

    Checks both the ``bab`` field (Indonesian laws often label penjelasan
    chapters) and the text content for penjelasan markers.

    Returns:
        True if the chunk is identified as penjelasan content.
    """
    # Check bab field for penjelasan indicators
    bab = str(doc.get("bab", "")).strip()
    if bab and re.search(r"penjelasan", bab, re.IGNORECASE):
        return True

    # Check text content for penjelasan patterns
    text = doc.get("text", "")
    for pattern in _PENJELASAN_PATTERNS:
        if pattern.search(text):
            return True

    # Check judul/tentang for penjelasan markers
    judul = str(doc.get("judul", ""))
    if re.search(r"penjelasan", judul, re.IGNORECASE):
        return True

    return False


def extract_ayat_from_text(text: str, existing_ayat: str | None) -> str | None:
    """
    Extract an ayat (verse) number from the start of a text segment when
    the metadata is missing.

    Why:
        Some Azzindani-sourced entries have ``ayat`` set to ``null`` even
        though the textual content begins with an ayat marker like "(1)".
        This helper fills missing ``ayat`` metadata by parsing that prefix.

    What:
        Looks only for a parenthesised integer at the start of the text,
        e.g. "(1) ..." and returns the digits as a string ("1").

    Constraints:
    - Only attempts extraction when ``existing_ayat`` is falsy; existing
      metadata is preserved and never overwritten.
    - Matches are anchored to the beginning of the text and limited to
      the first 10 characters to avoid false positives later in the
      segment. The exact regex used is ``r'^\\s*\\((\\d+)\\)'``.

    Args:
        text: Document text to inspect.
        existing_ayat: Previously-extracted ayat metadata (may be None).

    Returns:
        The ayat number as a string if extracted, otherwise None. If
        ``existing_ayat`` is provided, it is returned unchanged.
    """
    # Preserve existing metadata
    if existing_ayat:
        return existing_ayat

    if not text:
        return None

    # Look only at the start of the text (first 10 chars) to avoid
    # matching parenthesised numbers occurring later in the paragraph.
    prefix = text[:10]
    match = re.match(r"^\s*\((\d+)\)", prefix)
    if match:
        return match.group(1)
    return None


def build_parent_context(metadata: dict[str, Any]) -> str:
    """
    Build a hierarchical breadcrumb path for a legal document chunk.

    Format: ``"UU No. 11 Tahun 2020 > BAB III > Pasal 5 > Ayat (1)"``

    This serves as both ``parent_context`` and ``full_path`` in the
    chunk payload, enabling downstream consumers to understand exactly
    where a chunk sits in the legal document hierarchy.
    """
    parts: list[str] = []

    # Document identity
    doc_type = metadata.get("jenis_dokumen", "")
    nomor = metadata.get("nomor", "")
    tahun = metadata.get("tahun", "")
    if doc_type and nomor:
        parts.append(f"{doc_type} No. {nomor} Tahun {tahun}")

    judul = metadata.get("judul", "")
    if judul and parts:
        parts[-1] += f" tentang {judul}"

    # Chapter
    bab = metadata.get("bab")
    if bab:
        parts.append(f"BAB {bab}")

    # Article
    pasal = metadata.get("pasal")
    if pasal:
        parts.append(f"Pasal {pasal}")

    # Verse
    ayat = metadata.get("ayat")
    if ayat:
        parts.append(f"Ayat ({ayat})")

    return " > ".join(parts)


def format_citation(metadata: dict[str, Any]) -> str:
    """
    Format citation string from document metadata.
    
    Examples:
    - UU No. 11 Tahun 2020 tentang Cipta Kerja, Pasal 5 Ayat (1)
    - PP No. 24 Tahun 2018 tentang Perizinan Berusaha, Pasal 3
    """
    doc_type = metadata.get("jenis_dokumen", "")
    nomor = metadata.get("nomor", "")
    tahun = metadata.get("tahun", "")
    judul = metadata.get("judul", "")
    
    # Base citation
    citation = f"{doc_type} No. {nomor} Tahun {tahun}"
    
    if judul:
        citation += f" tentang {judul}"
    
    # Add article reference
    pasal = metadata.get("pasal")
    if pasal:
        citation += f", Pasal {pasal}"
    
    ayat = metadata.get("ayat")
    if ayat:
        citation += f" Ayat ({ayat})"
    
    bab = metadata.get("bab")
    if bab and not pasal:
        citation += f", Bab {bab}"
    
    return citation


def generate_citation_id(metadata: dict[str, Any]) -> str:
    """
    Generate unique citation ID for a document chunk.
    
    Format: {jenis}_{nomor}_{tahun}_Pasal{pasal}[_Ayat{ayat}]
    Example: UU_11_2020_Pasal5_Ayat1
    """
    parts = [
        metadata.get("jenis_dokumen", "DOC"),
        str(metadata.get("nomor", "0")),
        str(metadata.get("tahun", "0")),
    ]
    
    if metadata.get("pasal"):
        parts.append(f"Pasal{metadata['pasal']}")
    
    if metadata.get("ayat"):
        parts.append(f"Ayat{metadata['ayat']}")
    
    if metadata.get("bab") and not metadata.get("pasal"):
        parts.append(f"Bab{metadata['bab']}")
    
    return "_".join(parts)


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 100,
) -> list[str]:
    """
    Split long text into overlapping chunks by sentence boundaries.
    
    Args:
        text: Input text to split
        chunk_size: Target chunk size in characters
        overlap: Overlap between consecutive chunks in characters
    
    Returns:
        List of text chunks (single-element list if text is short enough)
    """
    if len(text) <= chunk_size:
        return [text]
    
    import re
    
    # Split by sentence boundaries common in Indonesian legal text
    # Handles ". ", "; ", and newlines
    sentences = re.split(r'(?<=[.;])\s+|\n+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        candidate = (current_chunk + " " + sentence).strip() if current_chunk else sentence
        
        if len(candidate) <= chunk_size:
            current_chunk = candidate
        else:
            # Save current chunk if it has content
            if current_chunk:
                chunks.append(current_chunk)
                # Start new chunk with overlap from end of previous
                if overlap > 0 and len(current_chunk) > overlap:
                    overlap_text = current_chunk[-overlap:]
                    # Find word boundary in overlap region
                    space_idx = overlap_text.find(" ")
                    if space_idx > 0:
                        overlap_text = overlap_text[space_idx + 1:]
                    current_chunk = (overlap_text + " " + sentence).strip()
                else:
                    current_chunk = sentence
            else:
                # Single sentence exceeds chunk_size — keep it as-is
                chunks.append(sentence)
                current_chunk = ""
    
    # Don't forget the last chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def create_document_chunks(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Create chunks from legal documents with metadata for citations.

    **Chunking strategy** (Pasal-based, per Phase 2 plan §3.2):

    1. Each input document entry is treated as a natural legal unit
       (typically one Pasal or one Ayat).
    2. If the text is ≤ ``MAX_CHUNK_SIZE`` (2000 chars) and ≥
       ``MIN_CHUNK_SIZE`` (50 chars), it becomes a single chunk.
    3. If the text exceeds ``MAX_CHUNK_SIZE``, it is split into
       sub-chunks using sentence-boundary splitting (fallback to
       the existing ``chunk_text`` function).
    4. Chunks shorter than ``MIN_CHUNK_SIZE`` are skipped.

    **Hierarchy metadata** added to every chunk:

    - ``parent_context`` / ``full_path``: breadcrumb path
      e.g. ``"UU No. 11 Tahun 2020 tentang Cipta Kerja > BAB III > Pasal 5 > Ayat (1)"``
    - ``parent_bab``: BAB identifier (or empty string)
    - ``parent_pasal``: Pasal number (or empty string)
    - ``parent_ayat``: Ayat number (or empty string)
    - ``is_penjelasan``: boolean — True if chunk is from an
      explanation (Penjelasan) section
    """
    chunks = []

    for doc in documents:
        # Extract text
        text = doc.get("text", "")
        if not text or len(text.strip()) < MIN_CHUNK_SIZE:
            continue

        text = text.strip()

        # Build base metadata (excluding text)
        metadata = {
            "jenis_dokumen": doc.get("jenis_dokumen", ""),
            "nomor": doc.get("nomor", ""),
            "tahun": doc.get("tahun", 0),
            "judul": doc.get("judul", ""),
            "tentang": doc.get("tentang", ""),
        }

        # Optional standard fields
        for field in ["bab", "pasal", "ayat"]:
            if field in doc:
                metadata[field] = doc[field]

        # If ayat metadata is missing, attempt to extract from the text
        # prefix (e.g. "(1) ...") using extract_ayat_from_text(). This
        # preserves any existing ayat value and only fills when absent.
        metadata["ayat"] = extract_ayat_from_text(text, metadata.get("ayat"))

        # --- Phase 2 §3.2: Hierarchy metadata ---
        is_penjelasan = detect_penjelasan(doc)
        parent_context = build_parent_context(metadata)

        metadata["parent_context"] = parent_context
        metadata["full_path"] = parent_context  # alias
        metadata["parent_bab"] = str(metadata.get("bab", ""))
        metadata["parent_pasal"] = str(metadata.get("pasal", ""))
        metadata["parent_ayat"] = str(metadata.get("ayat", ""))
        metadata["is_penjelasan"] = is_penjelasan

        # Generate base citation ID and citation string
        base_citation_id = generate_citation_id(metadata)
        base_citation = format_citation(metadata)

        # --- Phase 2 §3.2 + Phase 4: Pasal-based + structure-aware chunking ---
        # Each document entry is already a legal unit (Pasal/Ayat).
        # Only split if the text exceeds MAX_CHUNK_SIZE.
        if len(text) <= MAX_CHUNK_SIZE:
            # Single chunk — the natural legal unit
            chunks.append({
                "text": text,
                "citation_id": base_citation_id,
                "citation": base_citation,
                "metadata": metadata,
            })
        else:
            # --- Structure-aware splitting (Phase 4 enhancement) ---
            # First attempt: split along BAB/Pasal/Ayat boundaries so
            # chunks respect the legal hierarchy. Only fall back to
            # sentence-boundary splitting for segments that still exceed
            # MAX_CHUNK_SIZE after structural splitting.
            structural_segments = _split_by_legal_boundaries(text)
            final_pieces: list[str] = []
            for segment in structural_segments:
                if len(segment) <= MAX_CHUNK_SIZE:
                    final_pieces.append(segment)
                else:
                    # Sub-split oversized segments using sentence boundaries
                    final_pieces.extend(
                        chunk_text(segment, chunk_size=MAX_CHUNK_SIZE, overlap=100)
                    )

            for chunk_idx, chunk_text_piece in enumerate(final_pieces):
                if len(chunk_text_piece.strip()) < MIN_CHUNK_SIZE:
                    continue
                part_num = chunk_idx + 1
                cid = f"{base_citation_id}_chunk{part_num}"
                cit = f"{base_citation} (bagian {part_num})"
                chunks.append({
                    "text": chunk_text_piece,
                    "citation_id": cid,
                    "citation": cit,
                    "metadata": metadata,
                })

    return chunks


def get_collection_config() -> dict[str, Any]:
    """
    Get Qdrant collection configuration.
    
    Dimension is determined by the active embedder (precedence: Jina > NVIDIA > HuggingFace):
    - Jina jina-embeddings-v3: 1024 dimensions (default)
    - NVIDIA NV-Embed-QA: 1024 dimensions
    - HuggingFace MiniLM: 384 dimensions
    """
    if USE_JINA_EMBEDDINGS:
        dim = JINA_EMBEDDING_DIM
    elif USE_NVIDIA_EMBEDDINGS:
        dim = NVIDIA_EMBEDDING_DIM
    else:
        dim = EMBEDDING_DIM
    return {
        "vectors_config": {
            "size": dim,
            "distance": "Cosine",
        }
    }


def create_point_struct(
    point_id: int,
    chunk: dict[str, Any],
    embedding: list[float],
    source: str = "manual",
) -> PointStruct:
    """
    Create a Qdrant PointStruct from a chunk and its embedding.

    Args:
        point_id: Unique integer identifier for the point.
        chunk: Document chunk dict with ``text``, ``citation_id``,
            ``citation``, and ``metadata`` keys.
        embedding: Dense vector for the chunk text.
        source: Provenance tag (e.g. ``"manual"``,
            ``"huggingface_azzindani"``, ``"otf_peraturan"``).

    Returns:
        A :class:`PointStruct` ready for upsert into Qdrant.
    """
    # Flatten metadata into payload for filtering
    payload = {
        "text": chunk["text"],
        "citation_id": chunk["citation_id"],
        "citation": chunk.get("citation", ""),
        **chunk["metadata"],
        # Provenance / tracking fields
        "source": source,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }
    
    return PointStruct(
        id=point_id,
        vector=embedding,
        payload=payload
    )


# ---------------------------------------------------------------------------
# Deduplication helpers
# ---------------------------------------------------------------------------

def get_existing_keys(
    client: QdrantClient,
    collection_name: str,
) -> Set[Tuple[str, str, str, str, str]]:
    """Fetch all composite keys already stored in a Qdrant collection.

    The composite key is ``(jenis_dokumen, nomor, tahun, pasal, ayat)``
    which uniquely identifies a regulation chunk.

    Args:
        client: Active Qdrant client.
        collection_name: Name of the target collection.

    Returns:
        A set of 5-tuples representing existing document chunks.
    """
    existing_keys: Set[Tuple[str, str, str, str, str]] = set()

    # Scroll through all points (vectors not needed)
    scroll_response = client.scroll(
        collection_name=collection_name,
        limit=10000,
        with_payload=True,
        with_vectors=False,
    )

    points, next_offset = scroll_response

    while points:
        for point in points:
            payload = point.payload or {}
            key = (
                payload.get("jenis_dokumen", ""),
                str(payload.get("nomor", "")),
                str(payload.get("tahun", "")),
                payload.get("pasal", ""),
                payload.get("ayat", ""),
            )
            existing_keys.add(key)

        if next_offset is None:
            break

        scroll_response = client.scroll(
            collection_name=collection_name,
            limit=10000,
            offset=next_offset,
            with_payload=True,
            with_vectors=False,
        )
        points, next_offset = scroll_response

    return existing_keys


def filter_duplicates(
    chunks: list[dict[str, Any]],
    existing_keys: Set[Tuple[str, str, str, str, str]],
) -> list[dict[str, Any]]:
    """Remove chunks whose composite key already exists in Qdrant.

    Args:
        chunks: List of document chunk dicts (each with a ``metadata``
            sub-dict).
        existing_keys: Set of 5-tuples from :func:`get_existing_keys`.

    Returns:
        Filtered list containing only **new** chunks.
    """
    new_chunks: list[dict[str, Any]] = []

    for chunk in chunks:
        metadata = chunk["metadata"]
        key = (
            metadata.get("jenis_dokumen", ""),
            str(metadata.get("nomor", "")),
            str(metadata.get("tahun", "")),
            metadata.get("pasal", ""),
            metadata.get("ayat", ""),
        )

        if key not in existing_keys:
            new_chunks.append(chunk)

    return new_chunks


# ---------------------------------------------------------------------------
# Ensure collection exists (non-destructive)
# ---------------------------------------------------------------------------

def ensure_collection_exists(
    client: QdrantClient,
    collection_name: str,
    force_reindex: bool = False,
) -> None:
    """Create a Qdrant collection only if it does not already exist.

    When *force_reindex* is ``True`` the collection is **recreated**,
    which deletes all existing data.  Otherwise the function is a no-op
    when the collection is already present.

    Args:
        client: Active Qdrant client.
        collection_name: Desired collection name.
        force_reindex: If ``True``, drop and recreate.
    """
    config = get_collection_config()
    vectors = VectorParams(
        size=config["vectors_config"]["size"],
        distance=Distance.COSINE,
    )

    if force_reindex:
        client.recreate_collection(
            collection_name=collection_name,
            vectors_config=vectors,
        )
        print(f"Force-recreated collection: {collection_name}")
    else:
        try:
            client.get_collection(collection_name=collection_name)
            print(f"Using existing collection: {collection_name}")
        except Exception:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=vectors,
            )
            print(f"Created new collection: {collection_name}")


def ingest_documents(
    json_path: str,
    collection_name: str = COLLECTION_NAME,
    qdrant_url: str | None = None,
    qdrant_api_key: str | None = None,
    batch_size: int = 100,
    source: str = "manual",
    force_reindex: bool = False,
) -> dict[str, Any]:
    """
    Main ingestion pipeline with incremental deduplication.
    
    1. Load documents from JSON
    2. Create chunks with metadata
    3. Ensure collection exists (non-destructive unless force_reindex)
    4. Deduplicate against existing data
    5. Generate embeddings using HuggingFace (batched with progress)
    6. Upsert new chunks to Qdrant collection
    
    Args:
        json_path: Path to JSON file with legal documents.
        collection_name: Qdrant collection name.
        qdrant_url: Qdrant server URL (defaults to env var or localhost).
        qdrant_api_key: API key for Qdrant Cloud (optional).
        batch_size: Number of texts to embed per batch (default 100).
        source: Data provenance identifier (``"manual"``,
            ``"huggingface_azzindani"``, ``"otf_peraturan"``).
        force_reindex: When ``True``, recreate the collection from
            scratch (deletes all existing data).
    
    Returns:
        Status dict with ingestion and deduplication results.
    """
    # Get config from environment
    qdrant_url = qdrant_url or os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = qdrant_api_key or os.getenv("QDRANT_API_KEY")
    
    # Initialize clients (with API key for Qdrant Cloud)
    if qdrant_api_key:
        client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    else:
        client = QdrantClient(url=qdrant_url)
    
    if USE_JINA_EMBEDDINGS:
        # Jina takes highest precedence — lazy import to avoid side effects
        import importlib

        mod = importlib.import_module("backend.retriever")
        JinaEmbedder = getattr(mod, "JinaEmbedder")

        embedder = JinaEmbedder()
        print(f"Using Jina embeddings: {JINA_EMBEDDING_MODEL} ({JINA_EMBEDDING_DIM}d) [precedence: Jina > NVIDIA > HuggingFace]")
    elif USE_NVIDIA_EMBEDDINGS:
        # Lazy import to avoid side effects when NVIDIA embeddings are not used
        import importlib

        mod = importlib.import_module("backend.retriever")
        NVIDIAEmbedder = getattr(mod, "NVIDIAEmbedder")

        embedder = NVIDIAEmbedder()
        print(f"Using NVIDIA embeddings: {NVIDIA_EMBEDDING_MODEL} ({NVIDIA_EMBEDDING_DIM}d)")
    else:
        embedder = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        print(f"Using HuggingFace embeddings: {EMBEDDING_MODEL} ({EMBEDDING_DIM}d)")
    
    # Load documents
    with open(json_path, "r", encoding="utf-8") as f:
        documents = json.load(f)
    
    print(f"Loaded {len(documents)} documents from {json_path}")
    
    # Create chunks
    chunks = create_document_chunks(documents)
    print(f"Created {len(chunks)} chunks")
    
    # Ensure collection exists (non-destructive by default)
    ensure_collection_exists(client, collection_name, force_reindex)
    
    # Deduplication: skip chunks that already exist in the collection
    if force_reindex:
        # Collection was just recreated — nothing to deduplicate against
        new_chunks = chunks
    else:
        print("Checking for existing documents (deduplication)...")
        existing_keys = get_existing_keys(client, collection_name)
        new_chunks = filter_duplicates(chunks, existing_keys)
        print(
            f"Deduplication: {len(new_chunks)} new, "
            f"{len(chunks) - len(new_chunks)} skipped (already exist)"
        )
    
    if not new_chunks:
        print("No new chunks to ingest — all documents already present.")
        return {
            "status": "success",
            "documents_loaded": len(documents),
            "chunks_created": len(chunks),
            "chunks_new": 0,
            "chunks_skipped": len(chunks),
            "collection_name": collection_name,
        }
    
    # Generate embeddings with batched progress bar
    texts = [chunk["text"] for chunk in new_chunks]
    print(f"Generating embeddings for {len(texts)} new chunks...")

    embeddings: list[list[float]] = []
    rate_limit_count = 0
    for i in tqdm(range(0, len(texts), batch_size), desc="Embedding batches"):
        batch = texts[i : i + batch_size]
        try:
            batch_embeddings = embedder.embed_documents(batch)
            embeddings.extend(batch_embeddings)
        except Exception as e:
            if "rate limit" in str(e).lower() or "429" in str(e):
                rate_limit_count += 1
                print(f"\n[RATE LIMIT] Batch {i // batch_size}: {e}")
                print(f"Waiting 60s before retry (rate limit encounters: {rate_limit_count})...")
                time.sleep(60)
                # Retry once more after long wait
                try:
                    batch_embeddings = embedder.embed_documents(batch)
                    embeddings.extend(batch_embeddings)
                except Exception as e2:
                    print(f"[FATAL] Batch {i // batch_size} failed after extra retry: {e2}")
                    print(f"Progress: {len(embeddings)}/{len(texts)} embeddings generated")
                    raise
            else:
                raise
        # Inter-batch delay to stay under rate limits
        if i + batch_size < len(texts):
            time.sleep(3)

    print(f"Generated {len(embeddings)} embeddings")
    
    # Determine starting point ID (avoid collisions with existing points)
    if force_reindex:
        start_id = 0
    else:
        try:
            info = client.get_collection(collection_name=collection_name)
            start_id = info.points_count or 0
        except Exception:
            start_id = 0
    
    # Create points with source tracking
    points = [
        create_point_struct(start_id + i, chunk, embedding, source=source)
        for i, (chunk, embedding) in enumerate(zip(new_chunks, embeddings))
    ]
    
    # Upsert to Qdrant in batches
    for i in tqdm(range(0, len(points), batch_size), desc="Upserting batches"):
        batch = points[i : i + batch_size]
        client.upsert(
            collection_name=collection_name,
            points=batch,
            wait=True,
        )
    print(f"Upserted {len(points)} points to Qdrant")
    
    return {
        "status": "success",
        "documents_loaded": len(documents),
        "chunks_created": len(chunks),
        "chunks_new": len(new_chunks),
        "chunks_skipped": len(chunks) - len(new_chunks),
        "collection_name": collection_name,
    }


def main():
    """CLI entry point for ingestion."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Ingest legal documents to Qdrant (incremental with deduplication)"
    )
    parser.add_argument(
        "--json-path",
        default="data/peraturan/regulations.json",
        help="Path to JSON file with documents"
    )
    parser.add_argument(
        "--collection",
        default=COLLECTION_NAME,
        help="Qdrant collection name"
    )
    parser.add_argument(
        "--qdrant-url",
        default=os.getenv("QDRANT_URL", "http://localhost:6333"),
        help="Qdrant server URL"
    )
    parser.add_argument(
        "--source",
        default="manual",
        help="Data source identifier (manual, huggingface_azzindani, otf_peraturan)"
    )
    parser.add_argument(
        "--force-reindex",
        action="store_true",
        help="Force recreation of collection (WARNING: deletes all existing data)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of texts to embed per batch (default: 100)"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt (auto-confirm destructive operations)"
    )
    
    args = parser.parse_args()
    
    # Safety confirmation for destructive operation
    if args.force_reindex and not args.yes:
        print("\n[WARNING] --force-reindex will DELETE ALL existing data!")
        print("Are you sure? Type 'yes' to continue: ", end="")
        response = input().strip().lower()
        if response != "yes":
            print("Aborting.")
            sys.exit(0)
    
    # Note: HuggingFace embeddings run locally, no API key needed for embeddings
    # NVIDIA_API_KEY is still used for the LLM (Llama 3.1) in later stages
    
    result = ingest_documents(
        json_path=args.json_path,
        collection_name=args.collection,
        qdrant_url=args.qdrant_url,
        batch_size=args.batch_size,
        source=args.source,
        force_reindex=args.force_reindex,
    )
    
    print("\n=== Ingestion Complete ===")
    print(f"Status: {result['status']}")
    print(f"Documents Loaded: {result['documents_loaded']}")
    print(f"Chunks Created: {result['chunks_created']}")
    print(f"Chunks New: {result['chunks_new']}")
    print(f"Chunks Skipped (duplicates): {result['chunks_skipped']}")
    print(f"Collection: {result['collection_name']}")


if __name__ == "__main__":
    main()
