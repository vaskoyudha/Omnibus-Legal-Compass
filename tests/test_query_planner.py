"""
Unit tests for backend.query_planner.QueryPlanner using mocked LLM and retriever.

Follows patterns from tests/test_hyde.py: use unittest.mock.Mock / MagicMock
"""
from unittest.mock import Mock, MagicMock

import pytest

from backend.query_planner import QueryPlanner
from backend.retriever import SearchResult


@pytest.fixture
def mock_llm_client():
    m = Mock()
    # Default generate returns empty string unless overridden in tests
    m.generate.return_value = ""
    return m


@pytest.fixture
def mock_retriever():
    return MagicMock()


def _make_search_result(i, citation_id, score=0.9, citation=None):
    if citation is None:
        citation = f"UU No. {i} Tahun 2020, Pasal {i}"
    return SearchResult(
        id=i,
        text=f"Dokumen {i} tentang hukum Indonesia",
        citation=citation,
        citation_id=citation_id,
        score=score,
        metadata={"jenis_dokumen": "UU", "tahun": 2020},
    )


class TestQueryPlanner:
    def test_should_decompose_simple_questions(self):
        planner = QueryPlanner(Mock())

        assert planner.should_decompose("Apa itu PT?") is False
        assert planner.should_decompose("Definisi perusahaan") is False
        assert planner.should_decompose("Syarat pendirian PT") is False

    def test_should_decompose_complex_questions(self):
        planner = QueryPlanner(Mock())

        assert planner.should_decompose("Perbedaan PT dan CV") is True
        assert planner.should_decompose("Syarat PT serta persyaratan CV") is True
        assert planner.should_decompose("PT dibandingkan dengan CV") is True

    def test_decompose_parses_numbered_output(self, mock_llm_client):
        mock_llm_client.generate.return_value = (
            "1. Apa perbedaan PT dan CV?\n"
            "2. Bagaimana cara mendirikan PT?\n"
            "3. Bagaimana cara mendirikan CV?"
        )

        planner = QueryPlanner(mock_llm_client)
        subs = planner.decompose("Perbedaan PT dan CV dan cara mendirikannya")

        assert len(subs) == 3
        assert "perbedaan pt dan cv" in subs[0].lower()
        assert "mendirikan pt" in subs[1].lower()

    def test_decompose_parses_bulleted_and_mixed_output(self, mock_llm_client):
        # Bulleted
        mock_llm_client.generate.return_value = (
            "- Apa perbedaan PT dan CV?\n"
            "- Syarat pendirian PT\n"
            "- Syarat pendirian CV"
        )

        planner = QueryPlanner(mock_llm_client)
        subs = planner.decompose("Perbedaan PT dan syarat pendirian")

        assert len(subs) == 3
        assert any("perbedaan pt dan cv" in s.lower() for s in subs)

        # Mixed formatting
        mock_llm_client.generate.return_value = (
            "Sub-pertanyaan:\n1) Apa perbedaan PT dan CV?\n- Bagaimana mendirikan PT?\nPlain line without marker"
        )

        subs2 = planner.decompose("Mixed formatting question")
        # Should extract three meaningful lines (ignoring header)
        assert len(subs2) >= 2

    def test_decompose_empty_llm_response(self, mock_llm_client):
        mock_llm_client.generate.return_value = ""

        planner = QueryPlanner(mock_llm_client)
        subs = planner.decompose("Pertanyaan apa")

        assert subs == []

    def test_multi_hop_search_simple_question(self, mock_llm_client, mock_retriever):
        # Simple question should not call LLM.generate
        planner = QueryPlanner(mock_llm_client)

        # Mock retriever.search return
        mock_retriever.hybrid_search.return_value = [
            _make_search_result(1, "UU_1", score=0.9),
            _make_search_result(2, "UU_2", score=0.8),
        ]

        res = planner.multi_hop_search("Apa itu PT?", mock_retriever, top_k=5)

        mock_retriever.hybrid_search.assert_called_once()
        mock_llm_client.generate.assert_not_called()
        assert isinstance(res, list)

    def test_multi_hop_search_complex_question_rrf(self, mock_llm_client, mock_retriever):
        # LLM returns two sub-questions
        mock_llm_client.generate.return_value = "1. Sub-kesatu\n2. Sub-kedua"

        # Prepare retriever search results for each sub-query
        results_1 = [
            _make_search_result(1, "UU_1", score=0.9),
            _make_search_result(2, "UU_2", score=0.8),
        ]
        results_2 = [
            _make_search_result(22, "UU_2", score=0.85),  # overlap on UU_2
            _make_search_result(3, "UU_3", score=0.7),
        ]

        mock_retriever.hybrid_search.side_effect = [results_1, results_2]

        planner = QueryPlanner(mock_llm_client)
        merged = planner.multi_hop_search("Perbedaan PT dan CV", mock_retriever, top_k=5)

        # Should call retriever.search twice (one per sub-question)
        assert mock_retriever.hybrid_search.call_count == 2

        # Merged results should include UU_2 (appears twice) and rank it highest
        citation_ids = [r.citation_id for r in merged]
        assert "UU_2" in citation_ids
        assert merged[0].citation_id == "UU_2"

        # Unique count should be 3
        assert len(merged) == 3

    def test_multi_hop_search_handles_empty_subsearches_and_llm_failure(self, mock_llm_client, mock_retriever):
        # LLM throws exception → decompose returns [] and fallback to regular search
        mock_llm_client.generate.side_effect = Exception("LLM down")

        # retriever.search for fallback
        mock_retriever.hybrid_search.return_value = [
            _make_search_result(1, "UU_1", score=0.9),
        ]

        planner = QueryPlanner(mock_llm_client)
        res = planner.multi_hop_search("Perbedaan PT dan CV", mock_retriever, top_k=5)

        # retriever.search should be called at least once for fallback
        mock_retriever.hybrid_search.assert_called()
        assert res == mock_retriever.hybrid_search.return_value

    def test_multi_hop_search_parsing_failure_empty_results(self, mock_llm_client, mock_retriever):
        # LLM returns sub-questions but retriever returns empty lists for each
        mock_llm_client.generate.return_value = "1. A\n2. B"
        mock_retriever.hybrid_search.side_effect = [[], []]

        planner = QueryPlanner(mock_llm_client)
        res = planner.multi_hop_search("Perbedaan PT dan CV", mock_retriever, top_k=5)

        # When all sub-searches return no results, planner falls back to regular search
        # Because retriever.search was set to side_effect for sub-queries, the fallback will call search again
        assert mock_retriever.hybrid_search.call_count >= 2
        # Result should be whatever retriever.search returns on fallback; since side_effect exhausted, subsequent calls return the last value
        assert isinstance(res, list)
