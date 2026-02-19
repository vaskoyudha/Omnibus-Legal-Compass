"""
Agentic RAG — Dynamic Retrieval Strategy Selection.

Dynamically selects the best retrieval strategy based on query characteristics
and intermediate result quality. Uses rule-based routing (NOT LLM-based) to
compose existing techniques (HyDE, CRAG, Multi-Query, Query Planner) into an
adaptive retrieval loop.

Intuition: Different questions need different retrieval approaches. A simple
factual query works fine with direct search, but compound questions benefit
from decomposition, definition queries from HyDE, and poor-quality results
from refinement via CRAG or multi-query expansion.

Example:
    Compound question: "Apa perbedaan PT dan CV serta cara mendirikannya?"
        → Strategy: "decompose" (QueryPlanner)
    Definition question: "Apa itu PKWT?"
        → Strategy: "hyde" (HyDE)
    Poor initial results (avg_score < 0.3):
        → Strategy: "refine_query" (CRAG)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm_client import LLMClient

# Import SearchResult at runtime for creating results
from retriever import SearchResult

# Configure logging
logger = logging.getLogger(__name__)


class AgenticRAG:
    """
    Agentic RAG with rule-based dynamic strategy selection.

    Composes existing retrieval techniques (HyDE, CRAG, Multi-Query,
    Query Planner) and selects the best strategy based on question
    characteristics and intermediate result quality. No LLM calls
    are used for routing — all decisions are rule-based heuristics.

    Attributes:
        MAX_ITERATIONS: Maximum number of retrieval iterations (prevents infinite loops).
        llm_client: Optional LLM client (passed through to sub-techniques).
        hyde: Optional HyDE instance for definition-style queries.
        crag: Optional CRAG instance for refining poor results.
        multi_query: Optional MultiQueryFusion instance for mediocre results.
        query_planner: Optional QueryPlanner instance for compound questions.

    Example:
        >>> agentic = AgenticRAG(hyde=hyde, crag=crag, multi_query=mq, query_planner=qp)
        >>> results = agentic.enhanced_search("Apa itu PT?", retriever, top_k=5)
        >>> for r in results[:3]:
        ...     print(f"{r.citation}: {r.score:.3f}")
    """

    MAX_ITERATIONS = 3

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        retriever=None,
        hyde=None,
        crag=None,
        multi_query=None,
        query_planner=None,
    ):
        """
        Initialize AgenticRAG with optional sub-technique instances.

        All parameters are optional. If a technique is not provided, the
        agent gracefully falls back to direct search when that strategy
        would otherwise be selected.

        Args:
        llm_client: Optional LLM client (passed through to sub-techniques)
            retriever: Optional default retriever (not used directly; retriever
                       is passed per-call to enhanced_search)
            hyde: Optional HyDE instance for definition-style queries
            crag: Optional CRAG instance for refining poor-quality results
            multi_query: Optional MultiQueryFusion instance for expanding queries
            query_planner: Optional QueryPlanner instance for decomposing compound questions
        """
        self.llm_client = llm_client
        self.retriever = retriever
        self.hyde = hyde
        self.crag = crag
        self.multi_query = multi_query
        self.query_planner = query_planner
        logger.info("Initialized AgenticRAG (rule-based strategy selection)")

    def select_strategy(
        self,
        question: str,
        results: list[SearchResult] | None = None,
    ) -> str:
        """
        Select retrieval strategy based on question characteristics and result quality.

        Uses rule-based heuristics — NO LLM calls. Strategy selection depends
        on whether this is the first iteration (results=None) or a subsequent
        iteration with intermediate results.

        Args:
            question: User's question in natural language
            results: Intermediate search results from a previous iteration,
                     or None if this is the first iteration

        Returns:
            Strategy name: one of "decompose", "hyde", "refine_query",
            "multi_query", or "direct"

        Rules (in order of priority):
            - If results provided (intermediate iteration):
                - avg_score < 0.3 → "refine_query" (CRAG)
                - avg_score < 0.5 → "multi_query"
            - If first iteration (results is None):
                - word_count > 15 OR compound keywords → "decompose"
                - definition keywords → "hyde"
            - Default → "direct"

        Example:
            >>> agentic.select_strategy("Apa itu PT?")
            'hyde'
            >>> agentic.select_strategy("Syarat PT", results_with_low_scores)
            'refine_query'
        """
        # --- Intermediate iteration: select based on result quality ---
        if results is not None:
            avg_score = sum(r.score for r in results) / len(results) if results else 0

            if avg_score < 0.3:
                logger.info(
                    f"Strategy: refine_query (avg_score={avg_score:.3f} < 0.3)"
                )
                return "refine_query"

            if avg_score < 0.5:
                logger.info(
                    f"Strategy: multi_query (avg_score={avg_score:.3f} < 0.5)"
                )
                return "multi_query"

        # --- First iteration: select based on question characteristics ---
        if results is None:
            word_count = len(question.split())

            # Detect compound questions
            compound_keywords = ["dan", "serta", "antara"]
            if word_count > 15 or any(
                kw in question.lower() for kw in compound_keywords
            ):
                logger.info(
                    f"Strategy: decompose (word_count={word_count}, "
                    f"compound keywords detected)"
                )
                return "decompose"

            # Detect definition questions
            definition_keywords = ["definisi", "apa itu", "pengertian"]
            if any(kw in question.lower() for kw in definition_keywords):
                logger.info("Strategy: hyde (definition question detected)")
                return "hyde"

        # --- Default ---
        logger.info("Strategy: direct (default)")
        return "direct"

    def enhanced_search(
        self,
        question: str,
        retriever,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """
        Execute agentic retrieval loop with dynamic strategy selection.

        Iterates up to MAX_ITERATIONS times, selecting the best strategy
        at each step. Exits early if results are good enough (avg_score >= 0.5).
        Gracefully falls back to direct search if a selected technique is
        not available (None).

        Args:
            question: User's question in natural language
            retriever: HybridRetriever instance (must have .hybrid_search() method)
            top_k: Number of results to retrieve (default: 5)

        Returns:
            List of SearchResult objects from the best retrieval strategy

        Algorithm:
            1. For each iteration (up to MAX_ITERATIONS):
                a. Select strategy (rule-based)
                b. Execute strategy (with fallback to direct if technique missing)
                c. If avg_score >= 0.5: break (good enough)
            2. Return final results

        Example:
            >>> agentic = AgenticRAG(hyde=hyde, crag=crag)
            >>> results = agentic.enhanced_search("Apa itu PT?", retriever)
            >>> print(f"Found {len(results)} results")
        """
        logger.info(f"AgenticRAG search: {question[:50]}...")

        results: list[SearchResult] = []

        for iteration in range(self.MAX_ITERATIONS):
            # Select strategy: first iteration uses question only,
            # subsequent iterations also consider result quality
            strategy = self.select_strategy(
                question, results if iteration > 0 else None
            )

            logger.info(
                f"Iteration {iteration + 1}/{self.MAX_ITERATIONS}: "
                f"strategy={strategy}"
            )

            # Execute chosen strategy with graceful fallback
            results = self._execute_strategy(
                strategy, question, retriever, top_k
            )

            # Check if results are good enough to stop early
            if results:
                avg_score = sum(r.score for r in results) / len(results)
                if avg_score >= 0.5:
                    logger.info(
                        f"Early exit: avg_score={avg_score:.3f} >= 0.5 "
                        f"(iteration {iteration + 1})"
                    )
                    break

        logger.info(f"AgenticRAG complete: {len(results)} results")
        return results

    def _execute_strategy(
        self,
        strategy: str,
        question: str,
        retriever,
        top_k: int,
    ) -> list[SearchResult]:
        """
        Execute a specific retrieval strategy with fallback to direct search.

        If the selected technique is not available (None), gracefully falls
        back to direct hybrid_search.

        Args:
            strategy: Strategy name ("direct", "hyde", "decompose",
                      "multi_query", "refine_query")
            question: User's question
            retriever: HybridRetriever instance
            top_k: Number of results to retrieve

        Returns:
            List of SearchResult objects from the executed strategy
        """
        try:
            if strategy == "hyde":
                if self.hyde is not None:
                    return self.hyde.enhanced_search(
                        question, retriever, top_k=top_k
                    )
                logger.warning(
                    "HyDE not available, falling back to direct search"
                )
                return retriever.hybrid_search(question, top_k=top_k)

            if strategy == "decompose":
                if self.query_planner is not None:
                    return self.query_planner.multi_hop_search(
                        question, retriever, top_k=top_k
                    )
                logger.warning(
                    "QueryPlanner not available, falling back to direct search"
                )
                return retriever.hybrid_search(question, top_k=top_k)

            if strategy == "multi_query":
                if self.multi_query is not None:
                    return self.multi_query.enhanced_search(
                        question, retriever, top_k=top_k
                    )
                logger.warning(
                    "MultiQuery not available, falling back to direct search"
                )
                return retriever.hybrid_search(question, top_k=top_k)

            if strategy == "refine_query":
                if self.crag is not None:
                    return self.crag.enhanced_search(
                        question, retriever, top_k=top_k
                    )
                logger.warning(
                    "CRAG not available, falling back to direct search"
                )
                return retriever.hybrid_search(question, top_k=top_k)

            # Default: direct search
            return retriever.hybrid_search(question, top_k=top_k)

        except Exception as e:
            logger.error(f"Strategy '{strategy}' failed: {e}", exc_info=True)
            logger.warning("Falling back to direct search after error")
            return retriever.hybrid_search(question, top_k=top_k)
