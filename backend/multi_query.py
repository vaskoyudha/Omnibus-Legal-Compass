"""
Multi-Query Fusion for Enhanced Indonesian Legal Retrieval.

Generates multiple query variants from the user's original question using
Indonesian legal templates (zero LLM calls), retrieves results for each variant,
and merges them using Reciprocal Rank Fusion (RRF).

Intuition: Different phrasings of the same question match different documents
in the vector space. By searching with 5 variants and fusing results, we
capture documents that any single query might miss.

Example:
    User question: "Apa syarat pendirian PT?"
    Variants:
        1. "syarat pendirian PT"                         (core topic)
        2. "Jelaskan tentang syarat pendirian PT"        (explain about...)
        3. "Apa ketentuan hukum mengenai syarat ..."     (legal provisions)
        4. "Pasal yang mengatur syarat pendirian PT"     (articles governing)
        5. "Definisi dan ruang lingkup syarat ..."       (definition & scope)
"""

from __future__ import annotations

import logging
import re

from retriever import SearchResult

# Configure logging
logger = logging.getLogger(__name__)

# RRF constant (standard value from information retrieval literature)
RRF_K = 60

# Indonesian question words and filler words to strip when extracting core topic
_STRIP_WORDS = {
    "apa", "bagaimana", "siapa", "kapan", "dimana", "mengapa",
    "berapa", "apakah", "itu", "yang", "adalah", "dari",
}


class MultiQueryFusion:
    """
    Multi-Query Fusion for enhanced retrieval using Indonesian legal templates.

    Generates 5 query variants from the user's question using predefined
    Indonesian legal templates (no LLM required), searches with each variant,
    and merges results using Reciprocal Rank Fusion (RRF).

    Example:
        >>> mqf = MultiQueryFusion()
        >>> variants = mqf.generate_variants("Apa syarat pendirian PT?")
        >>> print(len(variants))
        5
        >>> results = mqf.enhanced_search("Apa syarat pendirian PT?", retriever)
        >>> for result in results[:3]:
        ...     print(f"{result.citation}: {result.score:.3f}")
    """

    TEMPLATES = [
        "{query}",                                    # Original
        "Jelaskan tentang {query}",                   # Explain about...
        "Apa ketentuan hukum mengenai {query}",       # Legal provisions about...
        "Pasal yang mengatur {query}",                # Articles governing...
        "Definisi dan ruang lingkup {query}",         # Definition and scope of...
    ]

    def generate_variants(self, question: str) -> list[str]:
        """
        Generate 5 query variants from the user's question using templates.

        Extracts the core topic from the question (stripping Indonesian question
        words and punctuation), then applies each template.

        Args:
            question: User's original question in natural language

        Returns:
            List of 5 query variant strings

        Example:
            >>> mqf = MultiQueryFusion()
            >>> variants = mqf.generate_variants("Apa syarat pendirian PT?")
            >>> print(variants[0])
            "syarat pendirian PT"
            >>> print(variants[1])
            "Jelaskan tentang syarat pendirian PT"
        """
        core = _extract_core_topic(question)
        logger.info(f"Core topic extracted: '{core}' from: '{question[:50]}'")

        variants = [template.format(query=core) for template in self.TEMPLATES]
        logger.info(f"Generated {len(variants)} query variants")
        return variants

    def enhanced_search(
        self,
        question: str,
        retriever,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """
        Search with all query variants and merge results using RRF.

        Process:
        1. Generate 5 query variants via templates
        2. Search with each variant: retriever.hybrid_search(variant, top_k)
        3. Merge all result lists using Reciprocal Rank Fusion (RRF)
        4. Return deduplicated list sorted by RRF score (descending)

        Args:
            question: User's original question
            retriever: HybridRetriever instance (must have .hybrid_search() method)
            top_k: Number of results to retrieve per variant (default: 5)

        Returns:
            Deduplicated list of SearchResult objects sorted by RRF score (descending)

        Example:
            >>> mqf = MultiQueryFusion()
            >>> results = mqf.enhanced_search(
            ...     "Apa syarat pendirian PT?",
            ...     retriever,
            ...     top_k=5
            ... )
            >>> print(f"Found {len(results)} unique documents")

        RRF Formula:
            For document d appearing at rank r_i in result list i:
                RRF_score(d) = sum(1 / (k + r_i)) for all i
            where k = 60 (standard constant)

        Edge Cases:
            - Empty results from all variants → returns []
            - Duplicate documents across variants → merged with combined RRF score
        """
        logger.info(f"Multi-Query Fusion search: {question[:50]}...")

        # Generate query variants
        variants = self.generate_variants(question)

        # Search with each variant
        result_lists: list[list[SearchResult]] = []
        for variant in variants:
            logger.info(f"Searching variant: '{variant[:50]}' (top_k={top_k})...")
            results = retriever.hybrid_search(variant, top_k=top_k)
            result_lists.append(results)

        # Merge with RRF
        merged = _rrf_merge(result_lists, k=RRF_K)

        logger.info(
            f"Multi-Query Fusion complete: {len(variants)} variants "
            f"→ {len(merged)} unique documents"
        )

        return merged


def _extract_core_topic(question: str) -> str:
    """
    Extract the core topic from an Indonesian question.

    Strips Indonesian question words (apa, bagaimana, siapa, etc.) and
    punctuation to produce a clean core phrase for template insertion.

    Args:
        question: Raw user question string

    Returns:
        Core topic phrase with question words and punctuation removed

    Example:
        >>> _extract_core_topic("Apa itu PT?")
        "PT"
        >>> _extract_core_topic("Bagaimana cara mendirikan CV?")
        "cara mendirikan CV"
    """
    # Remove punctuation (?, !, ., etc.)
    cleaned = re.sub(r"[?.!,;:]+", "", question)

    # Split into words and filter out Indonesian question words (case-insensitive)
    words = cleaned.split()
    filtered = [w for w in words if w.lower() not in _STRIP_WORDS]

    # Rejoin and strip whitespace
    core = " ".join(filtered).strip()

    # Fallback: if everything was stripped, return the original (minus punctuation)
    if not core:
        core = re.sub(r"[?.!,;:]+", "", question).strip()

    return core


def _rrf_merge(
    result_lists: list[list[SearchResult]],
    k: int = RRF_K,
) -> list[SearchResult]:
    """
    Merge multiple result lists using Reciprocal Rank Fusion (RRF).

    For document d at rank r_i in list i:
        RRF_score(d) = sum(1 / (k + r_i)) for all lists where d appears

    Documents appearing in multiple lists accumulate higher scores.

    Args:
        result_lists: List of search result lists to merge
        k: RRF constant (default: 60)

    Returns:
        Deduplicated list of SearchResult sorted by RRF score (descending)
    """
    # Map: document ID -> RRF score
    rrf_scores: dict[str, float] = {}

    # Map: document ID -> SearchResult (for deduplication)
    doc_map: dict[str, SearchResult] = {}

    for result_list in result_lists:
        for rank, result in enumerate(result_list, start=1):
            doc_id = result.citation_id
            rrf_score = 1.0 / (k + rank)
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

    return merged_results
