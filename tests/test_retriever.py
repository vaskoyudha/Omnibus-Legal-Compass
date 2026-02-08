"""
Tests for HybridRetriever - Indonesian Legal Document Search.

Tests hybrid search functionality combining dense (vector) and sparse (BM25) retrieval.
"""
import pytest
from backend.retriever import (
    HybridRetriever,
    SearchResult,
    tokenize_indonesian,
    get_retriever,
    COLLECTION_NAME,
    QDRANT_URL,
)


# --- Tokenizer Tests ---

class TestTokenizeIndonesian:
    """Tests for Indonesian text tokenizer."""
    
    def test_basic_tokenization(self):
        """Test basic word extraction."""
        text = "Undang-Undang Cipta Kerja"
        tokens = tokenize_indonesian(text)
        assert "undang" in tokens
        assert "cipta" in tokens
        assert "kerja" in tokens
    
    def test_stopword_removal(self):
        """Test that Indonesian stopwords are removed."""
        text = "yang di dalam untuk dengan pada"
        tokens = tokenize_indonesian(text)
        # All words should be filtered as stopwords
        assert len(tokens) == 0
    
    def test_preserves_legal_terms(self):
        """Test that legal terms are preserved."""
        text = "Pasal 1 ayat 2 tentang perizinan berusaha"
        tokens = tokenize_indonesian(text)
        assert "pasal" in tokens
        assert "ayat" in tokens
        assert "perizinan" in tokens
        assert "berusaha" in tokens
    
    def test_lowercase_conversion(self):
        """Test that output is lowercase."""
        text = "UNDANG-UNDANG NOMOR 11 TAHUN 2020"
        tokens = tokenize_indonesian(text)
        for token in tokens:
            assert token == token.lower()
    
    def test_empty_input(self):
        """Test handling of empty string."""
        assert tokenize_indonesian("") == []
    
    def test_numbers_preserved(self):
        """Test that numbers are preserved."""
        text = "Pasal 11 Tahun 2020"
        tokens = tokenize_indonesian(text)
        assert "11" in tokens
        assert "2020" in tokens


# --- SearchResult Tests ---

class TestSearchResult:
    """Tests for SearchResult dataclass."""
    
    def test_creation(self):
        """Test SearchResult creation."""
        result = SearchResult(
            id=1,
            text="Test text",
            citation="UU No. 11 Tahun 2020",
            citation_id="UU_11_2020",
            score=0.95,
            metadata={"jenis_dokumen": "UU"}
        )
        assert result.id == 1
        assert result.text == "Test text"
        assert result.citation == "UU No. 11 Tahun 2020"
        assert result.score == 0.95
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = SearchResult(
            id=1,
            text="Test",
            citation="Citation",
            citation_id="ID",
            score=0.5,
            metadata={"key": "value"}
        )
        d = result.to_dict()
        assert isinstance(d, dict)
        assert d["id"] == 1
        assert d["metadata"]["key"] == "value"


# --- HybridRetriever Integration Tests ---
# These require Qdrant to be running with data

@pytest.fixture
def retriever():
    """Create a retriever instance for testing."""
    try:
        return get_retriever()
    except Exception as e:
        pytest.skip(f"Qdrant not available: {e}")


class TestHybridRetrieverInit:
    """Tests for retriever initialization."""
    
    def test_initialization(self, retriever):
        """Test that retriever initializes correctly."""
        assert retriever is not None
        assert retriever.collection_name == COLLECTION_NAME
    
    def test_corpus_loaded(self, retriever):
        """Test that corpus is loaded for BM25."""
        stats = retriever.get_stats()
        assert stats["corpus_loaded"] > 0
        assert stats["bm25_initialized"] is True
    
    def test_get_stats(self, retriever):
        """Test statistics retrieval."""
        stats = retriever.get_stats()
        assert "collection_name" in stats
        assert "total_documents" in stats
        assert "corpus_loaded" in stats
        assert "bm25_initialized" in stats
        assert "embedding_model" in stats
        assert stats["total_documents"] == 10  # Our sample data


class TestDenseSearch:
    """Tests for dense (vector) search."""
    
    def test_dense_search_returns_results(self, retriever):
        """Test that dense search returns results."""
        query = "Undang-Undang Cipta Kerja"
        results = retriever.dense_search(query, top_k=3)
        assert len(results) > 0
        assert len(results) <= 3
    
    def test_dense_search_result_structure(self, retriever):
        """Test that results have correct structure."""
        results = retriever.dense_search("perizinan berusaha", top_k=1)
        if results:
            r = results[0]
            assert isinstance(r, SearchResult)
            assert r.text  # Not empty
            assert r.citation  # Not empty
            assert r.score > 0
    
    def test_dense_search_scores_sorted(self, retriever):
        """Test that results are sorted by score descending."""
        results = retriever.dense_search("investasi", top_k=5)
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i].score >= results[i + 1].score


class TestSparseSearch:
    """Tests for sparse (BM25) search."""
    
    def test_sparse_search_returns_results(self, retriever):
        """Test that BM25 search returns results."""
        query = "Cipta Kerja"
        results = retriever.sparse_search(query, top_k=3)
        assert len(results) > 0
    
    def test_sparse_search_keyword_match(self, retriever):
        """Test that BM25 finds keyword matches."""
        # Search for a term that should exist
        results = retriever.sparse_search("perizinan", top_k=5)
        # Should find documents containing "perizinan"
        assert len(results) > 0
        # At least one result should contain the keyword
        found_keyword = any("perizinan" in r.text.lower() for r in results)
        assert found_keyword
    
    def test_sparse_search_empty_query(self, retriever):
        """Test handling of query with only stopwords."""
        # All stopwords should result in empty tokens
        results = retriever.sparse_search("yang di dalam untuk", top_k=3)
        assert results == []


class TestHybridSearch:
    """Tests for hybrid search with RRF fusion."""
    
    def test_hybrid_search_basic(self, retriever):
        """Test basic hybrid search."""
        query = "Apa itu Undang-Undang Cipta Kerja?"
        results = retriever.hybrid_search(query, top_k=5)
        assert len(results) > 0
        assert len(results) <= 5
    
    def test_hybrid_search_indonesian_query(self, retriever):
        """Test with Indonesian natural language query."""
        queries = [
            "Apa itu Undang-Undang Cipta Kerja?",
            "Peraturan tentang investasi",
            "Perizinan berusaha melalui OSS",
        ]
        for query in queries:
            results = retriever.hybrid_search(query, top_k=3)
            assert len(results) > 0, f"No results for: {query}"
    
    def test_hybrid_search_has_citations(self, retriever):
        """Test that results include citations."""
        results = retriever.hybrid_search("Cipta Kerja", top_k=3)
        for r in results:
            assert r.citation, "Citation should not be empty"
            assert r.citation_id, "Citation ID should not be empty"
    
    def test_hybrid_search_rrf_scores(self, retriever):
        """Test that RRF scores are reasonable."""
        results = retriever.hybrid_search("perizinan berusaha", top_k=5)
        for r in results:
            # RRF scores are typically small positive numbers
            assert r.score > 0
            assert r.score < 1  # RRF scores don't exceed 1 with k=60


class TestFilteredSearch:
    """Tests for filtered search by document type."""
    
    def test_search_by_document_type(self, retriever):
        """Test filtering by jenis_dokumen."""
        # Search only UU documents
        results = retriever.search_by_document_type(
            query="Cipta Kerja",
            jenis_dokumen="UU",
            top_k=5
        )
        # All results should be UU type
        for r in results:
            assert r.metadata.get("jenis_dokumen") == "UU"
    
    def test_search_by_nonexistent_type(self, retriever):
        """Test filtering with type that doesn't exist."""
        results = retriever.search_by_document_type(
            query="test",
            jenis_dokumen="NONEXISTENT_TYPE",
            top_k=5
        )
        # Should return empty or only dense results (BM25 has no filter)
        # But with hybrid, if dense returns nothing, result may be sparse only
        assert isinstance(results, list)


class TestEdgeCases:
    """Edge case tests."""
    
    def test_very_long_query(self, retriever):
        """Test with a very long query."""
        long_query = "perizinan berusaha " * 50
        results = retriever.hybrid_search(long_query, top_k=3)
        # Should not crash and return results
        assert isinstance(results, list)
    
    def test_special_characters_query(self, retriever):
        """Test with special characters in query."""
        query = "Pasal 1 (ayat 2) - tentang [perizinan]"
        results = retriever.hybrid_search(query, top_k=3)
        # Should handle gracefully
        assert isinstance(results, list)
    
    def test_top_k_zero(self, retriever):
        """Test with top_k=0."""
        results = retriever.hybrid_search("test", top_k=0)
        assert results == []
    
    def test_result_serialization(self, retriever):
        """Test that results can be serialized to dict."""
        results = retriever.hybrid_search("Cipta Kerja", top_k=1)
        if results:
            d = results[0].to_dict()
            # Should be JSON-serializable
            import json
            json_str = json.dumps(d)
            assert isinstance(json_str, str)


# --- Quick Integration Check ---

def test_full_search_pipeline(retriever):
    """End-to-end test of search pipeline."""
    # 1. Check stats
    stats = retriever.get_stats()
    assert stats["total_documents"] == 10
    
    # 2. Run hybrid search
    query = "Undang-Undang Nomor 11 Tahun 2020 tentang Cipta Kerja"
    results = retriever.hybrid_search(query, top_k=5)
    
    # 3. Validate results
    assert len(results) > 0
    top_result = results[0]
    
    # 4. Check result quality - should find Cipta Kerja related content
    assert "cipta" in top_result.text.lower() or "kerja" in top_result.text.lower()
    
    print(f"\n=== Full Pipeline Test ===")
    print(f"Query: {query}")
    print(f"Top result: {top_result.citation}")
    print(f"Score: {top_result.score:.4f}")
    print(f"Preview: {top_result.text[:100]}...")
