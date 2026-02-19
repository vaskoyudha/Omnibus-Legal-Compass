"""
Unit tests for backend.agentic_rag.AgenticRAG using mocked techniques and retriever.

Follows mocking patterns from tests/test_hyde.py (unittest.mock).
"""
from unittest.mock import Mock, MagicMock

import pytest

from backend.agentic_rag import AgenticRAG
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


class TestAgenticRAG:
    # ------------------------------------------------------------------ #
    # select_strategy tests
    # ------------------------------------------------------------------ #

    def test_select_strategy_decompose_compound_question(self):
        """Compound question with 'dan' keyword → 'decompose'."""
        agentic = AgenticRAG()
        strategy = agentic.select_strategy("Apa perbedaan PT dan CV?")
        assert strategy == "decompose"

    def test_select_strategy_decompose_long_question(self):
        """Question with > 15 words → 'decompose'."""
        agentic = AgenticRAG()
        long_q = "Bagaimana prosedur lengkap untuk mendaftarkan perusahaan baru di Indonesia termasuk semua izin yang diperlukan oleh pemerintah daerah"
        strategy = agentic.select_strategy(long_q)
        assert strategy == "decompose"

    def test_select_strategy_hyde_definition_question(self):
        """Definition question with 'Apa itu' → 'hyde'."""
        agentic = AgenticRAG()
        strategy = agentic.select_strategy("Apa itu PT?")
        assert strategy == "hyde"

    def test_select_strategy_hyde_pengertian(self):
        """Definition question with 'pengertian' → 'hyde'."""
        agentic = AgenticRAG()
        strategy = agentic.select_strategy("Pengertian PKWT dalam hukum?")
        assert strategy == "hyde"

    def test_select_strategy_refine_query_low_score(self):
        """Results with avg_score < 0.3 → 'refine_query'."""
        agentic = AgenticRAG()
        low_results = [
            _make_search_result(1, "UU_1", score=0.1),
            _make_search_result(2, "UU_2", score=0.2),
        ]
        strategy = agentic.select_strategy("Syarat PT", results=low_results)
        assert strategy == "refine_query"

    def test_select_strategy_multi_query_medium_score(self):
        """Results with 0.3 ≤ avg_score < 0.5 → 'multi_query'."""
        agentic = AgenticRAG()
        med_results = [
            _make_search_result(1, "UU_1", score=0.35),
            _make_search_result(2, "UU_2", score=0.40),
        ]
        strategy = agentic.select_strategy("Syarat PT", results=med_results)
        assert strategy == "multi_query"

    def test_select_strategy_direct_simple(self):
        """Simple short question without keywords → 'direct'."""
        agentic = AgenticRAG()
        strategy = agentic.select_strategy("Syarat PT")
        assert strategy == "direct"

    def test_select_strategy_direct_when_results_good(self):
        """Results with avg_score >= 0.5 → 'direct' (no refinement needed)."""
        agentic = AgenticRAG()
        good_results = [
            _make_search_result(1, "UU_1", score=0.8),
            _make_search_result(2, "UU_2", score=0.7),
        ]
        strategy = agentic.select_strategy("Syarat PT", results=good_results)
        assert strategy == "direct"

    # ------------------------------------------------------------------ #
    # enhanced_search tests
    # ------------------------------------------------------------------ #

    def test_enhanced_search_max_iterations_respected(self, mock_retriever):
        """Loop never exceeds MAX_ITERATIONS=3 even with poor results."""
        # Return consistently low-score results to force all iterations
        low_results = [
            _make_search_result(1, "UU_1", score=0.1),
            _make_search_result(2, "UU_2", score=0.1),
        ]
        mock_retriever.hybrid_search.return_value = low_results

        agentic = AgenticRAG()  # no techniques → always direct fallback
        results = agentic.enhanced_search("Syarat PT", mock_retriever, top_k=5)

        # hybrid_search should be called exactly MAX_ITERATIONS times
        assert mock_retriever.hybrid_search.call_count == AgenticRAG.MAX_ITERATIONS
        assert results == low_results

    def test_enhanced_search_early_exit_high_score(self, mock_retriever):
        """avg_score >= 0.5 on first iteration → break loop early (1 call)."""
        high_results = [
            _make_search_result(1, "UU_1", score=0.9),
            _make_search_result(2, "UU_2", score=0.8),
        ]
        mock_retriever.hybrid_search.return_value = high_results

        agentic = AgenticRAG()
        results = agentic.enhanced_search("Syarat PT", mock_retriever, top_k=5)

        # Should exit after first iteration (avg=0.85 >= 0.5)
        assert mock_retriever.hybrid_search.call_count == 1
        assert results == high_results

    def test_enhanced_search_missing_technique_fallback(self, mock_retriever):
        """If hyde=None, definition question falls back to direct search."""
        high_results = [
            _make_search_result(1, "UU_1", score=0.9),
        ]
        mock_retriever.hybrid_search.return_value = high_results

        # No hyde provided → should fallback to direct
        agentic = AgenticRAG(hyde=None)
        results = agentic.enhanced_search("Apa itu PT?", mock_retriever)

        # Should call hybrid_search (fallback from hyde)
        mock_retriever.hybrid_search.assert_called()
        assert results == high_results

    def test_enhanced_search_uses_hyde_when_available(self, mock_retriever):
        """Definition question with hyde available → calls hyde.enhanced_search."""
        mock_hyde = Mock()
        hyde_results = [
            _make_search_result(1, "UU_1", score=0.9),
        ]
        mock_hyde.enhanced_search.return_value = hyde_results

        agentic = AgenticRAG(hyde=mock_hyde)
        results = agentic.enhanced_search("Apa itu PT?", mock_retriever)

        mock_hyde.enhanced_search.assert_called_once_with(
            "Apa itu PT?", mock_retriever, top_k=5
        )
        assert results == hyde_results

    def test_enhanced_search_uses_query_planner_for_compound(self, mock_retriever):
        """Compound question with query_planner → calls multi_hop_search."""
        mock_qp = Mock()
        qp_results = [
            _make_search_result(1, "UU_1", score=0.8),
            _make_search_result(2, "UU_2", score=0.7),
        ]
        mock_qp.multi_hop_search.return_value = qp_results

        agentic = AgenticRAG(query_planner=mock_qp)
        results = agentic.enhanced_search(
            "Apa perbedaan PT dan CV?", mock_retriever
        )

        mock_qp.multi_hop_search.assert_called_once_with(
            "Apa perbedaan PT dan CV?", mock_retriever, top_k=5
        )
        assert results == qp_results

    def test_enhanced_search_refine_with_crag_on_low_scores(self, mock_retriever):
        """Low scores on iteration 1 → selects refine_query → calls CRAG."""
        mock_crag = Mock()
        crag_results = [
            _make_search_result(1, "UU_1", score=0.8),
        ]
        mock_crag.enhanced_search.return_value = crag_results

        # First call returns low scores, triggering CRAG on second iteration
        low_results = [
            _make_search_result(1, "UU_1", score=0.1),
            _make_search_result(2, "UU_2", score=0.1),
        ]
        mock_retriever.hybrid_search.return_value = low_results

        agentic = AgenticRAG(crag=mock_crag)
        results = agentic.enhanced_search("Syarat PT", mock_retriever, top_k=5)

        # First iteration: direct search (low scores)
        # Second iteration: refine_query → CRAG (returns high scores, exits)
        mock_crag.enhanced_search.assert_called()
        assert results == crag_results

    def test_enhanced_search_empty_results_continues(self, mock_retriever):
        """Empty results from retriever don't crash the loop."""
        mock_retriever.hybrid_search.return_value = []

        agentic = AgenticRAG()
        results = agentic.enhanced_search("Syarat PT", mock_retriever)

        # Should iterate MAX_ITERATIONS times (empty results, avg_score=0)
        assert mock_retriever.hybrid_search.call_count == AgenticRAG.MAX_ITERATIONS
        assert results == []
