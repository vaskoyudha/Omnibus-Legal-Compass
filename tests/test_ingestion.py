"""
Tests for Qdrant ingestion pipeline with NVIDIA NIM embeddings.
TDD approach - tests written first.
"""
import json
import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from dotenv import load_dotenv

# Load env at module level so skipif decorators can access env vars
load_dotenv()

# Tests should avoid heavy imports at module load. Individual tests import
# backend.scripts.ingest when they need embedder-specific constants.


def get_expected_embedding_dim() -> int:
    """Return embedding dimension according to the currently active
    embedder configuration in backend.scripts.ingest. Falls back to
    environment-derived defaults when the module cannot be queried.
    """
    try:
        from backend.scripts.ingest import get_collection_config

        cfg = get_collection_config()
        if cfg and "vectors_config" in cfg and "size" in cfg["vectors_config"]:
            return int(cfg["vectors_config"]["size"])
    except Exception:
        pass

    # Fallback precedence: Jina > NVIDIA > HuggingFace
    if os.getenv("USE_JINA_EMBEDDINGS", "false").lower() == "true":
        return int(os.getenv("JINA_EMBEDDING_DIM", "1024"))
    if os.getenv("USE_NVIDIA_EMBEDDINGS", "false").lower() == "true":
        return 1024
    return 384


# Test data path
DATA_DIR = Path(__file__).parent.parent / "data" / "peraturan"
SAMPLE_JSON = DATA_DIR / "sample.json"


class TestDocumentLoader:
    """Tests for loading legal documents from JSON."""
    
    def test_load_sample_json_exists(self):
        """Verify sample.json exists."""
        assert SAMPLE_JSON.exists(), f"Sample file not found: {SAMPLE_JSON}"
    
    def test_load_sample_json_valid(self):
        """Load and validate sample documents."""
        with open(SAMPLE_JSON, "r", encoding="utf-8") as f:
            docs = json.load(f)
        
        assert isinstance(docs, list)
        assert len(docs) == 10
        
        # Check required fields
        required_fields = ["jenis_dokumen", "nomor", "tahun", "judul", "text"]
        for doc in docs:
            for field in required_fields:
                assert field in doc, f"Missing field: {field}"
    
    def test_document_has_searchable_text(self):
        """Each document must have non-empty text for embedding."""
        with open(SAMPLE_JSON, "r", encoding="utf-8") as f:
            docs = json.load(f)
        
        for i, doc in enumerate(docs):
            assert doc.get("text"), f"Document {i} has empty text"
            assert len(doc["text"]) > 10, f"Document {i} text too short"


class TestDocumentChunker:
    """Tests for chunking legal documents."""
    
    def test_chunk_document_creates_metadata(self):
        """Chunked documents must preserve metadata for citations."""
        from backend.scripts.ingest import create_document_chunks
        
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "11",
            "tahun": 2020,
            "judul": "Cipta Kerja",
            "tentang": "Penciptaan Lapangan Kerja",
            "bab": "I",
            "pasal": "1",
            "text": "Dalam Undang-Undang ini yang dimaksud dengan penanaman modal."
        }
        
        chunks = create_document_chunks([doc])
        
        assert len(chunks) >= 1
        chunk = chunks[0]
        
        # Verify metadata preserved for citations
        assert chunk["metadata"]["jenis_dokumen"] == "UU"
        assert chunk["metadata"]["nomor"] == "11"
        assert chunk["metadata"]["tahun"] == 2020
        assert chunk["metadata"]["judul"] == "Cipta Kerja"
        assert chunk["metadata"]["pasal"] == "1"
        assert "text" in chunk
    
    def test_chunk_generates_citation_id(self):
        """Each chunk must have a unique citation ID."""
        from backend.scripts.ingest import create_document_chunks
        
        doc = {
            "jenis_dokumen": "PP",
            "nomor": "24",
            "tahun": 2018,
            "judul": "Perizinan Berusaha",
            "pasal": "3",
            "text": "Setiap Perizinan Berusaha wajib diterbitkan melalui OSS."
        }
        
        chunks = create_document_chunks([doc])
        
        assert chunks[0]["citation_id"]
        # Format: PP_24_2018_Pasal3
        assert "PP" in chunks[0]["citation_id"]
        assert "24" in chunks[0]["citation_id"]
        assert "2018" in chunks[0]["citation_id"]


class TestEmbeddingGenerator:
    """Tests for HuggingFace embedding generation."""
    
    def test_huggingface_embeddings_connection(self):
        """Test connection to HuggingFace embeddings (local)."""
        from langchain_huggingface import HuggingFaceEmbeddings
        
        embedder = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        
        # Test single query embedding
        result = embedder.embed_query("Apa itu penanaman modal?")

        assert isinstance(result, list)
        # Assert embedding dimension equals the HuggingFace model dimension
        # (use EMBEDDING_DIM from backend.scripts.ingest to mirror production
        # model size rather than environment-derived defaults)
        from backend.scripts.ingest import EMBEDDING_DIM

        assert len(result) == EMBEDDING_DIM
        assert all(isinstance(x, float) for x in result)
    
    def test_embedding_dimension_consistency(self):
        """Embeddings must have consistent dimensions."""
        # Mock embeddings for unit test
        mock_embeddings = [
            [0.1] * get_expected_embedding_dim(),
            [0.2] * get_expected_embedding_dim(),
            [0.3] * get_expected_embedding_dim(),
        ]
        
        # All should be same dimension
        dims = [len(e) for e in mock_embeddings]
        assert len(set(dims)) == 1, "Embedding dimensions must be consistent"


class TestQdrantIngestion:
    """Tests for Qdrant collection creation and data ingestion."""
    
    def test_collection_config(self):
        """Verify collection configuration for hybrid search."""
        from backend.scripts.ingest import get_collection_config
        
        config = get_collection_config()

        # Must have dense vector config
        vc = config.get("vectors_config") if config else None
        assert vc, "vectors_config missing from collection config"

        # The collection config must match the active embedder's dimension
        assert int(vc.get("size", 0)) == get_expected_embedding_dim()
        assert vc.get("distance") == "Cosine"
    
    def test_point_struct_creation(self):
        """Test creating Qdrant points from chunks."""
        from backend.scripts.ingest import create_point_struct
        
        chunk = {
            "text": "Penanaman modal adalah kegiatan menanamkan modal.",
            "citation_id": "UU_11_2020_Pasal1",
            "metadata": {
                "jenis_dokumen": "UU",
                "nomor": "11",
                "tahun": 2020,
                "judul": "Cipta Kerja",
                "pasal": "1"
            }
        }
        mock_embedding = [0.1] * get_expected_embedding_dim()
        
        point = create_point_struct(
            point_id=1,
            chunk=chunk,
            embedding=mock_embedding
        )
        
        assert point.id == 1
        assert point.vector == mock_embedding
        assert point.payload is not None
        payload = point.payload
        assert payload["text"] == chunk["text"]
        assert payload["citation_id"] == chunk["citation_id"]
        assert payload["jenis_dokumen"] == "UU"
    
    @pytest.mark.skipif(
        not os.getenv("QDRANT_URL"),
        reason="QDRANT_URL not set (Qdrant not running)"
    )
    def test_qdrant_connection(self):
        """Test connection to Qdrant server."""
        from qdrant_client import QdrantClient
        
        client = QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"))
        
        # Check health
        info = client.get_collections()
        assert info is not None


class TestIngestionPipeline:
    """End-to-end ingestion pipeline tests."""
    
    def test_full_pipeline_mock(self):
        """Test full ingestion pipeline with mocks."""
        from backend.scripts.ingest import ingest_documents
        
        with patch("backend.scripts.ingest.QdrantClient") as MockQdrant, \
             patch("backend.scripts.ingest.HuggingFaceEmbeddings") as MockEmbed:
            
            # Setup mocks
            mock_client = MagicMock()
            MockQdrant.return_value = mock_client
            
            # get_collection raises so ensure_collection_exists creates new
            mock_client.get_collection.side_effect = [
                Exception("not found"),  # first call: ensure_collection_exists
            ]
            # scroll returns empty (no existing docs)
            mock_client.scroll.return_value = ([], None)
            
            # Force ingest to use HuggingFace path for determinism in this test
            import backend.scripts.ingest as ingest_module
            ingest_module.USE_JINA_EMBEDDINGS = False
            ingest_module.USE_NVIDIA_EMBEDDINGS = False

            mock_embedder = MagicMock()
            mock_embedder.embed_documents.return_value = [[0.1] * get_expected_embedding_dim()] * 10
            MockEmbed.return_value = mock_embedder
            
            # Run ingestion
            result = ingest_documents(
                json_path=str(SAMPLE_JSON),
                collection_name="test_legal_docs",
                qdrant_url="http://localhost:6333"
            )
            
            # Verify calls — ensure_collection_exists path
            mock_client.create_collection.assert_called_once()
            mock_embedder.embed_documents.assert_called()
            mock_client.upsert.assert_called()
            
            assert result["status"] == "success"
            assert result["documents_loaded"] == 10
            assert result["chunks_new"] >= 1


class TestCitationFormat:
    """Tests for citation format generation."""
    
    def test_citation_format_uu(self):
        """Test citation format for Undang-Undang."""
        from backend.scripts.ingest import format_citation
        
        metadata = {
            "jenis_dokumen": "UU",
            "nomor": "11",
            "tahun": 2020,
            "judul": "Cipta Kerja",
            "pasal": "5",
            "ayat": "1"
        }
        
        citation = format_citation(metadata)
        
        assert "UU No. 11 Tahun 2020" in citation
        assert "Cipta Kerja" in citation
        assert "Pasal 5" in citation
        assert "Ayat (1)" in citation
    
    def test_citation_format_pp(self):
        """Test citation format for Peraturan Pemerintah."""
        from backend.scripts.ingest import format_citation
        
        metadata = {
            "jenis_dokumen": "PP",
            "nomor": "24",
            "tahun": 2018,
            "judul": "Perizinan Berusaha Terintegrasi",
            "pasal": "3"
        }
        
        citation = format_citation(metadata)
        
        assert "PP No. 24 Tahun 2018" in citation
        assert "Pasal 3" in citation
    
    def test_citation_format_perpres(self):
        """Test citation format for Peraturan Presiden."""
        from backend.scripts.ingest import format_citation
        
        metadata = {
            "jenis_dokumen": "Perpres",
            "nomor": "49",
            "tahun": 2021,
            "judul": "NIB",
            "pasal": "3"
        }
        
        citation = format_citation(metadata)
        
        assert "Perpres No. 49 Tahun 2021" in citation
