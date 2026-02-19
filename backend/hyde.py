"""
HyDE (Hypothetical Document Embeddings) for Enhanced Retrieval.

Improves retrieval quality by generating a hypothetical answer to the user's question,
then searching with BOTH the original question and the hypothetical answer. Results are
merged using Reciprocal Rank Fusion (RRF).

Intuition: The hypothetical answer is semantically closer to actual legal documents
than the user's raw question, bridging the vocabulary gap between natural queries
and formal legal text.

Example:
    User question: "Bagaimana cara mendirikan PT?"
    Hypothetical answer: "Untuk mendirikan Perseroan Terbatas (PT), diperlukan..."
    (The hypothetical matches legal document vocabulary better)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm_client import LLMClient

# Import SearchResult at runtime for creating merged results
from retriever import SearchResult

# Configure logging
logger = logging.getLogger(__name__)

# RRF constant (standard value from information retrieval literature)
RRF_K = 60


class HyDE:
    """
    Hypothetical Document Embeddings for enhanced retrieval.
    
    Uses an LLM to generate a hypothetical answer to the user's question,
    then searches with both the original question and the hypothetical answer.
    Results are merged using Reciprocal Rank Fusion (RRF).
    
    Args:
        llm_client: LLM client for generating hypothetical answers.
                    Accepts LLMClient.
    
    Example:
        >>> hyde = HyDE(llm_client)
        >>> results = hyde.enhanced_search("Apa syarat pendirian PT?", retriever)
        >>> for result in results[:3]:
        ...     print(f"{result.citation}: {result.score:.3f}")
    """
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize HyDE with an LLM client.
        
        Args:
            llm_client: LLM client for generating hypothetical answers
        """
        self.llm_client = llm_client
        logger.info("Initialized HyDE with LLM client")
    
    def generate_hypothetical(self, question: str) -> str:
        """
        Generate a hypothetical answer to the user's question.
        
        Creates a 100-200 word hypothetical answer that mimics legal document
        vocabulary. This bridges the semantic gap between informal user questions
        and formal legal text.
        
        Args:
            question: User's question in natural language
        
        Returns:
            Hypothetical answer (100-200 words) in legal document style
        
        Example:
            >>> hyde = HyDE(llm_client)
            >>> hyp = hyde.generate_hypothetical("Bagaimana cara mendirikan PT?")
            >>> print(hyp)
            "Untuk mendirikan Perseroan Terbatas (PT), diperlukan akta pendirian..."
        """
        prompt = f"""Bayangkan Anda menulis jawaban ideal untuk pertanyaan hukum ini.
Tulis paragraf singkat (100-200 kata) yang menjawab pertanyaan seolah-olah Anda adalah ahli hukum Indonesia.
Jangan sebutkan bahwa Anda tidak tahu atau butuh konteks lebih. Langsung tulis jawabannya menggunakan bahasa formal hukum.

Pertanyaan: {question}

Jawaban ideal (100-200 kata):"""
        
        logger.info(f"Generating hypothetical answer for: {question[:50]}...")
        
        try:
            hypothetical = self.llm_client.generate(
                user_message=prompt,
                system_message="Anda adalah ahli hukum Indonesia yang menulis dengan bahasa formal hukum.",
            )
            
            logger.info(f"Generated hypothetical answer ({len(hypothetical)} chars)")
            return hypothetical.strip()
        
        except Exception as e:
            logger.error(f"Failed to generate hypothetical answer: {e}")
            # Fallback: return the original question if generation fails
            logger.warning("Falling back to original question")
            return question
    
    def enhanced_search(
        self,
        question: str,
        retriever,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """
        Search with both original question and hypothetical answer, merge with RRF.
        
        Process:
        1. Generate hypothetical answer via LLM
        2. Search with original question: retriever.search(question, top_k)
        3. Search with hypothetical: retriever.search(hypothetical, top_k)
        4. Merge results using Reciprocal Rank Fusion (RRF):
           score = sum(1 / (k + rank)) for each list where doc appears
        5. Return deduplicated list sorted by RRF score
        
        Args:
            question: User's original question
            retriever: HybridRetriever instance (must have .search() method)
            top_k: Number of results to retrieve from each search (default: 5)
        
        Returns:
            Deduplicated list of SearchResult objects sorted by RRF score (descending)
        
        Example:
            >>> hyde = HyDE(llm_client)
            >>> results = hyde.enhanced_search(
            ...     "Apa syarat pendirian PT?",
            ...     retriever,
            ...     top_k=5
            ... )
            >>> print(f"Found {len(results)} unique documents")
            >>> print(f"Top result: {results[0].citation}")
        
        RRF Formula:
            For document d appearing at rank r_i in result list i:
                RRF_score(d) = sum(1 / (k + r_i)) for all i
            where k = 60 (standard constant)
        
        Edge Cases:
            - Empty results from either search → uses results from the other
            - Duplicate documents → merged with combined RRF score
            - Generation failure → falls back to single search with original question
        """
        logger.info(f"HyDE enhanced search: {question[:50]}...")
        
        # Generate hypothetical answer
        hypothetical = self.generate_hypothetical(question)
        
        # Search with both question and hypothetical
        logger.info(f"Searching with original question (top_k={top_k})...")
        results_question = retriever.search(question, top_k=top_k)
        
        logger.info(f"Searching with hypothetical answer (top_k={top_k})...")
        results_hypothetical = retriever.search(hypothetical, top_k=top_k)
        
        # Edge case: empty results
        if not results_question and not results_hypothetical:
            logger.warning("Both searches returned empty results")
            return []
        
        if not results_question:
            logger.warning("Original question search returned empty, using only hypothetical")
            return results_hypothetical
        
        if not results_hypothetical:
            logger.warning("Hypothetical search returned empty, using only original question")
            return results_question
        
        # Compute RRF scores
        # Map: document ID -> RRF score
        rrf_scores: dict[str, float] = {}
        
        # Map: document ID -> SearchResult (for deduplication)
        doc_map: dict[str, SearchResult] = {}
        
        # Process original question results
        for rank, result in enumerate(results_question, start=1):
            doc_id = result.citation_id
            rrf_score = 1.0 / (RRF_K + rank)
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + rrf_score
            doc_map[doc_id] = result
        
        # Process hypothetical results
        for rank, result in enumerate(results_hypothetical, start=1):
            doc_id = result.citation_id
            rrf_score = 1.0 / (RRF_K + rank)
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + rrf_score
            doc_map[doc_id] = result
        
        # Build merged results sorted by RRF score
        merged_results: list[SearchResult] = []
        
        for doc_id in sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True):
            result = doc_map[doc_id]
            
            # Create new SearchResult with RRF score
            merged_result = SearchResult(
                id=result.id,
                text=result.text,
                citation=result.citation,
                citation_id=result.citation_id,
                score=rrf_scores[doc_id],  # Replace with RRF score
                metadata=result.metadata,
            )
            merged_results.append(merged_result)
        
        logger.info(
            f"HyDE merge complete: {len(results_question)} + {len(results_hypothetical)} "
            f"→ {len(merged_results)} unique documents"
        )
        
        return merged_results
