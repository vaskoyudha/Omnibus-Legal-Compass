"""
Tests for backend.semantic_chunker — Semantic Chunking module.

CRITICAL: All tests mock SentenceTransformer to avoid loading the 80MB model.
Tests validate chunking logic, sentence splitting, cosine similarity, and
edge cases using predictable mock embeddings.
"""

from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import MagicMock

from backend.semantic_chunker import SemanticChunker, _split_sentences, _cosine_similarity


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_embedder():
    """Create a mock embedder (replaces the real SentenceTransformer)."""
    mock_instance = MagicMock()
    # Default: return identity-like embeddings (tests override as needed)
    mock_instance.encode.return_value = np.array([[1.0, 0.0]])
    return mock_instance


@pytest.fixture
def chunker_with_mock(mock_embedder):
    """Return a SemanticChunker whose embedder is already mocked."""
    chunker = SemanticChunker(similarity_threshold=0.5, max_chunk_size=1500)
    # Inject mock directly — bypasses lazy-load entirely, no model downloaded
    chunker._embedder = mock_embedder
    return chunker


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestSemanticChunker:
    """Tests for SemanticChunker class and helper functions."""

    # 1. Empty input
    def test_empty_input_returns_empty_list(self, chunker_with_mock):
        """Empty or whitespace-only input returns []."""
        assert chunker_with_mock.chunk("") == []
        assert chunker_with_mock.chunk("   ") == []
        assert chunker_with_mock.chunk("\n\t") == []

    # 2. Single sentence
    def test_single_sentence_returns_single_chunk(self, chunker_with_mock):
        """A single sentence (no split points) returns [text.strip()]."""
        text = "Pasal 1 tentang ketentuan umum"
        result = chunker_with_mock.chunk(text)
        assert result == ["Pasal 1 tentang ketentuan umum"]

    # 3. Similar sentences grouped together
    def test_similar_sentences_grouped(self, chunker_with_mock):
        """Sentences with high similarity embeddings stay in one chunk."""
        text = "Ketentuan umum berlaku. Definisi istilah hukum. Ruang lingkup peraturan."

        # All embeddings are very similar → cosine ~1.0
        chunker_with_mock._embedder.encode.return_value = np.array([
            [1.0, 0.0, 0.0],
            [0.99, 0.1, 0.0],
            [0.98, 0.15, 0.0],
        ])

        result = chunker_with_mock.chunk(text)

        # All sentences should be in a single chunk (high similarity)
        assert len(result) == 1
        assert "Ketentuan umum berlaku." in result[0]
        assert "Definisi istilah hukum." in result[0]
        assert "Ruang lingkup peraturan." in result[0]

    # 4. Different sentences split into separate chunks
    def test_different_sentences_split(self, chunker_with_mock):
        """Sentences with low similarity are split into separate chunks."""
        text = "Ketentuan umum berlaku. Sanksi pidana diterapkan. Definisi istilah hukum."

        # First pair: very similar. Second pair: very different → split.
        chunker_with_mock._embedder.encode.return_value = np.array([
            [1.0, 0.0, 0.0],   # Sentence 1
            [0.99, 0.1, 0.0],  # Sentence 2: similar to 1 (cosine ~0.99)
            [0.0, 0.0, 1.0],   # Sentence 3: orthogonal to 2 (cosine ~0.0)
        ])

        result = chunker_with_mock.chunk(text)

        # Should split between sentence 2 and 3
        assert len(result) == 2
        assert "Ketentuan umum berlaku." in result[0]
        assert "Sanksi pidana diterapkan." in result[0]
        assert "Definisi istilah hukum." in result[1]

    # 5. max_chunk_size enforced
    def test_max_chunk_size_enforced(self, chunker_with_mock):
        """Chunks are split when they would exceed max_chunk_size."""
        # Three sentences, each ~30 chars. max_chunk_size=50 forces splits.
        text = "Pasal satu tentang hukum. Pasal dua tentang sanksi. Pasal tiga tentang banding."

        # All embeddings identical → cosine = 1.0 (no semantic split)
        chunker_with_mock._embedder.encode.return_value = np.array([
            [1.0, 0.0],
            [1.0, 0.0],
            [1.0, 0.0],
        ])

        # Override max_chunk_size to force size-based splits
        chunker_with_mock.max_chunk_size = 50

        result = chunker_with_mock.chunk(text)

        # With max_chunk_size=50, sentences can't all fit in one chunk
        assert len(result) >= 2
        # Each chunk should be <= 50 chars (or a single sentence if it exceeds)
        for chunk in result:
            # A single sentence may exceed 50, but joined chunks should respect limit
            assert len(chunk) <= 50 or " " not in chunk or chunk.count(".") <= 1

    # 6. Indonesian legal text handled
    def test_indonesian_text_handled(self, chunker_with_mock):
        """Bahasa Indonesia legal text is split and chunked correctly."""
        text = (
            "Perseroan Terbatas wajib didirikan oleh dua orang atau lebih. "
            "Akta pendirian dibuat di hadapan notaris. "
            "Modal dasar paling sedikit Rp50.000.000; "
            "Pendaftaran dilakukan melalui sistem AHU online."
        )

        # Similar first three, different last one
        chunker_with_mock._embedder.encode.return_value = np.array([
            [0.9, 0.1, 0.0],
            [0.85, 0.15, 0.0],
            [0.8, 0.2, 0.0],
            [0.0, 0.0, 1.0],
        ])

        result = chunker_with_mock.chunk(text)

        # Should split before the last sentence (orthogonal embedding)
        assert len(result) == 2
        assert "Perseroan Terbatas" in result[0]
        assert "AHU online" in result[1]

    # 7. Lazy loading: no immediate import
    def test_lazy_loading_no_immediate_import(self):
        """Instantiating SemanticChunker does NOT load the model."""
        chunker = SemanticChunker()
        # Model should NOT be loaded just from instantiation
        assert chunker._embedder is None
        # The sentence_transformers module should not have been imported
        # into the semantic_chunker module namespace
        import backend.semantic_chunker as sc_module
        assert not hasattr(sc_module, "SentenceTransformer")

    # 8. _split_sentences helper with various punctuation
    def test_split_sentences_punctuation(self):
        """_split_sentences correctly splits on . ! ? ; followed by whitespace."""
        text = "Pasal 1. Definisi umum! Ketentuan berlaku? Sanksi pidana; Penutup."
        result = _split_sentences(text)
        assert result == [
            "Pasal 1.",
            "Definisi umum!",
            "Ketentuan berlaku?",
            "Sanksi pidana;",
            "Penutup.",
        ]

    # 9. _cosine_similarity correctness
    def test_cosine_similarity_correctness(self):
        """_cosine_similarity returns correct values for known vectors."""
        # Identical vectors → 1.0
        a = np.array([1.0, 0.0, 0.0])
        assert _cosine_similarity(a, a) == pytest.approx(1.0)

        # Orthogonal vectors → 0.0
        b = np.array([0.0, 1.0, 0.0])
        assert _cosine_similarity(a, b) == pytest.approx(0.0)

        # Opposite vectors → -1.0
        c = np.array([-1.0, 0.0, 0.0])
        assert _cosine_similarity(a, c) == pytest.approx(-1.0)

        # Zero vector → 0.0 (no division error)
        z = np.array([0.0, 0.0, 0.0])
        assert _cosine_similarity(a, z) == pytest.approx(0.0)
        assert _cosine_similarity(z, z) == pytest.approx(0.0)

    # 10. _split_sentences with empty input
    def test_split_sentences_empty(self):
        """_split_sentences returns [] for empty strings."""
        assert _split_sentences("") == []
        assert _split_sentences("   ") == []

    # 11. Multiple breakpoints produce multiple chunks
    def test_multiple_breakpoints(self, chunker_with_mock):
        """Multiple similarity drops produce multiple chunks."""
        text = "Satu. Dua. Tiga. Empat. Lima."

        # Alternating: similar, different, similar, different
        chunker_with_mock._embedder.encode.return_value = np.array([
            [1.0, 0.0],   # Satu
            [0.0, 1.0],   # Dua  (different from Satu)
            [1.0, 0.0],   # Tiga (different from Dua)
            [0.0, 1.0],   # Empat (different from Tiga)
            [1.0, 0.0],   # Lima (different from Empat)
        ])

        result = chunker_with_mock.chunk(text)

        # Every consecutive pair is orthogonal (sim=0.0 < 0.5 threshold)
        # → each sentence becomes its own chunk
        assert len(result) == 5
