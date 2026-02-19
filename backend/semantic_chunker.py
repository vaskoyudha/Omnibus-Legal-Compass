"""
Semantic Chunking for Indonesian Legal Document Ingestion.

Splits documents into chunks based on semantic similarity between consecutive
sentences, rather than fixed character counts. This produces more coherent
chunks that respect topical boundaries in legal text.

Intuition: Consecutive sentences about the same legal topic have high
embedding similarity. When similarity drops below a threshold, it signals
a topic shift — an ideal place to split.

Algorithm:
    1. Split text → sentences (using punctuation boundaries)
    2. Embed each sentence with SentenceTransformer
    3. Compute cosine similarity between consecutive sentence pairs
    4. Group sentences into chunks: split when similarity < threshold
       or accumulated chunk exceeds max_chunk_size
    5. Return list of chunk strings

Example:
    >>> chunker = SemanticChunker(similarity_threshold=0.5, max_chunk_size=1500)
    >>> chunks = chunker.chunk("Pasal 1. Definisi umum. Pasal 2. Ketentuan khusus.")
    >>> print(len(chunks))
    2
"""

from __future__ import annotations

import logging
import re

import numpy as np

# Configure logging
logger = logging.getLogger(__name__)


def _split_sentences(text: str) -> list[str]:
    """
    Split text into sentences using punctuation boundaries.

    Splits on whitespace following sentence-ending punctuation marks
    commonly used in Indonesian legal text: . ! ? ;

    Args:
        text: Raw text to split into sentences

    Returns:
        List of non-empty sentence strings (stripped of leading/trailing whitespace)

    Example:
        >>> _split_sentences("Pasal 1. Definisi umum. Pasal 2.")
        ['Pasal 1.', 'Definisi umum.', 'Pasal 2.']
    """
    parts = re.split(r"(?<=[.!?;])\s+", text)
    return [s.strip() for s in parts if s.strip()]


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.

    Args:
        a: First vector (numpy array)
        b: Second vector (numpy array)

    Returns:
        Cosine similarity in range [-1, 1]. Returns 0.0 if either vector
        has zero norm (to avoid division by zero).

    Example:
        >>> _cosine_similarity(np.array([1, 0]), np.array([0, 1]))
        0.0
        >>> _cosine_similarity(np.array([1, 0]), np.array([1, 0]))
        1.0
    """
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot_product / (norm_a * norm_b))


class SemanticChunker:
    """
    Semantic chunker that splits documents based on embedding similarity.

    Groups consecutive sentences into chunks while their embeddings remain
    semantically similar. Starts a new chunk when similarity drops below
    the threshold or accumulated text exceeds max_chunk_size.

    The SentenceTransformer model is lazy-loaded on first use to avoid
    import-time overhead (the model is ~80MB).

    Args:
        similarity_threshold: Minimum cosine similarity between consecutive
            sentences to keep them in the same chunk (default: 0.5)
        max_chunk_size: Maximum character length of a single chunk (default: 1500)

    Example:
        >>> chunker = SemanticChunker(similarity_threshold=0.5)
        >>> chunks = chunker.chunk("Pasal 1. Ketentuan umum. Pasal 2. Sanksi.")
        >>> for chunk in chunks:
        ...     print(f"[{len(chunk)} chars] {chunk[:60]}...")
    """

    def __init__(
        self,
        similarity_threshold: float = 0.5,
        max_chunk_size: int = 1500,
    ) -> None:
        self.similarity_threshold = similarity_threshold
        self.max_chunk_size = max_chunk_size
        self._embedder = None
        logger.info(
            "Initialized SemanticChunker "
            f"(threshold={similarity_threshold}, max_chunk_size={max_chunk_size})"
        )

    @property
    def embedder(self):
        """Lazy-load SentenceTransformer model on first access."""
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer

            self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Loaded SentenceTransformer model: all-MiniLM-L6-v2")
        return self._embedder

    def chunk(self, text: str) -> list[str]:
        """
        Split text into semantically coherent chunks.

        Process:
        1. If text is empty/whitespace → return []
        2. Split into sentences via _split_sentences()
        3. If 0 or 1 sentences → return [text.strip()]
        4. Encode all sentences with SentenceTransformer
        5. Compute cosine similarity between consecutive pairs
        6. Group sentences: start new chunk when similarity < threshold
           or chunk would exceed max_chunk_size
        7. Return list of chunk strings

        Args:
            text: Document text to chunk

        Returns:
            List of chunk strings. Empty list if input is empty/whitespace.

        Example:
            >>> chunker = SemanticChunker(similarity_threshold=0.5)
            >>> chunks = chunker.chunk("Pasal 1. Definisi. Pasal 2. Sanksi.")
            >>> print(len(chunks))
            2
        """
        # Handle empty/whitespace input
        if not text or not text.strip():
            logger.debug("Empty input, returning []")
            return []

        # Split into sentences
        sentences = _split_sentences(text)

        # Handle 0 or 1 sentences
        if len(sentences) <= 1:
            logger.debug(f"Single sentence, returning as-is ({len(sentences)} sentences)")
            return [text.strip()]

        # Encode all sentences
        logger.info(f"Encoding {len(sentences)} sentences...")
        embeddings = self.embedder.encode(sentences)

        # Compute consecutive similarities
        similarities: list[float] = []
        for i in range(len(embeddings) - 1):
            sim = _cosine_similarity(embeddings[i], embeddings[i + 1])
            similarities.append(sim)

        logger.debug(
            f"Similarities: min={min(similarities):.3f}, "
            f"max={max(similarities):.3f}, "
            f"mean={sum(similarities) / len(similarities):.3f}"
        )

        # Group sentences into chunks
        chunks: list[str] = []
        current_sentences: list[str] = [sentences[0]]

        for i in range(len(similarities)):
            next_sentence = sentences[i + 1]
            current_text = " ".join(current_sentences)

            # Check if adding next sentence would exceed max_chunk_size
            would_exceed = len(current_text) + len(next_sentence) + 1 > self.max_chunk_size

            # Check if similarity is below threshold
            below_threshold = similarities[i] < self.similarity_threshold

            if below_threshold or would_exceed:
                # Finalize current chunk and start new one
                chunks.append(" ".join(current_sentences))
                current_sentences = [next_sentence]
                logger.debug(
                    f"Split at sentence {i + 1}: "
                    f"sim={similarities[i]:.3f}, "
                    f"exceed={would_exceed}"
                )
            else:
                current_sentences.append(next_sentence)

        # Don't forget the last chunk
        if current_sentences:
            chunks.append(" ".join(current_sentences))

        logger.info(
            f"Chunked {len(sentences)} sentences into {len(chunks)} chunks"
        )

        return chunks
