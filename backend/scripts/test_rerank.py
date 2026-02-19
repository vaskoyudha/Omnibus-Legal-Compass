import logging
import sys

from backend.retriever import HybridRetriever, SearchResult, RERANKER_MODEL


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger = logging.getLogger("test_rerank")

    # Create a bare retriever instance without running full __init__ (avoid Qdrant calls)
    retriever = object.__new__(HybridRetriever)

    # Allow forcing dummy reranker via env var (avoid large HF downloads during CI/dev)
    import os
    use_dummy = os.getenv("USE_DUMMY_RERANKER", "false").lower() == "true"

    # Try to load CrossEncoder; if unavailable or forced, use a dummy reranker to exercise timing
    try:
        if not use_dummy:
            from sentence_transformers import CrossEncoder

            logger.info(f"Loading CrossEncoder model: {RERANKER_MODEL}")
            retriever.reranker = CrossEncoder(RERANKER_MODEL)
            logger.info("CrossEncoder loaded")
        else:
            raise RuntimeError("Dummy reranker forced via USE_DUMMY_RERANKER")
    except Exception as e:
        logger.warning(f"CrossEncoder not available or forced off, using dummy reranker for timing test: {e}")

        class DummyReranker:
            def predict(self, pairs):
                # Simulate tiny processing delay per call
                import time
                time.sleep(0.02)  # 20ms
                # Return deterministic scores
                return [float(i % 7) for i in range(len(pairs))]

        retriever.reranker = DummyReranker()

    # Build dummy SearchResult list
    dummy_results = [
        SearchResult(id=i, text=f"Document content number {i}", citation=f"Doc {i}", citation_id=str(i), score=0.0, metadata={})
        for i in range(1, 11)
    ]

    # Call _rerank
    try:
        reranked = retriever._rerank("Apa itu UU Cipta Kerja?", dummy_results, top_k=5)
        logger.info(f"Reranked {len(dummy_results)} -> {len(reranked)} results")
        for i, r in enumerate(reranked, 1):
            print(f"{i}. id={r.id} score={r.score:.4f} citation={r.citation}")
    except Exception as e:
        logger.error(f"_rerank call failed: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
