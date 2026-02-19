"""
Unit tests for backend.crag.CRAG using mocked LLM and retriever.

Follows mocking patterns from tests/test_hyde.py (unittest.mock).
"""
from unittest.mock import Mock, MagicMock

import pytest

from backend.crag import CRAG
from backend.retriever import SearchResult


@pytest.fixture
def mock_llm_client():
    m = Mock()
    m.generate.return_value = "Pertanyaan hukum yang diulang"
    return m


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


class TestCRAG:
    # ------------------------------------------------------------------ #
    # grade_retrieval tests
    # ------------------------------------------------------------------ #

    def test_grade_correct_high_scores(self):
        """Results with avg score ≥ 0.7 → 'correct'."""
        crag = CRAG()
        results = [
            _make_search_result(1, "UU_1", score=0.9),
            _make_search_result(2, "UU_2", score=0.8),
            _make_search_result(3, "UU_3", score=0.7),
        ]
        grade = crag.grade_retrieval("Syarat pendirian PT?", results)
        assert grade == "correct"

    def test_grade_ambiguous_medium_scores(self):
        """Results with 0.3 ≤ avg < 0.7 → 'ambiguous'."""
        crag = CRAG()
        results = [
            _make_search_result(1, "UU_1", score=0.5),
            _make_search_result(2, "UU_2", score=0.4),
            _make_search_result(3, "UU_3", score=0.6),
        ]
        grade = crag.grade_retrieval("Apa itu PKWT?", results)
        assert grade == "ambiguous"

    def test_grade_incorrect_low_scores(self):
        """Results with avg score < 0.3 → 'incorrect'."""
        crag = CRAG()
        results = [
            _make_search_result(1, "UU_1", score=0.1),
            _make_search_result(2, "UU_2", score=0.2),
            _make_search_result(3, "UU_3", score=0.15),
        ]
        grade = crag.grade_retrieval("Resep nasi goreng?", results)
        assert grade == "incorrect"

    def test_grade_empty_results_returns_incorrect(self):
        """Empty results list → 'incorrect'."""
        crag = CRAG()
        grade = crag.grade_retrieval("Pertanyaan kosong", [])
        assert grade == "incorrect"

    # ------------------------------------------------------------------ #
    # rephrase_query tests
    # ------------------------------------------------------------------ #

    def test_rephrase_calls_llm_with_correct_prompt(self, mock_llm_client):
        """rephrase_query calls LLM with the Indonesian rephrasing prompt."""
        mock_llm_client.generate.return_value = "Persyaratan mendirikan PT"

        crag = CRAG(mock_llm_client)
        question = "Apa syarat pendirian PT?"
        result = crag.rephrase_query(question)

        assert result == "Persyaratan mendirikan PT"
        mock_llm_client.generate.assert_called_once()

        # Verify prompt contains the question and Indonesian instructions
        call_kwargs = mock_llm_client.generate.call_args.kwargs
        assert "user_message" in call_kwargs
        prompt = call_kwargs["user_message"]
        assert question in prompt
        assert "Ulangi pertanyaan hukum" in prompt
        assert "Pertanyaan yang diulang:" in prompt

    def test_rephrase_no_llm_returns_original_question(self):
        """Without LLM client, rephrase_query returns the original question."""
        crag = CRAG()  # No LLM client
        question = "Apa syarat pendirian PT?"
        result = crag.rephrase_query(question)
        assert result == question

    # ------------------------------------------------------------------ #
    # enhanced_search tests
    # ------------------------------------------------------------------ #

    def test_enhanced_search_correct_returns_original(self, mock_llm_client, mock_retriever):
        """When grade is 'correct', return original results without rephrasing."""
        high_score_results = [
            _make_search_result(1, "UU_1", score=0.9),
            _make_search_result(2, "UU_2", score=0.8),
        ]
        mock_retriever.hybrid_search.return_value = high_score_results

        crag = CRAG(mock_llm_client)
        results = crag.enhanced_search("Syarat PT?", mock_retriever, top_k=5)

        # Should return original results as-is
        assert results == high_score_results
        # hybrid_search called only once (no rephrase search)
        assert mock_retriever.hybrid_search.call_count == 1
        # LLM never called for rephrasing
        mock_llm_client.generate.assert_not_called()

    def test_enhanced_search_ambiguous_merges_rrf(self, mock_llm_client, mock_retriever):
        """When grade is 'ambiguous', rephrase and RRF-merge both result sets."""
        mock_llm_client.generate.return_value = "Pertanyaan yang diulang"

        original_results = [
            _make_search_result(1, "UU_1", score=0.5),
            _make_search_result(2, "UU_2", score=0.4),
        ]
        rephrased_results = [
            _make_search_result(3, "UU_2", score=0.6),  # Overlap on UU_2
            _make_search_result(4, "UU_3", score=0.5),
        ]

        mock_retriever.hybrid_search.side_effect = [original_results, rephrased_results]

        crag = CRAG(mock_llm_client)
        merged = crag.enhanced_search("Pertanyaan ambigu", mock_retriever, top_k=5)

        # hybrid_search called twice (original + rephrased)
        assert mock_retriever.hybrid_search.call_count == 2
        # LLM called for rephrasing
        mock_llm_client.generate.assert_called_once()

        # Three unique citation_ids: UU_1, UU_2, UU_3
        citation_ids = [r.citation_id for r in merged]
        assert len(merged) == 3
        assert set(citation_ids) == {"UU_1", "UU_2", "UU_3"}

        # UU_2 appears in both lists → highest RRF score → ranked first
        assert merged[0].citation_id == "UU_2"

        # Scores should be descending
        scores = [r.score for r in merged]
        assert scores == sorted(scores, reverse=True)

    def test_enhanced_search_incorrect_replaces_with_rephrased(
        self, mock_llm_client, mock_retriever
    ):
        """When grade is 'incorrect', return ONLY rephrased results."""
        mock_llm_client.generate.return_value = "Pertanyaan yang lebih baik"

        low_score_results = [
            _make_search_result(1, "UU_1", score=0.1),
            _make_search_result(2, "UU_2", score=0.2),
        ]
        rephrased_results = [
            _make_search_result(3, "UU_3", score=0.8),
            _make_search_result(4, "UU_4", score=0.7),
        ]

        mock_retriever.hybrid_search.side_effect = [low_score_results, rephrased_results]

        crag = CRAG(mock_llm_client)
        results = crag.enhanced_search("Resep masak?", mock_retriever, top_k=5)

        # hybrid_search called twice
        assert mock_retriever.hybrid_search.call_count == 2
        # LLM called for rephrasing
        mock_llm_client.generate.assert_called_once()

        # Should return ONLY rephrased results (original discarded)
        assert results == rephrased_results
        citation_ids = [r.citation_id for r in results]
        assert "UU_1" not in citation_ids
        assert "UU_2" not in citation_ids
        assert set(citation_ids) == {"UU_3", "UU_4"}

    def test_enhanced_search_no_llm_graceful_degradation(self, mock_retriever):
        """Without LLM, ambiguous/incorrect grades still work (no rephrase)."""
        # Ambiguous scores, no LLM client
        ambiguous_results = [
            _make_search_result(1, "UU_1", score=0.5),
            _make_search_result(2, "UU_2", score=0.4),
        ]
        # When rephrase returns original question, second search returns same results
        mock_retriever.hybrid_search.side_effect = [ambiguous_results, ambiguous_results]

        crag = CRAG()  # No LLM client
        results = crag.enhanced_search("Pertanyaan tanpa LLM", mock_retriever, top_k=5)

        # hybrid_search still called twice (original + "rephrased" which is same)
        assert mock_retriever.hybrid_search.call_count == 2

        # Results should be deduplicated via RRF
        citation_ids = [r.citation_id for r in results]
        assert len(results) == 2
        assert set(citation_ids) == {"UU_1", "UU_2"}

    # ------------------------------------------------------------------ #
    # Edge case tests
    # ------------------------------------------------------------------ #

    def test_grade_boundary_exactly_correct_threshold(self):
        """Score exactly at CORRECT_THRESHOLD (0.7) → 'correct'."""
        crag = CRAG()
        results = [_make_search_result(1, "UU_1", score=0.7)]
        grade = crag.grade_retrieval("Boundary test", results)
        assert grade == "correct"

    def test_grade_boundary_exactly_ambiguous_threshold(self):
        """Score exactly at AMBIGUOUS_THRESHOLD (0.3) → 'ambiguous'."""
        crag = CRAG()
        results = [_make_search_result(1, "UU_1", score=0.3)]
        grade = crag.grade_retrieval("Boundary test", results)
        assert grade == "ambiguous"

    def test_rephrase_llm_exception_falls_back(self, mock_llm_client):
        """If LLM raises exception during rephrase, fall back to original."""
        mock_llm_client.generate.side_effect = Exception("LLM down")

        crag = CRAG(mock_llm_client)
        question = "Apa itu PKWT?"
        result = crag.rephrase_query(question)

        assert result == question

    def test_enhanced_search_empty_initial_results(self, mock_llm_client, mock_retriever):
        """Empty initial results → grade 'incorrect' → rephrase and replace."""
        mock_llm_client.generate.return_value = "Pertanyaan yang lebih baik"

        rephrased_results = [
            _make_search_result(1, "UU_1", score=0.8),
        ]
        mock_retriever.hybrid_search.side_effect = [[], rephrased_results]

        crag = CRAG(mock_llm_client)
        results = crag.enhanced_search("Pertanyaan kosong", mock_retriever, top_k=5)

        # Empty → incorrect → rephrase → return rephrased results only
        assert mock_retriever.hybrid_search.call_count == 2
        assert results == rephrased_results
