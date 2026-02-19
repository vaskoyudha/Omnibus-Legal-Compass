"""
Query Decomposition for Multi-Hop Retrieval.

Detects complex questions containing multiple sub-questions and decomposes them
into 2-4 simpler queries for improved retrieval accuracy. Results from each
sub-query are merged using Reciprocal Rank Fusion (RRF).

Intuition: Complex compound questions often fail to match relevant documents
because they mix multiple concepts. Decomposing into focused sub-queries
increases recall by finding documents for each concept independently.

Example:
    Complex: "Apa perbedaan antara PT dan CV serta bagaimana cara mendirikannya?"
    Sub-queries:
        1. "Apa perbedaan antara PT dan CV?"
        2. "Bagaimana cara mendirikan PT?"
        3. "Bagaimana cara mendirikan CV?"
"""

from __future__ import annotations

import re
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm_client import LLMClient, NVIDIANimClient, CopilotChatClient
    from retriever import HybridRetriever, SearchResult

# Import SearchResult at runtime for creating merged results
from retriever import SearchResult

# Configure logging
logger = logging.getLogger(__name__)

# RRF constant (must match hyde.py and retriever.py)
RRF_K = 60


class QueryPlanner:
    """
    Query decomposition for multi-hop retrieval.
    
    Detects complex questions with multiple sub-questions and decomposes them
    using an LLM. Each sub-query is searched independently, then results are
    merged with RRF for improved recall.
    
    Attributes:
        llm_client: LLM client for generating sub-queries (Copilot, NVIDIA NIM, etc.)
    """
    
    def __init__(
        self,
        llm_client: LLMClient | NVIDIANimClient | CopilotChatClient,
    ):
        """
        Initialize QueryPlanner.
        
        Args:
            llm_client: LLM client for decomposing complex questions
        """
        self.llm_client = llm_client
        logger.info("QueryPlanner initialized with LLM client")
    
    def should_decompose(self, question: str) -> bool:
        """
        Detect if question is complex and needs decomposition.
        
        Uses keyword-based heuristics to identify compound questions with
        multiple sub-questions. Checks for Indonesian conjunction words
        that indicate complexity.
        
        Args:
            question: User's original question
            
        Returns:
            True if question contains multiple sub-questions, False otherwise
            
        Example:
            >>> planner.should_decompose("Apa syarat mendirikan PT?")
            False
            >>> planner.should_decompose("Apa perbedaan PT dan CV serta cara mendirikannya?")
            True
        """
        # Indonesian compound question indicators
        indicators = [
            "dan",          # and
            "serta",        # as well as
            "juga",         # also
            "selain",       # besides
            "dibandingkan", # compared
            "antara",       # between
            "vs",           # versus
            "versus",       # versus
        ]
        
        question_lower = question.lower()
        is_complex = any(indicator in question_lower for indicator in indicators)
        
        if is_complex:
            logger.info(f"Complex question detected: {question[:50]}...")
        else:
            logger.debug(f"Simple question detected: {question[:50]}...")
        
        return is_complex
    
    def decompose(self, question: str) -> list[str]:
        """
        Break complex question into 2-4 sub-queries using LLM.
        
        Calls LLM with Indonesian prompt asking to decompose the question
        into simpler, independent sub-questions. Parses LLM response to
        extract sub-queries, handling numbered lists and bullet points.
        
        Args:
            question: Complex question to decompose
            
        Returns:
            List of 2-4 sub-query strings. Empty list if decomposition fails.
            
        Example:
            >>> planner.decompose("Apa perbedaan PT dan CV serta cara mendirikan PT?")
            [
                "Apa perbedaan antara PT dan CV?",
                "Bagaimana cara mendirikan PT?"
            ]
        """
        # Indonesian decomposition prompt
        prompt = f"""Pecah pertanyaan hukum berikut menjadi 2-4 sub-pertanyaan yang lebih sederhana dan spesifik.
Setiap sub-pertanyaan harus bisa dijawab secara independen dan fokus pada satu konsep hukum.

Pertanyaan asli: {question}

Format output (satu baris per sub-pertanyaan, maksimal 4):
1. Sub-pertanyaan pertama
2. Sub-pertanyaan kedua
3. Sub-pertanyaan ketiga (jika diperlukan)
4. Sub-pertanyaan keempat (jika diperlukan)

PENTING: Jangan tambahkan penjelasan atau komentar. Hanya tulis sub-pertanyaan.

Sub-pertanyaan:"""
        
        try:
            # Generate sub-queries via LLM
            response = self.llm_client.generate(
                user_message=prompt,
            )
            
            logger.debug(f"LLM decomposition response: {response[:200]}...")
            
            # Parse numbered/bulleted lines
            sub_questions = []
            lines = response.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Match patterns like "1. ", "2) ", "- ", "• "
                # Also handle plain lines without markers
                match = re.match(r'^(?:\d+[\.\)]\s*|[-•]\s*)(.+)$', line)
                
                if match:
                    cleaned = match.group(1).strip()
                    if cleaned:
                        sub_questions.append(cleaned)
                elif line and not line.startswith(('Sub-pertanyaan:', 'Pertanyaan:', 'PENTING:')):
                    # Handle plain lines without markers (fallback)
                    sub_questions.append(line)
            
            # Cap at 4 sub-questions for performance
            sub_questions = sub_questions[:4]
            
            if not sub_questions:
                logger.warning(f"No sub-questions extracted from LLM response: {response}")
                return []
            
            logger.info(f"Decomposed into {len(sub_questions)} sub-queries: {sub_questions}")
            return sub_questions
        
        except Exception as e:
            logger.error(f"Decomposition failed: {e}", exc_info=True)
            return []
    
    def multi_hop_search(
        self,
        question: str,
        retriever: HybridRetriever,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """
        Execute multi-hop search with query decomposition and RRF merging.
        
        Workflow:
            1. Check if question is complex via should_decompose()
            2. If simple: return regular retriever.search()
            3. If complex:
                a. Decompose into 2-4 sub-queries
                b. Search each sub-query independently
                c. Merge all results using RRF
                d. Deduplicate and sort by RRF score
        
        Args:
            question: User's question (may be complex)
            retriever: HybridRetriever instance for searching
            top_k: Number of results to return after merging
            
        Returns:
            List of SearchResult objects, sorted by RRF score. If decomposition
            fails or question is simple, returns regular search results.
            
        Example:
            >>> results = planner.multi_hop_search(
            ...     "Apa perbedaan PT dan CV serta cara mendirikannya?",
            ...     retriever,
            ...     top_k=5
            ... )
            >>> len(results)
            5
        """
        # Check complexity
        if not self.should_decompose(question):
            logger.info("Simple question - using regular search")
            return retriever.hybrid_search(question, top_k=top_k)
        
        # Decompose question
        sub_questions = self.decompose(question)
        
        # Fallback to regular search if decomposition fails
        if not sub_questions:
            logger.warning("Decomposition failed - falling back to regular search")
            return retriever.hybrid_search(question, top_k=top_k)
        
        # Search each sub-query
        logger.info(f"Searching {len(sub_questions)} sub-queries...")
        all_results: list[list[SearchResult]] = []
        
        for i, sub_q in enumerate(sub_questions, start=1):
            logger.debug(f"Sub-query {i}/{len(sub_questions)}: {sub_q}")
            
            try:
                results = retriever.hybrid_search(sub_q, top_k=top_k)
                all_results.append(results)
                logger.debug(f"  Retrieved {len(results)} results")
            except Exception as e:
                logger.error(f"Search failed for sub-query '{sub_q}': {e}")
                # Continue with other sub-queries
                continue
        
        # Check if we got any results
        if not all_results:
            logger.warning("All sub-query searches failed - falling back to regular search")
            return retriever.hybrid_search(question, top_k=top_k)
        
        # Merge with RRF (same formula as HyDE)
        logger.info("Merging results with RRF...")
        
        rrf_scores: dict[str, float] = {}
        doc_map: dict[str, SearchResult] = {}
        
        for result_list in all_results:
            for rank, result in enumerate(result_list, start=1):
                # Use citation_id as unique identifier
                doc_id = result.citation_id
                
                # Compute RRF score
                rrf_score = 1.0 / (RRF_K + rank)
                rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + rrf_score
                
                # Store first occurrence of document
                if doc_id not in doc_map:
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
        
        # Return top_k results
        final_results = merged_results[:top_k]
        logger.info(f"Multi-hop search complete: {len(final_results)} results (from {len(merged_results)} unique docs)")
        
        return final_results
