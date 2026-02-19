"""
Unit tests for backend.hyde.HyDE using mocked LLM and retriever.

Follows mocking patterns from tests/test_rag_chain.py (unittest.mock).
"""
from unittest.mock import Mock, MagicMock

import pytest

from backend.hyde import HyDE
from backend.retriever import SearchResult


@pytest.fixture
def mock_llm_client():
    m = Mock()
    m.generate.return_value = "Mocked hypothetical answer"
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


class TestHyDE:
    def test_generate_hypothetical_calls_llm(self, mock_llm_client):
        mock_llm_client.generate.return_value = "Hipotetikal mengenai PT"

        hyde = HyDE(mock_llm_client)
        question = "Syarat pendirian PT?"
        out = hyde.generate_hypothetical(question)

        assert out == "Hipotetikal mengenai PT"
        # Called once
        mock_llm_client.generate.assert_called_once()
        # Verify the question is present in the user_message argument
        call_kwargs = mock_llm_client.generate.call_args.kwargs
        assert "user_message" in call_kwargs
        assert question in call_kwargs["user_message"]

    def test_generate_hypothetical_fallback_on_exception(self, mock_llm_client):
        # Simulate LLM failure — HyDE should fall back to returning the original question
        mock_llm_client.generate.side_effect = Exception("LLM error")

        hyde = HyDE(mock_llm_client)
        question = "Apa itu PKWT?"
        out = hyde.generate_hypothetical(question)

        assert out == question

    def test_enhanced_search_rrf_merge(self, mock_llm_client, mock_retriever):
        # Setup LLM
        mock_llm_client.generate.return_value = "Hipotetikal jawaban"

        # Results for original question
        results_q = [
            _make_search_result(1, "UU_1", score=0.9),
            _make_search_result(2, "UU_2", score=0.8),
        ]

        # Results for hypothetical (overlap on UU_2)
        results_h = [
            _make_search_result(22, "UU_2", score=0.85),
            _make_search_result(3, "UU_3", score=0.7),
        ]

        # retriever.search called first for question, then for hypothetical
        mock_retriever.search.side_effect = [results_q, results_h]

        hyde = HyDE(mock_llm_client)
        merged = hyde.enhanced_search("Test question", mock_retriever, top_k=3)

        # Three unique citation_ids
        assert len(merged) == 3

        # Document that appears in both lists (UU_2) must rank highest by RRF score
        assert merged[0].citation_id == "UU_2"

        # Results should be sorted by descending score
        scores = [r.score for r in merged]
        assert scores == sorted(scores, reverse=True)

    def test_enhanced_search_handles_empty_results(self, mock_llm_client, mock_retriever):
        mock_llm_client.generate.return_value = "Hipotetikal"
        # Both searches return empty
        mock_retriever.search.return_value = []

        hyde = HyDE(mock_llm_client)
        res = hyde.enhanced_search("Pertanyaan kosong", mock_retriever)

        assert res == []

    def test_enhanced_search_deduplicates_same_citation(self, mock_llm_client, mock_retriever):
        mock_llm_client.generate.return_value = "Hipotetikal"

        # Same citation_id appears in multiple results (different ids)
        q_results = [
            _make_search_result(1, "DUPLICATE_ID", score=0.9),
            _make_search_result(2, "UU_2", score=0.8),
        ]
        h_results = [
            _make_search_result(3, "DUPLICATE_ID", score=0.85),
            _make_search_result(4, "UU_4", score=0.7),
        ]

        mock_retriever.search.side_effect = [q_results, h_results]

        hyde = HyDE(mock_llm_client)
        merged = hyde.enhanced_search("Dup test", mock_retriever, top_k=4)

        # DUPLICATE_ID should only appear once in merged results
        citation_ids = [r.citation_id for r in merged]
        assert citation_ids.count("DUPLICATE_ID") == 1
        # Total unique docs should be 3
        assert len(merged) == 3

    def test_enhanced_search_on_llm_failure_uses_fallback_question(self, mock_llm_client, mock_retriever):
        # LLM fails — HyDE.generate_hypothetical returns the original question
        mock_llm_client.generate.side_effect = Exception("LLM down")

        # Prepare retriever to return same results for both calls
        q_results = [
            _make_search_result(1, "UU_1", score=0.9),
            _make_search_result(2, "UU_2", score=0.8),
        ]
        # retriever.search will be called twice with same question (fallback)
        mock_retriever.search.side_effect = [q_results, q_results]

        hyde = HyDE(mock_llm_client)
        merged = hyde.enhanced_search("Fallback question", mock_retriever, top_k=2)

        # retriever.search called twice
        assert mock_retriever.search.call_count == 2

        # Deduplication should keep only unique citation_ids (2)
        assert len(merged) == 2
        ids = {r.citation_id for r in merged}
        assert ids == {"UU_1", "UU_2"}
