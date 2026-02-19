"""
Unit tests for backend.parent_child.ParentChildRetriever using mocked retriever.

Follows mocking patterns from tests/test_hyde.py (unittest.mock).
"""
from unittest.mock import Mock, MagicMock

import pytest

from backend.parent_child import ParentChildRetriever
from backend.retriever import SearchResult


@pytest.fixture
def mock_retriever():
    return MagicMock()


def _make_search_result(i, citation_id, score=0.9, citation=None, metadata=None):
    """Helper to build SearchResult objects with optional custom metadata."""
    if citation is None:
        citation = f"UU No. {i} Tahun 2020, Pasal {i}"
    if metadata is None:
        metadata = {
            "jenis_dokumen": "UU",
            "tahun": 2020,
            "parent_citation_id": f"UU_40_2007_Pasal_{i}",
        }
    return SearchResult(
        id=i,
        text=f"Child chunk {i} tentang hukum Indonesia",
        citation=citation,
        citation_id=citation_id,
        score=score,
        metadata=metadata,
    )


class TestParentChildRetriever:
    def test_maps_children_to_parent_text(self, mock_retriever):
        """Verify parent text appears in results instead of child text."""
        parent_store = {
            "UU_40_2007_Pasal_1": "Full text of Pasal 1 from UU 40/2007 with all ayat.",
            "UU_40_2007_Pasal_2": "Full text of Pasal 2 from UU 40/2007 with all ayat.",
        }

        children = [
            _make_search_result(1, "UU_1", score=0.95, metadata={
                "jenis_dokumen": "UU", "tahun": 2007,
                "parent_citation_id": "UU_40_2007_Pasal_1",
            }),
            _make_search_result(2, "UU_2", score=0.85, metadata={
                "jenis_dokumen": "UU", "tahun": 2007,
                "parent_citation_id": "UU_40_2007_Pasal_2",
            }),
        ]
        mock_retriever.hybrid_search.return_value = children

        pcr = ParentChildRetriever(parent_store=parent_store)
        results = pcr.enhanced_search("Apa syarat pendirian PT?", mock_retriever, top_k=5)

        assert len(results) == 2
        # Parent text should replace child text
        assert results[0].text == "Full text of Pasal 1 from UU 40/2007 with all ayat."
        assert results[1].text == "Full text of Pasal 2 from UU 40/2007 with all ayat."
        # Child citation and score preserved
        assert results[0].citation == children[0].citation
        assert results[0].score == children[0].score
        assert results[1].citation == children[1].citation

    def test_deduplication_same_parent(self, mock_retriever):
        """Two children pointing to same parent_id produce only one result."""
        parent_store = {
            "UU_40_2007_Pasal_1": "Full text of Pasal 1.",
        }

        children = [
            _make_search_result(1, "UU_1_chunk_a", score=0.95, metadata={
                "jenis_dokumen": "UU", "tahun": 2007,
                "parent_citation_id": "UU_40_2007_Pasal_1",
            }),
            _make_search_result(2, "UU_1_chunk_b", score=0.85, metadata={
                "jenis_dokumen": "UU", "tahun": 2007,
                "parent_citation_id": "UU_40_2007_Pasal_1",
            }),
            _make_search_result(3, "UU_2", score=0.75, metadata={
                "jenis_dokumen": "UU", "tahun": 2007,
                "parent_citation_id": "UU_40_2007_Pasal_2",
            }),
        ]
        mock_retriever.hybrid_search.return_value = children

        pcr = ParentChildRetriever(parent_store=parent_store)
        results = pcr.enhanced_search("Test dedup", mock_retriever, top_k=5)

        # Only one result for UU_40_2007_Pasal_1 (deduped), Pasal_2 not in store → skipped
        assert len(results) == 1
        assert results[0].text == "Full text of Pasal 1."
        # Should use the first child's citation (highest score)
        assert results[0].citation_id == "UU_1_chunk_a"

    def test_top_k_respected(self, mock_retriever):
        """More parents available than top_k → results truncated to top_k."""
        parent_store = {
            f"UU_40_2007_Pasal_{i}": f"Full text of Pasal {i}."
            for i in range(1, 11)
        }

        children = [
            _make_search_result(i, f"UU_{i}", score=0.9 - i * 0.01, metadata={
                "jenis_dokumen": "UU", "tahun": 2007,
                "parent_citation_id": f"UU_40_2007_Pasal_{i}",
            })
            for i in range(1, 11)
        ]
        mock_retriever.hybrid_search.return_value = children

        pcr = ParentChildRetriever(parent_store=parent_store)
        results = pcr.enhanced_search("Test top_k", mock_retriever, top_k=3)

        assert len(results) == 3
        # hybrid_search should be called with 2x top_k
        mock_retriever.hybrid_search.assert_called_once_with("Test top_k", top_k=6)

    def test_missing_parent_in_store_fallback(self, mock_retriever):
        """Child has parent_id but it's not in store → falls back to children."""
        parent_store = {
            "UU_NONEXISTENT": "This parent is never referenced.",
        }

        children = [
            _make_search_result(1, "UU_1", score=0.9, metadata={
                "jenis_dokumen": "UU", "tahun": 2007,
                "parent_citation_id": "UU_40_2007_Pasal_99",  # Not in store
            }),
            _make_search_result(2, "UU_2", score=0.8, metadata={
                "jenis_dokumen": "UU", "tahun": 2007,
                "parent_citation_id": "UU_40_2007_Pasal_100",  # Not in store
            }),
        ]
        mock_retriever.hybrid_search.return_value = children

        pcr = ParentChildRetriever(parent_store=parent_store)
        results = pcr.enhanced_search("Test missing parent", mock_retriever, top_k=5)

        # Fallback: returns child results since no parents were found
        assert len(results) == 2
        assert results[0].text == children[0].text
        assert results[1].text == children[1].text

    def test_empty_parent_store_returns_children(self, mock_retriever):
        """Empty parent_store dict → returns child results directly."""
        children = [
            _make_search_result(1, "UU_1", score=0.9),
            _make_search_result(2, "UU_2", score=0.8),
        ]
        mock_retriever.hybrid_search.return_value = children

        pcr = ParentChildRetriever(parent_store={})
        results = pcr.enhanced_search("Test empty store", mock_retriever, top_k=5)

        assert len(results) == 2
        assert results[0].text == children[0].text
        assert results[1].text == children[1].text

    def test_none_parent_store_returns_children(self, mock_retriever):
        """None parent_store → returns child results directly."""
        children = [
            _make_search_result(1, "UU_1", score=0.9),
            _make_search_result(2, "UU_2", score=0.8),
        ]
        mock_retriever.hybrid_search.return_value = children

        pcr = ParentChildRetriever(parent_store=None)
        results = pcr.enhanced_search("Test None store", mock_retriever, top_k=5)

        assert len(results) == 2
        assert results[0].text == children[0].text
        assert results[1].text == children[1].text

    def test_no_parent_citation_id_in_metadata(self, mock_retriever):
        """Children lack parent_citation_id key → falls back to children."""
        parent_store = {
            "UU_40_2007_Pasal_1": "Full text of Pasal 1.",
        }

        # Metadata without parent_citation_id
        children = [
            _make_search_result(1, "UU_1", score=0.9, metadata={
                "jenis_dokumen": "UU", "tahun": 2007,
            }),
            _make_search_result(2, "UU_2", score=0.8, metadata={
                "jenis_dokumen": "UU", "tahun": 2007,
            }),
        ]
        mock_retriever.hybrid_search.return_value = children

        pcr = ParentChildRetriever(parent_store=parent_store)
        results = pcr.enhanced_search("Test no parent_citation_id", mock_retriever, top_k=5)

        # Fallback: returns child results since no parent_citation_id found
        assert len(results) == 2
        assert results[0].text == children[0].text
        assert results[1].text == children[1].text

    def test_hybrid_search_called_with_double_top_k(self, mock_retriever):
        """Verify retriever.hybrid_search is called with top_k * 2."""
        parent_store = {
            "UU_40_2007_Pasal_1": "Full text of Pasal 1.",
        }

        children = [
            _make_search_result(1, "UU_1", score=0.9, metadata={
                "jenis_dokumen": "UU", "tahun": 2007,
                "parent_citation_id": "UU_40_2007_Pasal_1",
            }),
        ]
        mock_retriever.hybrid_search.return_value = children

        pcr = ParentChildRetriever(parent_store=parent_store)
        pcr.enhanced_search("Test call", mock_retriever, top_k=7)

        mock_retriever.hybrid_search.assert_called_once_with("Test call", top_k=14)

    def test_mixed_children_some_with_parents_some_without(self, mock_retriever):
        """Mix of children with and without parent mappings → only mapped ones expanded."""
        parent_store = {
            "UU_40_2007_Pasal_1": "Full text of Pasal 1.",
        }

        children = [
            # This child has a valid parent_citation_id in the store
            _make_search_result(1, "UU_1", score=0.95, metadata={
                "jenis_dokumen": "UU", "tahun": 2007,
                "parent_citation_id": "UU_40_2007_Pasal_1",
            }),
            # This child has no parent_citation_id
            _make_search_result(2, "UU_2", score=0.85, metadata={
                "jenis_dokumen": "UU", "tahun": 2007,
            }),
            # This child has parent_citation_id but not in store
            _make_search_result(3, "UU_3", score=0.75, metadata={
                "jenis_dokumen": "UU", "tahun": 2007,
                "parent_citation_id": "UU_40_2007_Pasal_99",
            }),
        ]
        mock_retriever.hybrid_search.return_value = children

        pcr = ParentChildRetriever(parent_store=parent_store)
        results = pcr.enhanced_search("Test mixed", mock_retriever, top_k=5)

        # Only one child successfully mapped to parent
        assert len(results) == 1
        assert results[0].text == "Full text of Pasal 1."
        assert results[0].citation_id == "UU_1"
