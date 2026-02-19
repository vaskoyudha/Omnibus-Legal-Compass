"""
Markdown ingestion pipeline for Indonesian legal documents.

Scans a directory of markdown legal docs (from the indonesian-legal-docs
repository), parses each file through :class:`MarkdownParser`, extracts
cross-references and amendments, chunks content using structure-aware
splitting, deduplicates by content hash and composite key, embeds with
Jina v3 (HuggingFace fallback), and upserts to Qdrant with UUID point IDs.

Also creates knowledge graph edges for cross-references and amendments,
supports bulk HNSW optimization (m=0 trick), and has checkpoint/resume
capability for interrupted loads.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    HnswConfigDiff,
    OptimizersConfigDiff,
    PointStruct,
)

from backend.scripts.markdown_parser import (
    FormatPattern,
    MarkdownParser,
    ParsedRegulation,
    compute_content_hash,
)
from backend.cross_reference import extract_legal_references, LegalReference
from backend.amendment_detector import (
    AmendmentDetector,
    AmendmentRelation,
    AmendmentType,
)
from backend.knowledge_graph.graph import LegalKnowledgeGraph
from backend.knowledge_graph.schema import EdgeType

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

MIN_CHUNK_SIZE = 50
MAX_CHUNK_SIZE = 2000

# Regex patterns for penjelasan (explanation) section detection
_PENJELASAN_PATTERNS = [
    re.compile(r"PENJELASAN\s+ATAS", re.IGNORECASE),
    re.compile(r"^PENJELASAN$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"[Pp]enjelasan\s+[Pp]asal", re.IGNORECASE),
    re.compile(r"[Pp]enjelasan\s+[Uu]mum", re.IGNORECASE),
]

# ── Structure-aware chunking patterns ────────────────────────────────────────
# Legal hierarchy: BAB (chapter) → Pasal (article) → Ayat (verse/paragraph)

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
    r"(?:^|\n)\s*Bagian\s+(?:Kesatu|Kedua|Ketiga|Keempat|Kelima|Keenam"
    r"|Ketujuh|Kedelapan|Kesembilan|Kesepuluh)\b",
    re.IGNORECASE,
)
_PARAGRAF_BOUNDARY = re.compile(
    r"(?:^|\n)\s*Paragraf\s+\d+",
    re.IGNORECASE,
)

# Amendment type → knowledge graph edge type mapping
_AMENDMENT_EDGE_MAP: dict[AmendmentType, EdgeType] = {
    AmendmentType.AMENDS: EdgeType.AMENDS,
    AmendmentType.REVOKES: EdgeType.REVOKES,
    AmendmentType.REPLACES: EdgeType.REPLACES,
    AmendmentType.SUPPLEMENTS: EdgeType.REFERENCES,
}


# ── Helper Functions ─────────────────────────────────────────────────────────


def _split_by_legal_boundaries(text: str) -> list[str]:
    """Split a raw text block along BAB / Pasal / Ayat structural boundaries.

    Scans *text* for structural markers and splits at those positions so
    each resulting segment starts at a boundary marker.  If no boundaries
    are found, the original text is returned as a single-element list.
    """
    boundaries: list[int] = []
    for pattern in (
        _BAB_BOUNDARY,
        _PASAL_BOUNDARY,
        _BAGIAN_BOUNDARY,
        _PARAGRAF_BOUNDARY,
        _AYAT_BOUNDARY,
    ):
        for m in pattern.finditer(text):
            pos = m.start()
            while pos < len(text) and text[pos] in ("\n", "\r", " "):
                if text[pos] not in ("\n", "\r"):
                    break
                pos += 1
            boundaries.append(pos)

    if not boundaries:
        return [text]

    boundaries = sorted(set(boundaries))

    segments: list[str] = []
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


def _chunk_sentence(text: str, chunk_size: int = MAX_CHUNK_SIZE) -> list[str]:
    """Split oversized text by sentence boundaries."""
    if len(text) <= chunk_size:
        return [text]

    sentences = re.split(r"(?<=[.;])\s+|\n+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return [text]

    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        candidate = (current + " " + sentence).strip() if current else sentence
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = sentence

    if current:
        chunks.append(current)

    return chunks


def _detect_penjelasan(text: str, bab: str = "") -> bool:
    """Return True if text or bab indicates a penjelasan (explanation) section."""
    if bab and re.search(r"penjelasan", bab, re.IGNORECASE):
        return True
    for pattern in _PENJELASAN_PATTERNS:
        if pattern.search(text):
            return True
    return False


def _generate_citation_id(
    jenis: str,
    nomor: str,
    tahun: str,
    pasal: str = "",
    ayat: str = "",
    bab: str = "",
) -> str:
    """Generate unique citation ID matching the existing ingest.py format.

    Format: ``{jenis}_{nomor}_{tahun}_Pasal{N}[_Ayat{N}]``
    Example: ``UU_11_2020_Pasal5_Ayat1``
    """
    parts = [jenis, nomor, tahun]
    if pasal:
        parts.append(f"Pasal{pasal}")
    if ayat:
        parts.append(f"Ayat{ayat}")
    if bab and not pasal:
        parts.append(f"Bab{bab}")
    return "_".join(parts)


def _build_parent_context(
    jenis: str,
    nomor: str,
    tahun: str,
    judul: str,
    bab: str = "",
    pasal: str = "",
    ayat: str = "",
) -> str:
    """Build hierarchical breadcrumb path for a legal document chunk."""
    ctx = f"{jenis} No. {nomor} Tahun {tahun}"
    if judul:
        ctx += f" tentang {judul}"
    if bab:
        ctx += f" > {bab}"
    if pasal:
        ctx += f" > Pasal {pasal}"
    if ayat:
        ctx += f" > Ayat ({ayat})"
    return ctx


def _extract_pasal_ayat(segment: str) -> tuple[str, str]:
    """Extract leading Pasal and Ayat numbers from a text segment."""
    pasal = ""
    ayat = ""
    m = re.match(r"^\s*Pasal\s+(\d+[A-Z]?)\b", segment)
    if m:
        pasal = m.group(1)
    m = re.match(r"^\s*\((\d+)\)", segment)
    if m:
        ayat = m.group(1)
    return pasal, ayat


def _extract_bab(segment: str) -> str:
    """Extract leading BAB roman numeral from a text segment."""
    m = re.match(r"^\s*BAB\s+([IVXLCDM]+)", segment, re.IGNORECASE)
    return m.group(1) if m else ""


# ── Data Classes ─────────────────────────────────────────────────────────────


@dataclass
class ChunkData:
    """Represents a single chunk ready for embedding and Qdrant upsert."""

    text: str
    citation_id: str
    citation: str
    jenis_dokumen: str
    nomor: str
    tahun: str
    judul: str
    tentang: str
    bab: str = ""
    pasal: str = ""
    ayat: str = ""
    parent_context: str = ""
    full_path: str = ""
    parent_bab: str = ""
    parent_pasal: str = ""
    parent_ayat: str = ""
    is_penjelasan: bool = False
    source: str = "markdown_repo"
    format_pattern: str = ""
    has_full_text: bool = True
    quality_flag: str | None = None
    content_hash: str = ""
    filepath: str = ""

    def to_payload(self) -> dict[str, Any]:
        """Return payload dict matching the existing ingest.py schema."""
        return {
            "text": self.text,
            "citation_id": self.citation_id,
            "citation": self.citation,
            "jenis_dokumen": self.jenis_dokumen,
            "nomor": self.nomor,
            "tahun": self.tahun,
            "judul": self.judul,
            "tentang": self.tentang,
            "bab": self.bab,
            "pasal": self.pasal,
            "ayat": self.ayat,
            "parent_context": self.parent_context,
            "full_path": self.full_path,
            "parent_bab": self.parent_bab,
            "parent_pasal": self.parent_pasal,
            "parent_ayat": self.parent_ayat,
            "is_penjelasan": self.is_penjelasan,
            "source": self.source,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "format_pattern": self.format_pattern,
            "has_full_text": self.has_full_text,
            "quality_flag": self.quality_flag,
            "content_hash": self.content_hash,
            "filepath": self.filepath,
        }


@dataclass
class IngestionStats:
    """Counters for an ingestion run."""

    total_files: int = 0
    parsed: int = 0
    skipped: int = 0
    chunks_created: int = 0
    duplicates_skipped: int = 0
    uploaded: int = 0
    graph_edges: int = 0
    errors: int = 0

    def summary(self) -> str:
        """Return formatted summary string."""
        return (
            f"Ingestion complete: {self.total_files} files scanned, "
            f"{self.parsed} parsed, {self.skipped} skipped, "
            f"{self.chunks_created} chunks created, "
            f"{self.duplicates_skipped} duplicates skipped, "
            f"{self.uploaded} uploaded, "
            f"{self.graph_edges} graph edges, "
            f"{self.errors} errors"
        )


# ── ContentDeduplicator ─────────────────────────────────────────────────────


class ContentDeduplicator:
    """Hash-based deduplication by content hash and composite key."""

    def __init__(self) -> None:
        self.seen_hashes: set[str] = set()
        self.seen_keys: set[tuple[str, str, str, str, str]] = set()

    def is_duplicate(
        self,
        content_hash: str,
        jenis: str,
        nomor: str,
        tahun: str,
        pasal: str,
        ayat: str,
    ) -> tuple[bool, str]:
        """Check if a chunk is a duplicate.

        Returns ``(is_dup, reason)`` where *reason* is a human-readable
        string explaining why the chunk was considered duplicate.
        """
        if content_hash and content_hash in self.seen_hashes:
            return True, "content_hash"
        composite_key = (jenis, str(nomor), str(tahun), str(pasal), str(ayat))
        if composite_key in self.seen_keys:
            return True, "composite_key"
        # Not a duplicate — register it
        if content_hash:
            self.seen_hashes.add(content_hash)
        self.seen_keys.add(composite_key)
        return False, ""

    def add_existing_keys(self, keys: set[tuple[str, str, str, str, str]]) -> None:
        """Pre-populate from Qdrant existing composite keys."""
        self.seen_keys.update(keys)


# ── IngestionCheckpointer ───────────────────────────────────────────────────


class IngestionCheckpointer:
    """Resume interrupted loads via a JSON checkpoint file."""

    def __init__(self, checkpoint_file: Path) -> None:
        self.checkpoint_file = checkpoint_file

    def save(self, last_file: str, stats: dict[str, Any]) -> None:
        """Write checkpoint to disk."""
        payload = {
            "last_file": last_file,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stats": stats,
        }
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        self.checkpoint_file.write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

    def load(self) -> dict[str, Any] | None:
        """Read checkpoint, return ``None`` if not exists."""
        if not self.checkpoint_file.exists():
            return None
        try:
            return json.loads(
                self.checkpoint_file.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError):
            logger.warning("Corrupt checkpoint file — starting fresh")
            return None

    def clear(self) -> None:
        """Delete checkpoint file."""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()


# ── Main Pipeline ────────────────────────────────────────────────────────────


class MarkdownIngestionPipeline:
    """Ingest markdown legal documents into Qdrant with knowledge graph edges.

    Full pipeline: scan → parse → chunk → dedup → embed → upsert → graph.
    """

    def __init__(
        self,
        qdrant_url: str,
        collection_name: str,
        jina_api_key: str | None = None,
        repo_dir: Path | None = None,
    ) -> None:
        self.qdrant_client = QdrantClient(url=qdrant_url)
        self.collection_name = collection_name
        self.jina_api_key = jina_api_key
        self.repo_dir = repo_dir

        self.parser = MarkdownParser()
        self.amendment_detector = AmendmentDetector()
        self.kg = LegalKnowledgeGraph()
        self.dedup = ContentDeduplicator()
        self.stats = IngestionStats()

        # Lazy-initialized embedder (see _get_embedder)
        self._embedder: Any = None

    # ── Public API ───────────────────────────────────────────────────────

    def run(
        self,
        data_dir: Path,
        batch_size: int = 100,
        optimize_bulk: bool = True,
        checkpoint_file: Path | None = None,
    ) -> IngestionStats:
        """Execute the full ingestion pipeline.

        1. Scan all ``.md`` files in *data_dir* recursively.
        2. Load checkpoint if exists, skip already-processed files.
        3. Fetch existing composite keys from Qdrant for dedup.
        4. If *optimize_bulk*: disable HNSW indexing (m=0 trick).
        5. For each file: parse → skip BINARY/README → chunk → dedup → collect.
        6. Embed and upsert in batches.
        7. If *optimize_bulk*: re-enable HNSW indexing.
        8. Save checkpoint after each batch.
        9. Log stats summary.
        """
        checkpointer = (
            IngestionCheckpointer(checkpoint_file) if checkpoint_file else None
        )
        skip_until: str | None = None
        if checkpointer:
            cp = checkpointer.load()
            if cp:
                skip_until = cp.get("last_file")
                logger.info("Resuming from checkpoint after: %s", skip_until)

        # 1. Scan markdown files
        md_files = sorted(data_dir.rglob("*.md"))
        self.stats.total_files = len(md_files)
        logger.info("Found %d .md files in %s", len(md_files), data_dir)

        # 2. Skip already-processed files from checkpoint
        if skip_until:
            idx = None
            for i, f in enumerate(md_files):
                if str(f) == skip_until:
                    idx = i
                    break
            if idx is not None:
                md_files = md_files[idx + 1 :]
                logger.info("Skipping %d files (checkpoint)", idx + 1)

        # 3. Fetch existing keys from Qdrant for dedup
        existing_keys = self._fetch_existing_keys()
        self.dedup.add_existing_keys(existing_keys)
        logger.info(
            "Loaded %d existing composite keys for deduplication",
            len(existing_keys),
        )

        # 4. Disable HNSW indexing for bulk load
        if optimize_bulk:
            self._disable_indexing()
            logger.info("Disabled HNSW indexing for bulk load (m=0)")

        # 5. Process each file → accumulate chunks
        all_chunks: list[ChunkData] = []
        try:
            for filepath in md_files:
                try:
                    chunks = self.process_single_file(filepath)
                    # Dedup each chunk
                    for chunk in chunks:
                        is_dup, reason = self.dedup.is_duplicate(
                            chunk.content_hash,
                            chunk.jenis_dokumen,
                            chunk.nomor,
                            chunk.tahun,
                            chunk.pasal,
                            chunk.ayat,
                        )
                        if is_dup:
                            self.stats.duplicates_skipped += 1
                            logger.debug(
                                "Duplicate skipped (%s): %s",
                                reason,
                                chunk.citation_id,
                            )
                            continue
                        all_chunks.append(chunk)
                        self.stats.chunks_created += 1

                    # 6. Embed and upsert when batch is full
                    if len(all_chunks) >= batch_size:
                        self._embed_and_upsert(all_chunks, batch_size)
                        all_chunks.clear()
                        # 8. Save checkpoint
                        if checkpointer:
                            checkpointer.save(
                                str(filepath),
                                {
                                    "uploaded": self.stats.uploaded,
                                    "chunks_created": self.stats.chunks_created,
                                },
                            )

                except Exception:
                    self.stats.errors += 1
                    logger.exception("Error processing %s", filepath)

            # Flush remaining chunks
            if all_chunks:
                self._embed_and_upsert(all_chunks, batch_size)

        finally:
            # 7. Re-enable HNSW indexing
            if optimize_bulk:
                self._enable_indexing()
                logger.info("Re-enabled HNSW indexing (m=16, ef_construct=100)")

        # 9. Clear checkpoint and log summary
        if checkpointer:
            checkpointer.clear()
        logger.info(self.stats.summary())
        return self.stats

    def process_single_file(self, filepath: Path) -> list[ChunkData]:
        """Process one markdown file into a list of chunks.

        Also used by ``incremental_sync.py`` for single-file updates.

        Steps:
        1. Parse with :class:`MarkdownParser`
        2. Skip BINARY/README (return empty)
        3. Extract cross-refs from content
        4. Detect amendments from content and title
        5. Create knowledge graph edges
        6. Chunk the content
        7. Return list of :class:`ChunkData`
        """
        parsed = self.parser.parse(filepath)

        # Skip non-content patterns
        if parsed.format_pattern in (FormatPattern.BINARY, FormatPattern.README):
            self.stats.skipped += 1
            return []

        self.stats.parsed += 1

        # Extract cross-references
        refs = extract_legal_references(parsed.content)

        # Detect amendments from both content and title
        amendments = self.amendment_detector.detect_amendments(
            parsed.content, parsed.regulation_id
        )
        amendments.extend(
            self.amendment_detector.detect_from_title(
                parsed.judul, parsed.regulation_id
            )
        )

        # Store knowledge graph edges
        self._store_graph_edges(parsed.regulation_id, refs, amendments)

        # Chunk the content
        return self._chunk_regulation(parsed)

    # ── Chunking ─────────────────────────────────────────────────────────

    def _chunk_regulation(self, parsed: ParsedRegulation) -> list[ChunkData]:
        """Structure-aware chunking of a parsed regulation."""
        jenis = parsed.jenis_dokumen
        nomor = parsed.nomor
        tahun = parsed.tahun
        judul = parsed.judul
        fp_val = parsed.format_pattern.value
        fpath = parsed.filepath

        # Pattern D (CATALOG): metadata-only chunk
        if parsed.format_pattern == FormatPattern.CATALOG:
            ctx = _build_parent_context(jenis, nomor, tahun, judul)
            cid = _generate_citation_id(jenis, nomor, tahun)
            return [
                ChunkData(
                    text=judul or f"Catalog: {parsed.regulation_id}",
                    citation_id=cid,
                    citation=f"{jenis} No. {nomor} Tahun {tahun}",
                    jenis_dokumen=jenis,
                    nomor=nomor,
                    tahun=tahun,
                    judul=judul,
                    tentang=judul,
                    parent_context=ctx,
                    full_path=ctx,
                    has_full_text=False,
                    content_hash=parsed.content_hash,
                    source="markdown_repo",
                    format_pattern=fp_val,
                    filepath=fpath,
                )
            ]

        # Pattern C (OCR): chunk normally but flag quality
        quality_flag = "ocr" if parsed.format_pattern == FormatPattern.OCR_CONVERTED else None

        # Patterns A, B, C: structure-aware chunking
        content = parsed.content
        if not content or len(content.strip()) < MIN_CHUNK_SIZE:
            return []

        # Split along legal boundaries first
        structural_segments = _split_by_legal_boundaries(content)

        # Track current BAB / Pasal context as we walk through segments
        current_bab = ""
        current_pasal = ""
        chunks: list[ChunkData] = []

        for segment in structural_segments:
            if len(segment.strip()) < MIN_CHUNK_SIZE:
                continue

            # Detect BAB header to update context
            bab_label = _extract_bab(segment)
            if bab_label:
                current_bab = bab_label

            # Detect Pasal/Ayat from segment start
            seg_pasal, seg_ayat = _extract_pasal_ayat(segment)
            if seg_pasal:
                current_pasal = seg_pasal

            pasal = seg_pasal or current_pasal
            ayat = seg_ayat

            # Sub-split oversized segments by sentence boundaries
            if len(segment) > MAX_CHUNK_SIZE:
                pieces = _chunk_sentence(segment, MAX_CHUNK_SIZE)
            else:
                pieces = [segment]

            for piece_idx, piece in enumerate(pieces):
                if len(piece.strip()) < MIN_CHUNK_SIZE:
                    continue

                suffix = f"_chunk{piece_idx + 1}" if len(pieces) > 1 else ""

                cid = _generate_citation_id(
                    jenis, nomor, tahun, pasal, ayat, current_bab
                )
                if suffix:
                    cid += suffix

                ctx = _build_parent_context(
                    jenis, nomor, tahun, judul, current_bab, pasal, ayat
                )

                # Human-readable citation
                citation = f"{jenis} No. {nomor} Tahun {tahun}"
                if judul:
                    citation += f" tentang {judul}"
                if pasal:
                    citation += f", Pasal {pasal}"
                if ayat:
                    citation += f" Ayat ({ayat})"
                if suffix:
                    citation += f" (bagian {piece_idx + 1})"

                is_penjelasan = _detect_penjelasan(piece, current_bab)
                piece_hash = compute_content_hash(piece)

                chunks.append(
                    ChunkData(
                        text=piece,
                        citation_id=cid,
                        citation=citation,
                        jenis_dokumen=jenis,
                        nomor=nomor,
                        tahun=tahun,
                        judul=judul,
                        tentang=judul,
                        bab=current_bab,
                        pasal=pasal,
                        ayat=ayat,
                        parent_context=ctx,
                        full_path=ctx,
                        parent_bab=current_bab,
                        parent_pasal=pasal,
                        parent_ayat=ayat,
                        is_penjelasan=is_penjelasan,
                        has_full_text=True,
                        quality_flag=quality_flag,
                        content_hash=piece_hash,
                        source="markdown_repo",
                        format_pattern=fp_val,
                        filepath=fpath,
                    )
                )

        return chunks

    # ── Embedding & Upsert ───────────────────────────────────────────────

    def _embed_and_upsert(self, chunks: list[ChunkData], batch_size: int) -> None:
        """Embed chunk texts and upsert to Qdrant in batches."""
        embedder = self._get_embedder()
        texts = [c.text for c in chunks]

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_chunks = chunks[i : i + batch_size]

            try:
                embeddings = embedder.embed_documents(batch_texts)
            except Exception as exc:
                # Retry once after a pause for rate-limit errors
                if "429" in str(exc) or "rate limit" in str(exc).lower():
                    logger.warning("Rate limit hit — waiting 60s then retrying")
                    time.sleep(60)
                    embeddings = embedder.embed_documents(batch_texts)
                else:
                    raise

            points = [
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=emb,
                    payload=chunk.to_payload(),
                )
                for chunk, emb in zip(batch_chunks, embeddings)
            ]

            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=False,
            )
            self.stats.uploaded += len(points)
            logger.info(
                "Upserted batch of %d points (total: %d)",
                len(points),
                self.stats.uploaded,
            )

            # Small delay between batches to ease rate-limit pressure
            if i + batch_size < len(texts):
                time.sleep(1)

    def _get_embedder(self) -> Any:
        """Lazy-initialize the embedder (Jina v3 preferred, HuggingFace fallback)."""
        if self._embedder is not None:
            return self._embedder

        # Try Jina first
        api_key = self.jina_api_key or os.getenv("JINA_API_KEY")
        if api_key:
            try:
                from backend.retriever import JinaEmbedder

                self._embedder = JinaEmbedder(api_key=api_key)
                logger.info("Using Jina v3 embedder")
                return self._embedder
            except Exception:
                logger.warning("Jina embedder init failed — falling back to HuggingFace")

        # HuggingFace fallback
        from langchain_huggingface import HuggingFaceEmbeddings

        self._embedder = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        logger.info("Using HuggingFace embedder (paraphrase-multilingual-MiniLM-L12-v2)")
        return self._embedder

    # ── HNSW Optimization ────────────────────────────────────────────────

    def _disable_indexing(self) -> None:
        """Disable HNSW indexing during bulk load (m=0 trick)."""
        self.qdrant_client.update_collection(
            collection_name=self.collection_name,
            hnsw_config=HnswConfigDiff(m=0),
            optimizer_config=OptimizersConfigDiff(indexing_threshold=0),
        )

    def _enable_indexing(self) -> None:
        """Restore HNSW indexing after bulk load."""
        self.qdrant_client.update_collection(
            collection_name=self.collection_name,
            hnsw_config=HnswConfigDiff(m=16, ef_construct=100),
            optimizer_config=OptimizersConfigDiff(indexing_threshold=20000),
        )

    # ── Knowledge Graph Edges ────────────────────────────────────────────

    def _store_graph_edges(
        self,
        regulation_id: str,
        refs: list[LegalReference],
        amendments: list[AmendmentRelation],
    ) -> None:
        """Create knowledge graph edges for cross-references and amendments."""
        for ref in refs:
            self.kg.add_edge(
                regulation_id,
                ref.canonical,
                EdgeType.REFERENCES,
                metadata={"raw_text": ref.raw_text, "relation": ref.relation},
            )
            self.stats.graph_edges += 1

        for amendment in amendments:
            edge_type = _AMENDMENT_EDGE_MAP.get(
                amendment.amendment_type, EdgeType.REFERENCES
            )
            self.kg.add_edge(
                amendment.source_regulation,
                amendment.target_regulation,
                edge_type,
                metadata={
                    "raw_text": amendment.raw_text,
                    "confidence": amendment.confidence,
                },
            )
            self.stats.graph_edges += 1

    # ── Fetch Existing Keys ──────────────────────────────────────────────

    def _fetch_existing_keys(self) -> set[tuple[str, str, str, str, str]]:
        """Scroll through Qdrant and build a set of existing composite keys."""
        existing_keys: set[tuple[str, str, str, str, str]] = set()

        try:
            scroll_response = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                limit=10000,
                with_payload=True,
                with_vectors=False,
            )
        except Exception:
            logger.warning(
                "Could not fetch existing keys from Qdrant (collection may not exist)"
            )
            return existing_keys

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

            scroll_response = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                limit=10000,
                offset=next_offset,
                with_payload=True,
                with_vectors=False,
            )
            points, next_offset = scroll_response

        return existing_keys


# ── CLI Entry Point ──────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point for markdown ingestion pipeline."""
    parser = argparse.ArgumentParser(
        description="Ingest markdown legal documents into Qdrant"
    )
    parser.add_argument(
        "--data-dir",
        default="indonesian-legal-docs",
        help="Path to markdown docs directory (default: indonesian-legal-docs)",
    )
    parser.add_argument(
        "--qdrant-url",
        default=os.getenv("QDRANT_URL", "http://localhost:6333"),
        help="Qdrant server URL",
    )
    parser.add_argument(
        "--collection-name",
        default="indonesian_legal_docs",
        help="Qdrant collection name",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Embedding/upsert batch size (default: 100)",
    )
    parser.add_argument(
        "--no-bulk-optimize",
        action="store_true",
        help="Disable HNSW m=0 bulk optimization trick",
    )
    parser.add_argument(
        "--checkpoint-file",
        default=None,
        help="Checkpoint file path for resume capability",
    )
    parser.add_argument(
        "--jina-api-key",
        default=os.getenv("JINA_API_KEY"),
        help="Jina API key (default: JINA_API_KEY env var)",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    pipeline = MarkdownIngestionPipeline(
        qdrant_url=args.qdrant_url,
        collection_name=args.collection_name,
        jina_api_key=args.jina_api_key,
    )

    checkpoint_path = Path(args.checkpoint_file) if args.checkpoint_file else None

    stats = pipeline.run(
        data_dir=Path(args.data_dir),
        batch_size=args.batch_size,
        optimize_bulk=not args.no_bulk_optimize,
        checkpoint_file=checkpoint_path,
    )

    print(f"\n{'=' * 60}")
    print(stats.summary())
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
