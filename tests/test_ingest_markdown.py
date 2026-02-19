"""
Tests for markdown ingestion pipeline.

Covers ChunkData payload generation, ContentDeduplicator, IngestionCheckpointer,
structure-aware chunking, citation ID generation, pipeline orchestration with
mock Qdrant and mock embedder.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.scripts.ingest_markdown import (
    ChunkData,
    ContentDeduplicator,
    IngestionCheckpointer,
    MarkdownIngestionPipeline,
    _build_parent_context,
    _generate_citation_id,
)
from backend.scripts.markdown_parser import FormatPattern, ParsedRegulation


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_parsed_regulation(**overrides) -> ParsedRegulation:
    """Build a ParsedRegulation with sensible defaults for testing."""
    defaults = {
        "filepath": "test/law.md",
        "format_pattern": FormatPattern.STRUCTURED,
        "regulation_id": "UU_11_2020",
        "jenis_dokumen": "UU",
        "nomor": "11",
        "tahun": "2020",
        "judul": "Cipta Kerja",
        "content": (
            "Pasal 1\n"
            "Ketentuan umum dalam undang-undang ini yang dimaksud dengan "
            "Cipta Kerja adalah upaya penciptaan kerja.\n\n"
            "Pasal 2\n"
            "Pemerintah Pusat dan Pemerintah Daerah menyelenggarakan "
            "kebijakan Cipta Kerja."
        ),
        "chapters": [],
        "articles": [],
        "legal_basis": [],
        "keywords": [],
        "has_full_text": True,
        "quality_flag": None,
        "content_hash": "abc123hash",
        "yaml_metadata": {},
        "ministry": "",
        "effective_date": "",
        "source": "markdown_repo",
    }
    defaults.update(overrides)
    return ParsedRegulation(**defaults)


# ── ChunkData payload ───────────────────────────────────────────────────────


def test_chunk_data_to_payload():
    """ChunkData.to_payload() includes all 24 fields with correct types."""
    chunk = ChunkData(
        text="Pasal 1 tentang ketentuan umum.",
        citation_id="UU_11_2020_Pasal1",
        citation="UU No. 11 Tahun 2020 tentang Cipta Kerja, Pasal 1",
        jenis_dokumen="UU",
        nomor="11",
        tahun="2020",
        judul="Cipta Kerja",
        tentang="Cipta Kerja",
        bab="I",
        pasal="1",
        ayat="",
        parent_context="UU No. 11 Tahun 2020 tentang Cipta Kerja > I > Pasal 1",
        full_path="UU No. 11 Tahun 2020 tentang Cipta Kerja > I > Pasal 1",
        parent_bab="I",
        parent_pasal="1",
        parent_ayat="",
        is_penjelasan=False,
        source="markdown_repo",
        format_pattern="A",
        has_full_text=True,
        quality_flag=None,
        content_hash="hash123",
        filepath="test/law.md",
    )

    payload = chunk.to_payload()

    # All 24 keys must be present
    expected_keys = {
        "text", "citation_id", "citation", "jenis_dokumen", "nomor",
        "tahun", "judul", "tentang", "bab", "pasal", "ayat",
        "parent_context", "full_path", "parent_bab", "parent_pasal",
        "parent_ayat", "is_penjelasan", "source", "ingested_at",
        "format_pattern", "has_full_text", "quality_flag",
        "content_hash", "filepath",
    }
    assert set(payload.keys()) == expected_keys
    assert len(payload) == 24

    # Type checks
    assert isinstance(payload["text"], str)
    assert isinstance(payload["is_penjelasan"], bool)
    assert isinstance(payload["has_full_text"], bool)
    assert payload["source"] == "markdown_repo"

    # ingested_at must be valid ISO format
    parsed_dt = datetime.fromisoformat(payload["ingested_at"])
    assert parsed_dt.year >= 2020


# ── Citation ID generation ───────────────────────────────────────────────────


def test_generate_citation_id_pasal_ayat():
    """Citation ID with pasal and ayat produces Pasal/Ayat suffixes."""
    cid = _generate_citation_id("UU", "11", "2020", pasal="5", ayat="1")
    assert cid == "UU_11_2020_Pasal5_Ayat1"


def test_generate_citation_id_bab_only():
    """Citation ID with bab (no pasal) produces Bab suffix."""
    cid = _generate_citation_id("UU", "11", "2020", bab="II")
    assert cid == "UU_11_2020_BabII"


def test_generate_citation_id_basic():
    """Citation ID with just jenis/nomor/tahun — no structural suffix."""
    cid = _generate_citation_id("UU", "11", "2020")
    assert cid == "UU_11_2020"


# ── Parent context builder ───────────────────────────────────────────────────


def test_build_parent_context():
    """_build_parent_context produces full breadcrumb path."""
    ctx = _build_parent_context(
        jenis="UU",
        nomor="11",
        tahun="2020",
        judul="Cipta Kerja",
        bab="BAB II",
        pasal="5",
        ayat="1",
    )
    assert ctx == (
        "UU No. 11 Tahun 2020 tentang Cipta Kerja > BAB II > Pasal 5 > Ayat (1)"
    )


# ── ContentDeduplicator ─────────────────────────────────────────────────────


def test_content_deduplicator_hash_dup():
    """Same content_hash → duplicate detected with 'content_hash' reason."""
    dedup = ContentDeduplicator()

    is_dup1, reason1 = dedup.is_duplicate("hash_a", "UU", "11", "2020", "1", "")
    assert not is_dup1
    assert reason1 == ""

    is_dup2, reason2 = dedup.is_duplicate("hash_a", "PP", "5", "2021", "2", "1")
    assert is_dup2
    assert reason2 == "content_hash"


def test_content_deduplicator_composite_key_dup():
    """Different hash, same (jenis,nomor,tahun,pasal,ayat) → 'composite_key' dup."""
    dedup = ContentDeduplicator()

    dedup.is_duplicate("hash_x", "UU", "11", "2020", "1", "")
    is_dup, reason = dedup.is_duplicate("hash_y", "UU", "11", "2020", "1", "")
    assert is_dup
    assert reason == "composite_key"


def test_content_deduplicator_no_dup():
    """Different hash AND different key → not duplicate."""
    dedup = ContentDeduplicator()

    dedup.is_duplicate("hash_1", "UU", "11", "2020", "1", "")
    is_dup, reason = dedup.is_duplicate("hash_2", "PP", "5", "2021", "3", "1")
    assert not is_dup
    assert reason == ""


def test_content_deduplicator_add_existing_keys():
    """Pre-populated existing keys are detected as duplicates."""
    dedup = ContentDeduplicator()
    existing = {("UU", "11", "2020", "1", "")}
    dedup.add_existing_keys(existing)

    is_dup, reason = dedup.is_duplicate("new_hash", "UU", "11", "2020", "1", "")
    assert is_dup
    assert reason == "composite_key"


# ── IngestionCheckpointer ───────────────────────────────────────────────────


def test_checkpointer_save_load_clear(tmp_path: Path):
    """Save checkpoint → load back → clear → None."""
    cp_file = tmp_path / "checkpoints" / "checkpoint.json"
    ckpt = IngestionCheckpointer(cp_file)

    # Save
    ckpt.save("docs/law5.md", {"uploaded": 42, "chunks_created": 100})
    assert cp_file.exists()

    # Load
    data = ckpt.load()
    assert data is not None
    assert data["last_file"] == "docs/law5.md"
    assert data["stats"]["uploaded"] == 42
    assert "timestamp" in data

    # Clear
    ckpt.clear()
    assert not cp_file.exists()
    assert ckpt.load() is None


# ── Structure-aware chunking: CATALOG ────────────────────────────────────────


@patch("backend.scripts.ingest_markdown.QdrantClient")
def test_chunk_regulation_catalog_pattern(mock_qdrant_cls):
    """FormatPattern.CATALOG → exactly 1 chunk with has_full_text=False."""
    pipeline = MarkdownIngestionPipeline(
        qdrant_url="http://localhost:6333",
        collection_name="test_col",
    )

    parsed = _make_parsed_regulation(
        format_pattern=FormatPattern.CATALOG,
        content="",
        has_full_text=False,
    )

    chunks = pipeline._chunk_regulation(parsed)

    assert len(chunks) == 1
    assert chunks[0].has_full_text is False
    assert chunks[0].source == "markdown_repo"
    assert chunks[0].format_pattern == "D"
    assert chunks[0].jenis_dokumen == "UU"


# ── Structure-aware chunking: STRUCTURED ─────────────────────────────────────


@patch("backend.scripts.ingest_markdown.QdrantClient")
def test_chunk_regulation_structured_pattern(mock_qdrant_cls):
    """STRUCTURED with Pasal boundaries → chunks split at Pasal markers."""
    pipeline = MarkdownIngestionPipeline(
        qdrant_url="http://localhost:6333",
        collection_name="test_col",
    )

    parsed = _make_parsed_regulation(
        format_pattern=FormatPattern.STRUCTURED,
        content=(
            "Pasal 1\n"
            "Ketentuan umum dalam undang-undang ini yang dimaksud dengan "
            "Cipta Kerja adalah upaya penciptaan kerja melalui usaha "
            "sebesar-besarnya.\n\n"
            "Pasal 2\n"
            "Pemerintah Pusat dan Pemerintah Daerah menyelenggarakan "
            "kebijakan Cipta Kerja secara terpadu dan komprehensif."
        ),
    )

    chunks = pipeline._chunk_regulation(parsed)

    # Should produce at least 2 chunks (one per Pasal)
    assert len(chunks) >= 2

    # First chunk should reference Pasal 1
    pasal_values = [c.pasal for c in chunks]
    assert "1" in pasal_values
    assert "2" in pasal_values

    # All chunks should have correct metadata
    for c in chunks:
        assert c.jenis_dokumen == "UU"
        assert c.nomor == "11"
        assert c.tahun == "2020"
        assert c.format_pattern == "A"


# ── OCR quality flag ─────────────────────────────────────────────────────────


@patch("backend.scripts.ingest_markdown.QdrantClient")
def test_chunk_regulation_ocr_quality_flag(mock_qdrant_cls):
    """FormatPattern.OCR_CONVERTED → quality_flag='ocr' on all chunks."""
    pipeline = MarkdownIngestionPipeline(
        qdrant_url="http://localhost:6333",
        collection_name="test_col",
    )

    parsed = _make_parsed_regulation(
        format_pattern=FormatPattern.OCR_CONVERTED,
        content=(
            "Pasal 1\n"
            "Dokumen ini dikonversi dari PDF melalui proses OCR. "
            "Ketentuan umum dalam peraturan ini mengatur tentang "
            "penyelenggaraan kegiatan usaha di wilayah Indonesia."
        ),
    )

    chunks = pipeline._chunk_regulation(parsed)

    assert len(chunks) >= 1
    for c in chunks:
        assert c.quality_flag == "ocr"


# ── Skip small content ───────────────────────────────────────────────────────


@patch("backend.scripts.ingest_markdown.QdrantClient")
def test_chunk_regulation_skips_small_content(mock_qdrant_cls):
    """Content shorter than MIN_CHUNK_SIZE (50 chars) → empty list."""
    pipeline = MarkdownIngestionPipeline(
        qdrant_url="http://localhost:6333",
        collection_name="test_col",
    )

    parsed = _make_parsed_regulation(
        format_pattern=FormatPattern.STRUCTURED,
        content="Short.",  # well below 50 chars
    )

    chunks = pipeline._chunk_regulation(parsed)
    assert chunks == []


# ── process_single_file: BINARY skipped ──────────────────────────────────────


@patch("backend.scripts.ingest_markdown.extract_legal_references", return_value=[])
@patch("backend.scripts.ingest_markdown.AmendmentDetector")
@patch("backend.scripts.ingest_markdown.QdrantClient")
def test_process_single_file_binary_skipped(
    mock_qdrant_cls, mock_amend_cls, mock_extract_refs, tmp_path: Path
):
    """BINARY format → empty list and stats.skipped incremented."""
    mock_qdrant_cls.return_value.scroll.return_value = ([], None)

    pipeline = MarkdownIngestionPipeline(
        qdrant_url="http://localhost:6333",
        collection_name="test_col",
    )

    binary_parsed = _make_parsed_regulation(
        format_pattern=FormatPattern.BINARY,
        content="",
        has_full_text=False,
    )

    with patch.object(pipeline.parser, "parse", return_value=binary_parsed):
        chunks = pipeline.process_single_file(tmp_path / "binary.md")

    assert chunks == []
    assert pipeline.stats.skipped == 1


# ── Full pipeline run with mocks ─────────────────────────────────────────────


@patch("backend.scripts.ingest_markdown.extract_legal_references", return_value=[])
@patch("backend.scripts.ingest_markdown.AmendmentDetector")
@patch("backend.scripts.ingest_markdown.QdrantClient")
def test_pipeline_run_with_mock_qdrant(
    mock_qdrant_cls, mock_amend_cls, mock_extract_refs, tmp_path: Path
):
    """Full pipeline run: scan → parse → chunk → embed → upsert."""
    # Configure mock Qdrant client
    mock_qclient = MagicMock()
    mock_qclient.scroll.return_value = ([], None)
    mock_qdrant_cls.return_value = mock_qclient

    # Create a mock markdown file in tmp_path
    data_dir = tmp_path / "docs"
    data_dir.mkdir()
    md_file = data_dir / "uu-11-2020.md"
    md_file.write_text(
        "Pasal 1\n"
        "Ketentuan umum dalam undang-undang ini yang dimaksud dengan "
        "Cipta Kerja adalah upaya penciptaan kerja melalui usaha.\n\n"
        "Pasal 2\n"
        "Pemerintah Pusat dan Pemerintah Daerah menyelenggarakan "
        "kebijakan Cipta Kerja secara terpadu.\n",
        encoding="utf-8",
    )

    pipeline = MarkdownIngestionPipeline(
        qdrant_url="http://localhost:6333",
        collection_name="test_col",
    )

    parsed = _make_parsed_regulation()

    # Mock parser to return our controlled ParsedRegulation
    with patch.object(pipeline.parser, "parse", return_value=parsed):
        # Mock embedder to return dummy vectors (384-dim)
        mock_embedder = MagicMock()
        mock_embedder.embed_documents.return_value = [
            [0.1] * 384 for _ in range(10)
        ]
        pipeline._embedder = mock_embedder

        stats = pipeline.run(
            data_dir=data_dir,
            batch_size=50,
            optimize_bulk=False,
            checkpoint_file=None,
        )

    assert stats.total_files == 1
    assert stats.parsed == 1
    assert stats.chunks_created >= 1
    assert stats.errors == 0

    # Verify qdrant upsert was called
    mock_qclient.upsert.assert_called()
    assert stats.uploaded >= 1


# ── Checkpointer: corrupt file ──────────────────────────────────────────────


def test_checkpointer_corrupt_file_returns_none(tmp_path: Path):
    """Corrupt JSON checkpoint file → load() returns None gracefully."""
    cp_file = tmp_path / "bad_checkpoint.json"
    cp_file.write_text("{invalid json!!", encoding="utf-8")

    ckpt = IngestionCheckpointer(cp_file)
    assert ckpt.load() is None
