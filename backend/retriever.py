"""
Hybrid Search Retriever for Indonesian Legal Documents.

Combines dense vector search (HuggingFace embeddings via Qdrant) with
sparse BM25 retrieval for optimal recall on Bahasa Indonesia legal text.

Uses Reciprocal Rank Fusion (RRF) to merge results:
    score = sum(1 / (k + rank)) where k=60 (standard constant)
"""
from typing import Any
from dataclasses import dataclass
import logging

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from langchain_huggingface import HuggingFaceEmbeddings
from rank_bm25 import BM25Okapi

# Configure logging
logger = logging.getLogger(__name__)

# Constants - must match ingest.py
COLLECTION_NAME = "indonesian_legal_docs"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384
QDRANT_URL = "http://localhost:6333"
RRF_K = 60  # Standard RRF constant
RERANKER_MODEL = "jeffwan/mmarco-mMiniLMv2-L12-H384-v1"  # Multilingual cross-encoder


@dataclass
class SearchResult:
    """Single search result with score and metadata."""
    id: int
    text: str
    citation: str
    citation_id: str
    score: float
    metadata: dict[str, Any]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "text": self.text,
            "citation": self.citation,
            "citation_id": self.citation_id,
            "score": self.score,
            "metadata": self.metadata,
        }


def tokenize_indonesian(text: str) -> list[str]:
    """
    Simple tokenizer for Indonesian text.
    
    Handles basic preprocessing:
    - Lowercase
    - Split on whitespace and punctuation
    - Remove common Indonesian stopwords (minimal set)
    
    For production, consider using Sastrawi or similar.
    """
    import re
    
    # Lowercase and extract words
    text = text.lower()
    tokens = re.findall(r'\b[a-zA-Z0-9]+\b', text)
    
    # Minimal Indonesian stopwords (keep legal terms!)
    stopwords = {
        "dan", "atau", "yang", "di", "ke", "dari", "untuk",
        "dengan", "pada", "ini", "itu", "adalah", "sebagai",
        "dalam", "oleh", "tidak", "akan", "dapat", "telah",
        "tersebut", "bahwa", "jika", "maka", "atas", "setiap",
    }
    
    return [t for t in tokens if t not in stopwords and len(t) > 1]


class HybridRetriever:
    """
    Hybrid retriever combining dense vector search with BM25 sparse retrieval.
    
    Usage:
        retriever = HybridRetriever()
        results = retriever.hybrid_search("Apa itu Undang-Undang Cipta Kerja?", top_k=5)
    """
    
    def __init__(
        self,
        qdrant_url: str = QDRANT_URL,
        collection_name: str = COLLECTION_NAME,
        embedding_model: str = EMBEDDING_MODEL,
        use_reranker: bool = True,
    ):
        """
        Initialize the hybrid retriever.
        
        Args:
            qdrant_url: Qdrant server URL
            collection_name: Name of the Qdrant collection
            embedding_model: HuggingFace model for embeddings
            use_reranker: Whether to use CrossEncoder for re-ranking
        """
        self.collection_name = collection_name
        self.qdrant_url = qdrant_url
        self.use_reranker = use_reranker
        
        # Initialize Qdrant client
        self.client = QdrantClient(url=qdrant_url)
        
        # Initialize embeddings (same model as ingestion)
        self.embedder = HuggingFaceEmbeddings(model_name=embedding_model)
        
        # Initialize CrossEncoder for re-ranking (optional but recommended)
        self.reranker = None
        if use_reranker:
            try:
                from sentence_transformers import CrossEncoder
                logger.info(f"Loading CrossEncoder reranker: {RERANKER_MODEL}")
                self.reranker = CrossEncoder(RERANKER_MODEL)
                logger.info("CrossEncoder reranker loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load CrossEncoder, continuing without re-ranking: {e}")
                self.reranker = None
        
        # Load corpus for BM25
        self._corpus: list[dict[str, Any]] = []
        self._bm25: BM25Okapi | None = None
        self._load_corpus()
    
    def _load_corpus(self) -> None:
        """Load all documents from Qdrant for BM25 indexing."""
        # Get collection info
        collection_info = self.client.get_collection(self.collection_name)
        total_points = collection_info.points_count
        
        if total_points == 0:
            self._corpus = []
            self._bm25 = None
            return
        
        # Scroll through all points
        records, _ = self.client.scroll(
            collection_name=self.collection_name,
            limit=total_points,
            with_payload=True,
            with_vectors=False,  # Don't need vectors for BM25
        )
        
        # Build corpus
        self._corpus = []
        tokenized_corpus = []
        
        for record in records:
            payload = record.payload
            doc = {
                "id": record.id,
                "text": payload.get("text", ""),
                "citation": payload.get("citation", ""),
                "citation_id": payload.get("citation_id", ""),
                "metadata": {
                    k: v for k, v in payload.items()
                    if k not in ("text", "citation", "citation_id")
                },
            }
            self._corpus.append(doc)
            tokenized_corpus.append(tokenize_indonesian(doc["text"]))
        
        # Initialize BM25 index
        if tokenized_corpus:
            self._bm25 = BM25Okapi(tokenized_corpus)
    
    def dense_search(
        self,
        query: str,
        top_k: int = 10,
        filter_conditions: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """
        Perform dense vector search using Qdrant.
        
        Args:
            query: Search query in natural language
            top_k: Number of results to return
            filter_conditions: Optional Qdrant filter conditions
        
        Returns:
            List of SearchResult objects sorted by score (descending)
        """
        # Generate query embedding
        query_embedding = self.embedder.embed_query(query)
        
        # Build filter if provided
        search_filter = None
        if filter_conditions:
            conditions = []
            for key, value in filter_conditions.items():
                conditions.append(
                    FieldCondition(key=key, match=MatchValue(value=value))
                )
            search_filter = Filter(must=conditions)
        
        # Search Qdrant (using query_points API for qdrant-client 1.16+)
        from qdrant_client.models import QueryRequest
        
        query_response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=top_k,
            query_filter=search_filter,
            with_payload=True,
        )
        
        # Convert to SearchResult
        search_results = []
        for hit in query_response.points:
            payload = hit.payload
            search_results.append(SearchResult(
                id=hit.id,
                text=payload.get("text", ""),
                citation=payload.get("citation", ""),
                citation_id=payload.get("citation_id", ""),
                score=hit.score,
                metadata={
                    k: v for k, v in payload.items()
                    if k not in ("text", "citation", "citation_id")
                },
            ))
        
        return search_results
    
    def sparse_search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[SearchResult]:
        """
        Perform BM25 sparse search over the corpus.
        
        Args:
            query: Search query in natural language
            top_k: Number of results to return
        
        Returns:
            List of SearchResult objects sorted by BM25 score (descending)
        """
        if not self._bm25 or not self._corpus:
            return []
        
        # Tokenize query
        query_tokens = tokenize_indonesian(query)
        
        if not query_tokens:
            return []
        
        # Get BM25 scores
        scores = self._bm25.get_scores(query_tokens)
        
        # Get top-k indices
        scored_indices = [(i, score) for i, score in enumerate(scores)]
        scored_indices.sort(key=lambda x: x[1], reverse=True)
        top_indices = scored_indices[:top_k]
        
        # Build results
        results = []
        for idx, score in top_indices:
            if score > 0:  # Only include non-zero scores
                doc = self._corpus[idx]
                results.append(SearchResult(
                    id=doc["id"],
                    text=doc["text"],
                    citation=doc["citation"],
                    citation_id=doc["citation_id"],
                    score=score,
                    metadata=doc["metadata"],
                ))
        
        return results
    
    def _rrf_fusion(
        self,
        dense_results: list[SearchResult],
        sparse_results: list[SearchResult],
        k: int = RRF_K,
    ) -> list[tuple[SearchResult, float]]:
        """
        Apply Reciprocal Rank Fusion to combine results.
        
        RRF Score = sum(1 / (k + rank)) for each list where document appears
        
        Args:
            dense_results: Results from dense search
            sparse_results: Results from sparse search
            k: RRF constant (default 60)
        
        Returns:
            List of (SearchResult, rrf_score) tuples sorted by RRF score
        """
        # Build ID to result mapping and accumulate RRF scores
        rrf_scores: dict[int, float] = {}
        result_map: dict[int, SearchResult] = {}
        
        # Process dense results
        for rank, result in enumerate(dense_results, start=1):
            doc_id = result.id
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k + rank)
            if doc_id not in result_map:
                result_map[doc_id] = result
        
        # Process sparse results
        for rank, result in enumerate(sparse_results, start=1):
            doc_id = result.id
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k + rank)
            if doc_id not in result_map:
                result_map[doc_id] = result
        
        # Sort by RRF score
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        
        return [(result_map[doc_id], rrf_scores[doc_id]) for doc_id in sorted_ids]
    
    def _rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int,
    ) -> list[SearchResult]:
        """
        Re-rank results using CrossEncoder for improved relevance.
        
        Args:
            query: Original search query
            results: Initial search results to re-rank
            top_k: Number of results to return after re-ranking
        
        Returns:
            Re-ranked list of SearchResult objects
        """
        if not self.reranker or not results:
            return results[:top_k]
        
        # Prepare query-document pairs for CrossEncoder
        pairs = [(query, result.text) for result in results]
        
        try:
            # Get cross-encoder scores
            scores = self.reranker.predict(pairs)
            
            # Create scored results and sort by cross-encoder score
            scored_results = list(zip(results, scores))
            scored_results.sort(key=lambda x: x[1], reverse=True)
            
            # Return top_k with updated scores
            reranked = []
            for result, ce_score in scored_results[:top_k]:
                # Normalize cross-encoder score to 0-1 range (sigmoid-like)
                normalized_score = max(0.0, min(1.0, (ce_score + 10) / 20))
                reranked.append(SearchResult(
                    id=result.id,
                    text=result.text,
                    citation=result.citation,
                    citation_id=result.citation_id,
                    score=normalized_score,
                    metadata=result.metadata,
                ))
            
            logger.debug(f"Re-ranked {len(results)} results to top {len(reranked)}")
            return reranked
            
        except Exception as e:
            logger.warning(f"Re-ranking failed, returning original results: {e}")
            return results[:top_k]
    
    def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        dense_weight: float = 0.5,
        dense_top_k: int | None = None,
        sparse_top_k: int | None = None,
        filter_conditions: dict[str, Any] | None = None,
        use_reranking: bool = True,
    ) -> list[SearchResult]:
        """
        Perform hybrid search combining dense and sparse retrieval.
        
        Uses Reciprocal Rank Fusion (RRF) to merge results from both methods,
        optionally followed by CrossEncoder re-ranking for improved relevance.
        
        Args:
            query: Search query in natural language
            top_k: Number of final results to return
            dense_weight: Weight for dense results (0-1, currently unused with RRF)
            dense_top_k: Number of dense results to retrieve (default: 2 * top_k)
            sparse_top_k: Number of sparse results to retrieve (default: 2 * top_k)
            filter_conditions: Optional filter for dense search
            use_reranking: Whether to apply CrossEncoder re-ranking (default: True)
        
        Returns:
            List of SearchResult objects with RRF-fused (and optionally re-ranked) scores
        """
        # Default retrieval counts - fetch more if reranking
        rerank_multiplier = 3 if (use_reranking and self.reranker) else 2
        if dense_top_k is None:
            dense_top_k = top_k * rerank_multiplier
        if sparse_top_k is None:
            sparse_top_k = top_k * rerank_multiplier
        
        # Perform both searches
        dense_results = self.dense_search(
            query, top_k=dense_top_k, filter_conditions=filter_conditions
        )
        sparse_results = self.sparse_search(query, top_k=sparse_top_k)
        
        # Fuse with RRF
        fused = self._rrf_fusion(dense_results, sparse_results)
        
        # Get candidates for potential re-ranking
        candidates = []
        for result, rrf_score in fused[:top_k * 2]:  # Get more candidates for reranking
            candidates.append(SearchResult(
                id=result.id,
                text=result.text,
                citation=result.citation,
                citation_id=result.citation_id,
                score=rrf_score,
                metadata=result.metadata,
            ))
        
        # Apply CrossEncoder re-ranking if enabled
        if use_reranking and self.reranker:
            return self._rerank(query, candidates, top_k)
        
        # Return top_k without re-ranking
        return candidates[:top_k]
    
    def search_by_document_type(
        self,
        query: str,
        jenis_dokumen: str,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """
        Search within a specific document type.
        
        Args:
            query: Search query
            jenis_dokumen: Document type (UU, PP, Perpres, etc.)
            top_k: Number of results
        
        Returns:
            Filtered search results
        """
        return self.hybrid_search(
            query=query,
            top_k=top_k,
            filter_conditions={"jenis_dokumen": jenis_dokumen},
        )
    
    def get_stats(self) -> dict[str, Any]:
        """Get retriever statistics."""
        collection_info = self.client.get_collection(self.collection_name)
        return {
            "collection_name": self.collection_name,
            "total_documents": collection_info.points_count,
            "corpus_loaded": len(self._corpus),
            "bm25_initialized": self._bm25 is not None,
            "embedding_model": EMBEDDING_MODEL,
            "embedding_dim": EMBEDDING_DIM,
        }


# Convenience function for quick access
def get_retriever(
    qdrant_url: str = QDRANT_URL,
    collection_name: str = COLLECTION_NAME,
) -> HybridRetriever:
    """Factory function to get a configured retriever instance."""
    return HybridRetriever(
        qdrant_url=qdrant_url,
        collection_name=collection_name,
    )


if __name__ == "__main__":
    # Quick test
    print("Initializing HybridRetriever...")
    retriever = get_retriever()
    
    stats = retriever.get_stats()
    print(f"Stats: {stats}")
    
    # Test query
    query = "Apa itu Undang-Undang Cipta Kerja?"
    print(f"\nQuery: {query}")
    
    results = retriever.hybrid_search(query, top_k=3)
    print(f"Found {len(results)} results:")
    for i, r in enumerate(results, 1):
        print(f"\n{i}. {r.citation}")
        print(f"   Score: {r.score:.4f}")
        print(f"   Text: {r.text[:100]}...")
