"""
Parent-Child Retrieval for Enhanced Indonesian Legal Search.

Indexes small child chunks for retrieval precision but returns large parent
context to the LLM for better answer generation. Children are mapped to their
parent via metadata["parent_citation_id"], and the full parent text is looked
up from a pre-built parent_store dictionary.

Intuition: Small chunks match user queries precisely (high recall), but the
surrounding parent context (e.g., full Pasal or Bab) gives the LLM enough
information to generate accurate, complete answers.

Example:
    User question: "Apa syarat pendirian PT?"
    Child chunk: "...modal dasar Perseroan paling sedikit Rp50.000.000..."
    Parent text: Full Pasal 32 UU 40/2007 (all ayat, complete context)

Algorithm:
    1. Search for child chunks (small, precise)
    2. Map each child to its parent via metadata["parent_citation_id"]
    3. Look up parent full text from parent_store dict
    4. Return parent text but preserve child's citation/score/metadata
    5. Dedup by parent_id (multiple children may point to same parent)
    6. Graceful fallback: if no parent_store or parent not found, return children
"""

from __future__ import annotations

import logging

from retriever import SearchResult

# Configure logging
logger = logging.getLogger(__name__)


class ParentChildRetriever:
    """
    Parent-Child Retrieval for enhanced legal search context.

    Retrieves small child chunks for precision, then expands each result to
    its full parent text for richer LLM context. Deduplicates by parent_id
    so multiple children pointing to the same parent produce only one result.

    Args:
        parent_store: Dictionary mapping parent_citation_id to full parent text.
                      Example: {"UU_40_2007_Pasal_1": "Full text of Pasal 1..."}
                      If None, falls back to returning child chunks as-is.

    Example:
        >>> store = {"UU_40_2007_Pasal_1": "Full text of Pasal 1 from UU 40/2007..."}
        >>> pcr = ParentChildRetriever(parent_store=store)
        >>> results = pcr.enhanced_search("Apa syarat pendirian PT?", retriever)
        >>> for result in results[:3]:
        ...     print(f"{result.citation}: {result.score:.3f}")
    """

    def __init__(self, parent_store: dict[str, str] | None = None) -> None:
        """
        Initialize ParentChildRetriever with an optional parent store.

        Args:
            parent_store: Dictionary mapping parent_citation_id to full parent text.
                          If None, enhanced_search falls back to returning children.
        """
        self.parent_store = parent_store or {}
        logger.info(
            "Initialized ParentChildRetriever with %d parent documents",
            len(self.parent_store),
        )

    def enhanced_search(
        self,
        question: str,
        retriever,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """
        Retrieve child chunks and expand to parent context.

        Process:
        1. Retrieve 2x children: retriever.hybrid_search(question, top_k * 2)
        2. For each child, get parent_id from metadata["parent_citation_id"]
        3. Deduplicate by parent_id (seen_parents set)
        4. Look up parent text from parent_store
        5. Create new SearchResult with parent text, keeping child citation/score/metadata
        6. Collect until len(parent_results) >= top_k
        7. Fallback: if no parent_store or no parents found, return child_results[:top_k]

        Args:
            question: User's original question
            retriever: HybridRetriever instance (must have .hybrid_search() method)
            top_k: Number of results to return (default: 5)

        Returns:
            List of SearchResult objects with parent text (or child fallback)

        Example:
            >>> pcr = ParentChildRetriever(parent_store=store)
            >>> results = pcr.enhanced_search(
            ...     "Apa syarat pendirian PT?",
            ...     retriever,
            ...     top_k=5
            ... )
            >>> print(f"Found {len(results)} parent documents")

        Edge Cases:
            - No parent_store → returns child_results[:top_k]
            - Empty parent_store → returns child_results[:top_k]
            - Child lacks parent_citation_id → skipped for parent expansion
            - parent_citation_id not in store → skipped for parent expansion
            - No parents found after processing all children → returns child_results[:top_k]
        """
        logger.info("Parent-Child search: %s...", question[:50])

        # Retrieve 2x children for dedup margin
        child_results = retriever.hybrid_search(question, top_k=top_k * 2)

        # Fallback: if no parent_store, return children directly
        if not self.parent_store:
            logger.info("No parent store available, returning child results")
            return child_results[:top_k]

        # Map children to parents with deduplication
        seen_parents: set[str] = set()
        parent_results: list[SearchResult] = []

        for child in child_results:
            if len(parent_results) >= top_k:
                break

            parent_id = child.metadata.get("parent_citation_id")
            if parent_id is None:
                continue

            # Deduplicate by parent_id
            if parent_id in seen_parents:
                continue

            # Look up parent text
            parent_text = self.parent_store.get(parent_id)
            if parent_text is None:
                continue

            seen_parents.add(parent_id)

            # Create new SearchResult with parent text, keeping child metadata
            parent_result = SearchResult(
                id=child.id,
                text=parent_text,
                citation=child.citation,
                citation_id=child.citation_id,
                score=child.score,
                metadata=child.metadata,
            )
            parent_results.append(parent_result)

        # Fallback: if no parents found, return children
        if not parent_results:
            logger.warning(
                "No parent documents found, falling back to child results"
            )
            return child_results[:top_k]

        logger.info(
            "Parent-Child expansion complete: %d children → %d parent documents",
            len(child_results),
            len(parent_results),
        )

        return parent_results
