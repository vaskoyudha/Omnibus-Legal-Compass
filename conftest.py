"""
Shared pytest fixtures for Omnibus Legal Compass test suite.

Provides mocked dependencies for backend testing without requiring
live Qdrant or NVIDIA NIM API connections.
"""

from __future__ import annotations

import sys
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Ensure backend is importable from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))


# ── SearchResult fixture data ────────────────────────────────────────────────


@pytest.fixture
def sample_search_results():
    """Return a list of 3 SearchResult objects with realistic Indonesian legal data."""
    from retriever import SearchResult

    return [
        SearchResult(
            id=1,
            text=(
                "Perseroan Terbatas yang selanjutnya disebut Perseroan adalah badan hukum "
                "yang merupakan persekutuan modal, didirikan berdasarkan perjanjian, melakukan "
                "kegiatan usaha dengan modal dasar yang seluruhnya terbagi dalam saham."
            ),
            citation="UU No. 40 Tahun 2007 tentang Perseroan Terbatas, Pasal 1 ayat (1)",
            citation_id="uu-40-2007-pasal-1-1",
            score=0.89,
            metadata={
                "jenis_dokumen": "UU",
                "tahun": 2007,
                "nomor": 40,
                "tentang": "Perseroan Terbatas",
            },
        ),
        SearchResult(
            id=2,
            text=(
                "Modal dasar Perseroan paling sedikit Rp50.000.000,00 (lima puluh juta rupiah). "
                "Paling sedikit 25% dari modal dasar harus ditempatkan dan disetor penuh."
            ),
            citation="UU No. 40 Tahun 2007 tentang Perseroan Terbatas, Pasal 32 ayat (1)",
            citation_id="uu-40-2007-pasal-32-1",
            score=0.82,
            metadata={
                "jenis_dokumen": "UU",
                "tahun": 2007,
                "nomor": 40,
                "tentang": "Perseroan Terbatas",
            },
        ),
        SearchResult(
            id=3,
            text=(
                "Perizinan Berusaha adalah legalitas yang diberikan kepada Pelaku Usaha untuk "
                "memulai dan menjalankan usaha dan/atau kegiatannya melalui sistem OSS "
                "(Online Single Submission)."
            ),
            citation="PP No. 5 Tahun 2021 tentang Penyelenggaraan Perizinan Berusaha Berbasis Risiko, Pasal 1",
            citation_id="pp-5-2021-pasal-1",
            score=0.75,
            metadata={
                "jenis_dokumen": "PP",
                "tahun": 2021,
                "nomor": 5,
                "tentang": "Penyelenggaraan Perizinan Berusaha Berbasis Risiko",
            },
        ),
    ]


# ── Sample query ─────────────────────────────────────────────────────────────


@pytest.fixture
def sample_legal_query() -> str:
    """Return a sample Indonesian legal question string."""
    return "Apa syarat pendirian Perseroan Terbatas (PT) di Indonesia?"


# ── Qdrant mock ──────────────────────────────────────────────────────────────


@pytest.fixture
def mock_qdrant_client():
    """
    Patch qdrant_client.QdrantClient with a MagicMock.

    Provides sensible defaults for .scroll(), .search(), and .get_collection().
    """
    mock_client = MagicMock()

    # .get_collection() → object with points_count
    collection_info = MagicMock()
    collection_info.points_count = 10
    mock_client.get_collection.return_value = collection_info

    # .scroll() → (records_list, next_offset)
    mock_client.scroll.return_value = ([], None)

    # .search() → empty list
    mock_client.search.return_value = []

    # .query_points() → object with empty points list
    query_response = MagicMock()
    query_response.points = []
    mock_client.query_points.return_value = query_response

    with patch("qdrant_client.QdrantClient", return_value=mock_client) as patched:
        yield mock_client


# ── NVIDIA NIM LLM mock ─────────────────────────────────────────────────────


@pytest.fixture
def mock_nvidia_llm():
    """
    Patch NVIDIANimClient to return a canned legal response.

    Avoids real NVIDIA API calls during testing.
    """
    canned_response = (
        "Berdasarkan Undang-Undang Nomor 40 Tahun 2007 tentang Perseroan Terbatas, "
        "syarat pendirian PT meliputi minimal dua orang pendiri yang membuat akta "
        "pendirian di hadapan notaris dalam Bahasa Indonesia [1]. Modal dasar PT "
        "paling sedikit Rp50.000.000 (lima puluh juta rupiah), dan 25% harus "
        "ditempatkan serta disetor penuh [2].\n\n"
        "Selain itu, pelaku usaha wajib memiliki Nomor Induk Berusaha (NIB) yang "
        "diperoleh melalui sistem OSS sebagai legalitas perizinan berusaha [3].\n\n"
        "Jawaban ini memiliki tingkat keyakinan tinggi karena didukung langsung "
        "oleh pasal-pasal dalam UU Perseroan Terbatas dan PP tentang Perizinan Berusaha."
    )

    mock_client = MagicMock()
    mock_client.generate.return_value = canned_response
    mock_client.generate_stream.return_value = iter(
        [canned_response[i : i + 50] for i in range(0, len(canned_response), 50)]
    )

    with patch("rag_chain.NVIDIANimClient", return_value=mock_client) as patched:
        yield mock_client


# ── FastAPI TestClient ───────────────────────────────────────────────────────


@pytest.fixture
def test_client(mock_qdrant_client, mock_nvidia_llm):
    """
    FastAPI TestClient for backend.main:app with mocked dependencies.

    Injects mock Qdrant and NVIDIA NIM so the app starts without
    live external services.
    """
    # Patch HybridRetriever to avoid real Qdrant/embedding init
    mock_retriever = MagicMock()
    mock_retriever.collection_name = "indonesian_legal_docs"
    mock_retriever.client = mock_qdrant_client
    mock_retriever.hybrid_search.return_value = []
    mock_retriever.search_by_document_type.return_value = []

    # Patch LegalRAGChain to use our mocked retriever and LLM
    with patch("rag_chain.HybridRetriever", return_value=mock_retriever), \
         patch("rag_chain.NVIDIANimClient", return_value=mock_nvidia_llm):
        # Import app after patching so lifespan uses mocks
        from main import app

        with TestClient(app) as client:
            yield client
