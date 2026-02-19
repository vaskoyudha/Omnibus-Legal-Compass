"""
Unit tests for backend.multi_query.MultiQueryFusion using mocked retriever.

Follows mocking patterns from tests/test_hyde.py (unittest.mock).
"""
from unittest.mock import Mock, MagicMock

import pytest

from backend.multi_query import MultiQueryFusion, _extract_core_topic
from backend.retriever import SearchResult


@pytest.fixture
def mock_retriever():
    return MagicMock()


def _make_search_result(i, citation_id, score=0.9, citation=None):
    """Helper to build SearchResult objects similar to retriever.SearchResult."""
    if citation is None:
        citation = f"UU No. {i} Tahun 2020, Pasal {i}"
    return SearchResult(
        id=i,
        text=f"Pasal {i} tentang hukum Indonesia",
        citation=citation,
        citation_id=citation_id,
        score=score,
        metadata={"jenis_dokumen": "UU", "tahun": 2020},
    )


class TestMultiQueryFusion:
    def test_generate_variants_produces_five_variants(self):
        mqf = MultiQueryFusion()
        variants = mqf.generate_variants("Apa syarat pendirian PT?")

        assert len(variants) == 5
        # First variant should be the core topic itself (original template)
        assert variants[0] == "syarat pendirian PT"
        # Other variants should contain the core topic
        for variant in variants[1:]:
            assert "syarat pendirian PT" in variant

    def test_extract_core_topic_strips_question_words(self):
        """Test 10+ patterns of Indonesian question word stripping."""
        cases = [
            ("Apa itu PT?", "PT"),
            ("Bagaimana cara mendirikan CV?", "cara mendirikan CV"),
            ("Siapa yang bertanggung jawab?", "bertanggung jawab"),
            ("Kapan berlaku UU Cipta Kerja?", "berlaku UU Cipta Kerja"),
            ("Dimana mendaftarkan perusahaan?", "mendaftarkan perusahaan"),
            ("Mengapa perlu izin usaha?", "perlu izin usaha"),
            ("Berapa modal minimum PT?", "modal minimum PT"),
            ("Apakah PKWT itu sah?", "PKWT sah"),
            ("Apa yang dimaksud dari RUPS?", "dimaksud RUPS"),
            ("Bagaimana itu adalah ketentuan dari pasal?", "ketentuan pasal"),
        ]
        for question, expected in cases:
            result = _extract_core_topic(question)
            assert result == expected, f"Failed for '{question}': got '{result}', expected '{expected}'"

    def test_extract_core_topic_preserves_content(self):
        """Verify meaningful content remains intact after extraction."""
        # No question words — should preserve everything
        result = _extract_core_topic("syarat pendirian PT")
        assert result == "syarat pendirian PT"

        # Longer phrase with only one question word
        result = _extract_core_topic("Apa syarat modal dasar perseroan terbatas?")
        assert result == "syarat modal dasar perseroan terbatas"

        # All question words — fallback to original minus punctuation
        result = _extract_core_topic("Apa itu?")
        assert result == "Apa itu"

    def test_enhanced_search_calls_retriever_five_times(self, mock_retriever):
        """Mock retriever and assert 5 calls to .hybrid_search (one per variant)."""
        mock_retriever.hybrid_search.return_value = [
            _make_search_result(1, "UU_1", score=0.9),
        ]

        mqf = MultiQueryFusion()
        mqf.enhanced_search("Apa syarat pendirian PT?", mock_retriever, top_k=3)

        assert mock_retriever.hybrid_search.call_count == 5

    def test_enhanced_search_rrf_merges_overlapping_results(self, mock_retriever):
        """Same doc in multiple result lists → higher RRF score."""
        # UU_OVERLAP appears in 3 out of 5 lists → should rank highest
        list_with_overlap = [
            _make_search_result(10, "UU_OVERLAP", score=0.9),
            _make_search_result(2, "UU_UNIQUE_A", score=0.8),
        ]
        list_with_overlap_2 = [
            _make_search_result(11, "UU_OVERLAP", score=0.85),
            _make_search_result(3, "UU_UNIQUE_B", score=0.7),
        ]
        list_with_overlap_3 = [
            _make_search_result(12, "UU_OVERLAP", score=0.88),
            _make_search_result(4, "UU_UNIQUE_C", score=0.6),
        ]
        list_no_overlap_1 = [
            _make_search_result(5, "UU_UNIQUE_D", score=0.75),
        ]
        list_no_overlap_2 = [
            _make_search_result(6, "UU_UNIQUE_E", score=0.65),
        ]

        mock_retriever.hybrid_search.side_effect = [
            list_with_overlap,
            list_with_overlap_2,
            list_with_overlap_3,
            list_no_overlap_1,
            list_no_overlap_2,
        ]

        mqf = MultiQueryFusion()
        merged = mqf.enhanced_search("Test overlap", mock_retriever, top_k=5)

        # UU_OVERLAP should be first (highest RRF score — appears in 3 lists)
        assert merged[0].citation_id == "UU_OVERLAP"

        # All results should be sorted by descending RRF score
        scores = [r.score for r in merged]
        assert scores == sorted(scores, reverse=True)

        # Should have 6 unique documents total
        # (UU_OVERLAP + UU_UNIQUE_A + UU_UNIQUE_B + UU_UNIQUE_C + UU_UNIQUE_D + UU_UNIQUE_E)
        citation_ids = [r.citation_id for r in merged]
        assert len(set(citation_ids)) == 6
        assert len(citation_ids) == 6  # no duplicates

    def test_enhanced_search_handles_empty_results(self, mock_retriever):
        """Some variants return [] → no crash, returns whatever is available."""
        results_with_data = [
            _make_search_result(1, "UU_1", score=0.9),
        ]
        # 3 variants return empty, 2 return data
        mock_retriever.hybrid_search.side_effect = [
            [],
            results_with_data,
            [],
            [],
            results_with_data,
        ]

        mqf = MultiQueryFusion()
        merged = mqf.enhanced_search("Empty test", mock_retriever, top_k=3)

        # Should not crash; UU_1 appears in 2 lists
        assert len(merged) == 1
        assert merged[0].citation_id == "UU_1"

    def test_enhanced_search_all_empty(self, mock_retriever):
        """All variants return empty results → returns []."""
        mock_retriever.hybrid_search.side_effect = [[], [], [], [], []]

        mqf = MultiQueryFusion()
        merged = mqf.enhanced_search("Nothing here", mock_retriever, top_k=3)

        assert merged == []
