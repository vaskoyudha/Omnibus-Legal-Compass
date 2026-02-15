"""
Unit tests for HybridRetriever — all external dependencies mocked.

Covers: __init__, _load_corpus, expand_query, dense_search, sparse_search,
_rrf_fusion, _rerank, hybrid_search, search_by_document_type, get_stats.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import numpy as np

from retriever import (
    HybridRetriever,
    SearchResult,
    tokenize_indonesian,
    get_retriever,
    COLLECTION_NAME,
    RRF_K,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sr(doc_id: int, score: float = 0.5, text: str = "text") -> SearchResult:
    """Shortcut to create a SearchResult."""
    return SearchResult(
        id=doc_id,
        text=text,
        citation=f"UU No. {doc_id}",
        citation_id=f"uu-{doc_id}",
        score=score,
        metadata={"jenis_dokumen": "UU"},
    )


@pytest.fixture
def retriever():
    """Create a HybridRetriever with all external deps mocked."""
    with (
        patch("retriever.QdrantClient") as mock_qclient_cls,
        patch("retriever.HuggingFaceEmbeddings") as mock_embeddings_cls,
    ):
        # Mock the Qdrant collection info for _load_corpus
        mock_client = MagicMock()
        mock_collection_info = MagicMock()
        mock_collection_info.points_count = 0  # Empty corpus → skip BM25
        mock_client.get_collection.return_value = mock_collection_info
        mock_qclient_cls.return_value = mock_client

        mock_embedder = MagicMock()
        mock_embedder.embed_query.return_value = [0.1] * 384
        mock_embeddings_cls.return_value = mock_embedder

        ret = HybridRetriever(use_reranker=False)
        ret.client = mock_client
        ret.embedder = mock_embedder
        yield ret


@pytest.fixture
def retriever_with_corpus():
    """Retriever with a small in-memory corpus + BM25."""
    with (
        patch("retriever.QdrantClient") as mock_qclient_cls,
        patch("retriever.HuggingFaceEmbeddings") as mock_embeddings_cls,
    ):
        mock_client = MagicMock()

        # Simulate 3 documents in Qdrant for _load_corpus
        mock_collection_info = MagicMock()
        mock_collection_info.points_count = 3
        mock_client.get_collection.return_value = mock_collection_info

        # Simulate scroll returning 3 records
        records = []
        docs = [
            {"id": 1, "text": "Undang-Undang Cipta Kerja nomor 11 tahun 2020", "citation": "UU 11/2020", "citation_id": "uu-11-2020", "jenis_dokumen": "UU"},
            {"id": 2, "text": "Peraturan Pemerintah tentang perizinan berusaha", "citation": "PP 5/2021", "citation_id": "pp-5-2021", "jenis_dokumen": "PP"},
            {"id": 3, "text": "Perpres investasi dan penanaman modal asing", "citation": "Perpres 10/2021", "citation_id": "perpres-10-2021", "jenis_dokumen": "Perpres"},
        ]
        for doc in docs:
            r = MagicMock()
            r.id = doc["id"]
            r.payload = doc
            records.append(r)
        mock_client.scroll.return_value = (records, None)

        mock_qclient_cls.return_value = mock_client

        mock_embedder = MagicMock()
        mock_embedder.embed_query.return_value = [0.1] * 384
        mock_embeddings_cls.return_value = mock_embedder

        ret = HybridRetriever(use_reranker=False)
        ret.client = mock_client
        ret.embedder = mock_embedder
        yield ret


# ---------------------------------------------------------------------------
# _load_corpus tests
# ---------------------------------------------------------------------------


class TestLoadCorpus:
    def test_empty_collection_loads_nothing(self, retriever):
        assert retriever._corpus == []
        assert retriever._bm25 is None

    def test_corpus_loaded_with_documents(self, retriever_with_corpus):
        assert len(retriever_with_corpus._corpus) == 3
        assert retriever_with_corpus._bm25 is not None

    def test_corpus_skips_records_with_no_payload(self):
        """Records where payload is None should be skipped."""
        with (
            patch("retriever.QdrantClient") as mock_qclient_cls,
            patch("retriever.HuggingFaceEmbeddings") as mock_embeddings_cls,
        ):
            mock_client = MagicMock()
            mock_info = MagicMock()
            mock_info.points_count = 2
            mock_client.get_collection.return_value = mock_info

            r1 = MagicMock()
            r1.id = 1
            r1.payload = None  # Should be skipped

            r2 = MagicMock()
            r2.id = 2
            r2.payload = {"text": "test doc", "citation": "C", "citation_id": "c-1"}

            mock_client.scroll.return_value = ([r1, r2], None)
            mock_qclient_cls.return_value = mock_client
            mock_embeddings_cls.return_value = MagicMock()

            ret = HybridRetriever(use_reranker=False)
            assert len(ret._corpus) == 1


# ---------------------------------------------------------------------------
# expand_query tests
# ---------------------------------------------------------------------------


class TestExpandQuery:
    def test_no_synonyms_returns_original_only(self, retriever):
        queries = retriever.expand_query("random unmatched query")
        assert queries == ["random unmatched query"]

    def test_synonym_expansion_pt(self, retriever):
        queries = retriever.expand_query("Cara mendirikan PT di Indonesia")
        assert len(queries) >= 2
        # Should contain a variant with "Perseroan Terbatas" or "perusahaan"
        combined = " ".join(queries)
        assert "Perseroan Terbatas" in combined or "perusahaan" in combined

    def test_max_three_variants(self, retriever):
        # A query with many synonym matches should still cap at 3
        queries = retriever.expand_query("PT memerlukan NIB dan NPWP serta SIUP untuk pajak karyawan")
        assert len(queries) <= 3

    def test_nib_expansion(self, retriever):
        queries = retriever.expand_query("Bagaimana cara mendapatkan NIB?")
        combined = " ".join(queries)
        assert "Nomor Induk Berusaha" in combined or "izin berusaha" in combined


# ---------------------------------------------------------------------------
# _rrf_fusion tests
# ---------------------------------------------------------------------------


class TestRRFFusion:
    def test_basic_fusion_both_lists(self, retriever):
        dense = [_sr(1, 0.9), _sr(2, 0.8)]
        sparse = [_sr(2, 5.0), _sr(3, 4.0)]

        fused = retriever._rrf_fusion(dense, sparse)
        # doc 2 appears in both → highest RRF score
        ids = [r.id for r, _ in fused]
        assert ids[0] == 2  # doc 2 should be ranked first (appears in both)

    def test_single_list_dense(self, retriever):
        dense = [_sr(1), _sr(2)]
        fused = retriever._rrf_fusion(dense, [])
        assert len(fused) == 2

    def test_single_list_sparse(self, retriever):
        fused = retriever._rrf_fusion([], [_sr(3)])
        assert len(fused) == 1
        assert fused[0][0].id == 3

    def test_empty_inputs(self, retriever):
        fused = retriever._rrf_fusion([], [])
        assert fused == []

    def test_rrf_score_values(self, retriever):
        dense = [_sr(1)]
        sparse = [_sr(1)]
        fused = retriever._rrf_fusion(dense, sparse)
        # Both rank 1 → score = 2 * 1/(60+1)
        expected = 2 * (1 / (RRF_K + 1))
        assert abs(fused[0][1] - expected) < 1e-10


# ---------------------------------------------------------------------------
# _rerank tests
# ---------------------------------------------------------------------------


class TestRerank:
    def test_no_reranker_returns_truncated(self, retriever):
        results = [_sr(1), _sr(2), _sr(3)]
        reranked = retriever._rerank("query", results, top_k=2)
        assert len(reranked) == 2
        # Without reranker, just truncate
        assert reranked[0].id == 1
        assert reranked[1].id == 2

    def test_empty_results(self, retriever):
        reranked = retriever._rerank("query", [], top_k=5)
        assert reranked == []

    def test_reranker_reorders_by_ce_score(self, retriever):
        # Set up a mock reranker
        mock_reranker = MagicMock()
        mock_reranker.predict.return_value = [1.0, 5.0, 3.0]  # doc2 highest
        retriever.reranker = mock_reranker

        results = [_sr(1, text="aaa"), _sr(2, text="bbb"), _sr(3, text="ccc")]
        reranked = retriever._rerank("query", results, top_k=2)
        assert len(reranked) == 2
        assert reranked[0].id == 2  # Highest CE score
        assert reranked[1].id == 3

    def test_reranker_normalizes_scores(self, retriever):
        mock_reranker = MagicMock()
        mock_reranker.predict.return_value = [3.0]
        retriever.reranker = mock_reranker

        results = [_sr(1, text="test")]
        reranked = retriever._rerank("query", results, top_k=1)
        # CE score 3.0 → normalized (3+5)/10 = 0.8
        assert abs(reranked[0].score - 0.8) < 1e-6

    def test_reranker_exception_falls_back(self, retriever):
        mock_reranker = MagicMock()
        mock_reranker.predict.side_effect = RuntimeError("model error")
        retriever.reranker = mock_reranker

        results = [_sr(1), _sr(2)]
        reranked = retriever._rerank("query", results, top_k=2)
        # Should return original order
        assert len(reranked) == 2
        assert reranked[0].id == 1


# ---------------------------------------------------------------------------
# sparse_search tests
# ---------------------------------------------------------------------------


class TestSparseSearch:
    def test_no_bm25_returns_empty(self, retriever):
        results = retriever.sparse_search("test query")
        assert results == []

    def test_bm25_search(self, retriever_with_corpus):
        results = retriever_with_corpus.sparse_search("cipta kerja", top_k=2)
        assert len(results) > 0
        # First doc has "cipta kerja" in text
        assert any(r.id == 1 for r in results)

    def test_stopword_only_query(self, retriever_with_corpus):
        results = retriever_with_corpus.sparse_search("yang di dalam untuk", top_k=3)
        assert results == []


# ---------------------------------------------------------------------------
# dense_search tests
# ---------------------------------------------------------------------------


class TestDenseSearch:
    def test_basic_dense_search(self, retriever):
        # Mock query_points response
        mock_hit = MagicMock()
        mock_hit.id = 1
        mock_hit.score = 0.92
        mock_hit.payload = {
            "text": "Undang-Undang Cipta Kerja",
            "citation": "UU 11/2020",
            "citation_id": "uu-11",
            "jenis_dokumen": "UU",
        }
        mock_response = MagicMock()
        mock_response.points = [mock_hit]
        retriever.client.query_points.return_value = mock_response

        results = retriever.dense_search("cipta kerja", top_k=5)
        assert len(results) == 1
        assert results[0].id == 1
        assert results[0].score == 0.92
        assert results[0].metadata["jenis_dokumen"] == "UU"

    def test_dense_search_with_filter(self, retriever):
        mock_response = MagicMock()
        mock_response.points = []
        retriever.client.query_points.return_value = mock_response

        results = retriever.dense_search(
            "test", top_k=5, filter_conditions={"jenis_dokumen": "UU"}
        )
        # Should pass filter through
        call_kwargs = retriever.client.query_points.call_args
        assert call_kwargs.kwargs.get("query_filter") is not None

    def test_dense_search_skips_null_payload(self, retriever):
        mock_hit = MagicMock()
        mock_hit.id = 1
        mock_hit.score = 0.9
        mock_hit.payload = None

        mock_response = MagicMock()
        mock_response.points = [mock_hit]
        retriever.client.query_points.return_value = mock_response

        results = retriever.dense_search("test")
        assert results == []


# ---------------------------------------------------------------------------
# hybrid_search tests
# ---------------------------------------------------------------------------


class TestHybridSearch:
    def test_delegates_to_dense_and_sparse(self, retriever):
        with (
            patch.object(retriever, "dense_search", return_value=[_sr(1, 0.9)]) as mock_dense,
            patch.object(retriever, "sparse_search", return_value=[_sr(2, 3.0)]) as mock_sparse,
        ):
            results = retriever.hybrid_search("test", top_k=2, expand_queries=False)
            mock_dense.assert_called()
            mock_sparse.assert_called()
            assert len(results) <= 2

    def test_with_query_expansion(self, retriever):
        with (
            patch.object(retriever, "expand_query", return_value=["test", "test synonym"]),
            patch.object(retriever, "dense_search", return_value=[_sr(1, 0.9)]),
            patch.object(retriever, "sparse_search", return_value=[]),
        ):
            results = retriever.hybrid_search("test", top_k=2, expand_queries=True)
            # expand_query should be called, and then searches run for each variant
            retriever.expand_query.assert_called_once_with("test")

    def test_without_query_expansion(self, retriever):
        with (
            patch.object(retriever, "dense_search", return_value=[_sr(1)]),
            patch.object(retriever, "sparse_search", return_value=[]),
        ):
            results = retriever.hybrid_search("test", top_k=2, expand_queries=False)
            assert len(results) <= 2

    def test_reranking_path(self, retriever):
        retriever.reranker = MagicMock()
        retriever.reranker.predict.return_value = [0.5, 0.9]

        with (
            patch.object(retriever, "dense_search", return_value=[_sr(1, 0.8), _sr(2, 0.7)]),
            patch.object(retriever, "sparse_search", return_value=[]),
        ):
            results = retriever.hybrid_search(
                "test", top_k=2, use_reranking=True, expand_queries=False
            )
            assert len(results) <= 2

    def test_deduplication(self, retriever):
        """Same doc ID from multiple query variants should be deduplicated."""
        with (
            patch.object(retriever, "expand_query", return_value=["q1", "q2"]),
            patch.object(retriever, "dense_search", return_value=[_sr(1, 0.9)]),
            patch.object(retriever, "sparse_search", return_value=[_sr(1, 5.0)]),
        ):
            results = retriever.hybrid_search("test", top_k=5, expand_queries=True)
            # Doc 1 appears in both dense and sparse for 2 variants,
            # but should only appear once in results
            ids = [r.id for r in results]
            assert ids.count(1) == 1


# ---------------------------------------------------------------------------
# search_by_document_type tests
# ---------------------------------------------------------------------------


class TestSearchByDocumentType:
    def test_delegates_to_hybrid_search(self, retriever):
        with patch.object(retriever, "hybrid_search", return_value=[_sr(1)]) as mock_hs:
            results = retriever.search_by_document_type("test", "UU", top_k=3)
            mock_hs.assert_called_once_with(
                query="test",
                top_k=3,
                filter_conditions={"jenis_dokumen": "UU"},
            )
            assert len(results) == 1


# ---------------------------------------------------------------------------
# get_stats tests
# ---------------------------------------------------------------------------


class TestGetStats:
    def test_returns_stats_dict(self, retriever):
        mock_info = MagicMock()
        mock_info.points_count = 100
        retriever.client.get_collection.return_value = mock_info

        stats = retriever.get_stats()
        assert stats["collection_name"] == COLLECTION_NAME
        assert stats["total_documents"] == 100
        assert stats["corpus_loaded"] == 0
        assert stats["bm25_initialized"] is False


# ---------------------------------------------------------------------------
# __init__ edge cases
# ---------------------------------------------------------------------------


class TestRetrieverInit:
    def test_init_with_api_key(self):
        with (
            patch("retriever.QdrantClient") as mock_qclient_cls,
            patch("retriever.HuggingFaceEmbeddings"),
        ):
            mock_client = MagicMock()
            mock_info = MagicMock()
            mock_info.points_count = 0
            mock_client.get_collection.return_value = mock_info
            mock_qclient_cls.return_value = mock_client

            ret = HybridRetriever(
                qdrant_api_key="test-key", use_reranker=False  # pragma: allowlist secret
            )
            # Should have called QdrantClient with api_key
            mock_qclient_cls.assert_called_with(
                url=ret.qdrant_url, api_key="test-key", timeout=10  # pragma: allowlist secret
            )

    def test_init_without_api_key(self):
        with (
            patch("retriever.QdrantClient") as mock_qclient_cls,
            patch("retriever.HuggingFaceEmbeddings"),
        ):
            mock_client = MagicMock()
            mock_info = MagicMock()
            mock_info.points_count = 0
            mock_client.get_collection.return_value = mock_info
            mock_qclient_cls.return_value = mock_client

            ret = HybridRetriever(
                qdrant_api_key=None, use_reranker=False
            )
            mock_qclient_cls.assert_called_with(url=ret.qdrant_url, timeout=10)

    def test_init_with_reranker_failure(self):
        """CrossEncoder import failure should not crash init."""
        with (
            patch("retriever.QdrantClient") as mock_qclient_cls,
            patch("retriever.HuggingFaceEmbeddings"),
        ):
            mock_client = MagicMock()
            mock_info = MagicMock()
            mock_info.points_count = 0
            mock_client.get_collection.return_value = mock_info
            mock_qclient_cls.return_value = mock_client

            with patch(
                "retriever.HybridRetriever.__init__.__module__",
                create=True,
            ):
                # Simulate CrossEncoder import working but init failing
                with patch.dict("sys.modules", {"sentence_transformers": MagicMock()}):
                    with patch("sentence_transformers.CrossEncoder", side_effect=RuntimeError("model fail")):
                        ret = HybridRetriever(use_reranker=True)
                        assert ret.reranker is None
