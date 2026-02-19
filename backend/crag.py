"""
Corrective RAG (CRAG) for Quality-Aware Indonesian Legal Retrieval.

Grades retrieval quality after initial search and takes corrective action:
- **correct** (avg score ≥ 0.7): use results as-is
- **ambiguous** (0.3 ≤ avg score < 0.7): rephrase query, merge with RRF
- **incorrect** (avg score < 0.3): rephrase query, replace entirely

Intuition: Not all retrievals are equal. When the retriever returns low-confidence
results, rephrasing the query in different words can surface better documents.
Rather than blindly returning poor results, CRAG detects quality issues and
self-corrects via query rephrasing.

Example:
    User question: "Bagaimana cara mendirikan PT?"
    Initial retrieval score: 0.25 (incorrect)
    Rephrased: "Prosedur dan persyaratan pendirian Perseroan Terbatas"
    Result: Higher-quality documents from rephrased search
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm_client import LLMClient, NVIDIANimClient, CopilotChatClient

# Import SearchResult at runtime for creating merged results
from retriever import SearchResult

# Configure logging
logger = logging.getLogger(__name__)

# RRF constant (standard value from information retrieval literature)
RRF_K = 60


class CRAG:
    """
    Corrective RAG for quality-aware retrieval with self-correction.

    Grades initial retrieval results and takes corrective action when quality
    is insufficient. Uses three-way grading (correct/ambiguous/incorrect)
    to decide whether to keep, augment, or replace results.

    Args:
        llm_client: Optional LLM client for query rephrasing.
                    If None, rephrasing is skipped (graceful degradation).
                    Accepts LLMClient, NVIDIANimClient, or CopilotChatClient.

    Example:
        >>> crag = CRAG(llm_client)
        >>> results = crag.enhanced_search("Apa syarat pendirian PT?", retriever)
        >>> for result in results[:3]:
        ...     print(f"{result.citation}: {result.score:.3f}")
    """

    CORRECT_THRESHOLD = 0.7
    AMBIGUOUS_THRESHOLD = 0.3

    def __init__(
        self,
        llm_client: LLMClient | NVIDIANimClient | CopilotChatClient | None = None,
    ):
        """
        Initialize CRAG with an optional LLM client.

        Args:
            llm_client: Optional LLM client for query rephrasing.
                        If None, rephrasing falls back to returning original query.
        """
        self.llm_client = llm_client
        logger.info(
            "Initialized CRAG %s",
            "with LLM client" if llm_client else "without LLM client (no rephrasing)",
        )

    def grade_retrieval(self, question: str, results: list[SearchResult]) -> str:
        """
        Grade retrieval quality based on average score of results.

        Computes the mean score across all results and classifies into
        three quality tiers:
        - "correct" (avg ≥ 0.7): results are high quality
        - "ambiguous" (0.3 ≤ avg < 0.7): results are uncertain
        - "incorrect" (avg < 0.3 or empty): results are poor quality

        Args:
            question: The original user question (for logging)
            results: List of SearchResult objects from initial retrieval

        Returns:
            Grade string: "correct", "ambiguous", or "incorrect"

        Example:
            >>> crag = CRAG()
            >>> grade = crag.grade_retrieval("Syarat PT?", results)
            >>> print(grade)
            "correct"
        """
        if not results:
            logger.warning("Empty results for question: '%s' → incorrect", question[:50])
            return "incorrect"

        avg_score = sum(r.score for r in results) / len(results)
        logger.info(
            "Retrieval grade for '%s': avg_score=%.3f (%d results)",
            question[:50],
            avg_score,
            len(results),
        )

        if avg_score >= self.CORRECT_THRESHOLD:
            logger.info("Grade: correct (avg %.3f ≥ %.1f)", avg_score, self.CORRECT_THRESHOLD)
            return "correct"

        if avg_score >= self.AMBIGUOUS_THRESHOLD:
            logger.info("Grade: ambiguous (%.1f ≤ avg %.3f < %.1f)",
                        self.AMBIGUOUS_THRESHOLD, avg_score, self.CORRECT_THRESHOLD)
            return "ambiguous"

        logger.info("Grade: incorrect (avg %.3f < %.1f)", avg_score, self.AMBIGUOUS_THRESHOLD)
        return "incorrect"

    def rephrase_query(self, question: str) -> str:
        """
        Rephrase the query using the LLM to improve retrieval.

        If no LLM client is available, returns the original question unchanged
        (graceful degradation).

        Args:
            question: The original user question to rephrase

        Returns:
            Rephrased question string, or original if no LLM available

        Example:
            >>> crag = CRAG(llm_client)
            >>> rephrased = crag.rephrase_query("Bagaimana cara mendirikan PT?")
            >>> print(rephrased)
            "Prosedur dan persyaratan pendirian Perseroan Terbatas"
        """
        if self.llm_client is None:
            logger.warning("No LLM client available, returning original question")
            return question

        prompt = (
            "Ulangi pertanyaan hukum berikut dengan kata-kata berbeda untuk "
            "menemukan dokumen yang lebih relevan:\n\n"
            f"{question}\n\n"
            "Pertanyaan yang diulang:"
        )

        logger.info("Rephrasing query: '%s'...", question[:50])

        try:
            rephrased = self.llm_client.generate(user_message=prompt)
            logger.info("Rephrased query: '%s'", rephrased[:50])
            return rephrased.strip()
        except Exception as e:
            logger.error("Failed to rephrase query: %s", e)
            logger.warning("Falling back to original question")
            return question

    def enhanced_search(
        self,
        question: str,
        retriever,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """
        Search with corrective retrieval: grade quality and self-correct if needed.

        Process:
        1. Initial search: retriever.hybrid_search(question, top_k)
        2. Grade retrieval quality based on average score
        3. Take corrective action:
           - correct (≥ 0.7): return original results
           - ambiguous (0.3-0.7): rephrase, search again, RRF merge
           - incorrect (< 0.3): rephrase, search again, return ONLY rephrased

        Args:
            question: User's original question
            retriever: HybridRetriever instance (must have .hybrid_search() method)
            top_k: Number of results to retrieve (default: 5)

        Returns:
            List of SearchResult objects (potentially corrected)

        Example:
            >>> crag = CRAG(llm_client)
            >>> results = crag.enhanced_search(
            ...     "Apa syarat pendirian PT?",
            ...     retriever,
            ...     top_k=5
            ... )
            >>> print(f"Found {len(results)} documents")

        Edge Cases:
            - No LLM client → ambiguous/incorrect degrade to returning original results
            - Empty initial results → grade is "incorrect", attempts rephrase
            - Rephrase failure → falls back to original question
        """
        logger.info("CRAG enhanced search: '%s'...", question[:50])

        # Step 1: Initial search
        results = retriever.hybrid_search(question, top_k=top_k)
        logger.info("Initial search returned %d results", len(results))

        # Step 2: Grade retrieval quality
        grade = self.grade_retrieval(question, results)

        # Step 3: Corrective action
        if grade == "correct":
            logger.info("Grade correct — returning original results")
            return results

        if grade == "ambiguous":
            logger.info("Grade ambiguous — rephrasing and merging with RRF")
            rephrased = self.rephrase_query(question)
            rephrased_results = retriever.hybrid_search(rephrased, top_k=top_k)

            merged = _rrf_merge([results, rephrased_results], k=RRF_K)
            logger.info(
                "CRAG ambiguous merge: %d + %d → %d unique documents",
                len(results),
                len(rephrased_results),
                len(merged),
            )
            return merged

        # grade == "incorrect"
        logger.info("Grade incorrect — rephrasing and replacing entirely")
        rephrased = self.rephrase_query(question)
        rephrased_results = retriever.hybrid_search(rephrased, top_k=top_k)

        logger.info(
            "CRAG incorrect replacement: %d original → %d rephrased results",
            len(results),
            len(rephrased_results),
        )
        return rephrased_results


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
