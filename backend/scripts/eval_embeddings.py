"""
Embedding Evaluation Script for Indonesian Legal Corpus.

Benchmarks retrieval quality of the embedding model used in the RAG pipeline.
Runs entirely offline (no Qdrant required) — loads corpus from regulations.json,
embeds queries and documents in-memory, and measures retrieval metrics.

Metrics:
- MRR (Mean Reciprocal Rank): Average of 1/rank for first relevant result
- Recall@K (K=1,3,5,10): Fraction of queries where any relevant doc is in top-K
- Hit Rate: Same as Recall@1

Usage:
    python -m backend.scripts.eval_embeddings
    python -m backend.scripts.eval_embeddings --model "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    python -m backend.scripts.eval_embeddings --json-report results.json
"""

import json
import sys
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

import numpy as np


# Constants — must match ingest.py / retriever.py
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CORPUS_PATH = PROJECT_ROOT / "backend" / "data" / "peraturan" / "regulations.json"
GOLDEN_QA_PATH = PROJECT_ROOT / "tests" / "deepeval" / "golden_qa.json"

# Recall@K values to evaluate
RECALL_K_VALUES = [1, 3, 5, 10]


@dataclass
class RetrievalResult:
    """Result for a single query evaluation."""

    query_id: str
    question: str
    expected_regulations: list[str]
    top_k_citations: list[str]
    reciprocal_rank: float
    recall_at: dict[int, float] = field(default_factory=dict)
    first_relevant_rank: int | None = None


@dataclass
class EvalReport:
    """Aggregated evaluation report."""

    model_name: str
    corpus_size: int
    num_queries: int
    mrr: float
    hit_rate: float
    recall_at: dict[int, float]
    per_query: list[RetrievalResult]
    elapsed_seconds: float


def load_corpus(corpus_path: str | Path) -> list[dict[str, Any]]:
    """
    Load legal corpus from regulations.json.

    Returns list of dicts with keys: text, regulation_key, metadata.
    The regulation_key is formatted as "{jenis_dokumen} {nomor}/{tahun}"
    (e.g. "UU 40/2007") to match golden_qa.json regulation references.
    """
    corpus_path = Path(corpus_path)
    if not corpus_path.exists():
        raise FileNotFoundError(f"Corpus not found: {corpus_path}")

    with open(corpus_path, "r", encoding="utf-8") as f:
        documents = json.load(f)

    corpus = []
    for doc in documents:
        text = doc.get("text", "")
        if not text:
            continue

        jenis = doc.get("jenis_dokumen", "")
        nomor = doc.get("nomor", "")
        tahun = doc.get("tahun", "")

        # Build regulation key matching golden_qa format: "UU 40/2007"
        regulation_key = f"{jenis} {nomor}/{tahun}"

        corpus.append({
            "text": text,
            "regulation_key": regulation_key,
            "pasal": doc.get("pasal", ""),
            "metadata": {
                "jenis_dokumen": jenis,
                "nomor": nomor,
                "tahun": tahun,
                "judul": doc.get("judul", ""),
                "bab": doc.get("bab", ""),
                "pasal": doc.get("pasal", ""),
            },
        })

    return corpus


def load_golden_qa(qa_path: str | Path) -> list[dict[str, Any]]:
    """
    Load golden QA pairs from JSON.

    Each entry has:
    - id: unique identifier
    - question: query string
    - expected_answer_contains: keywords (unused for retrieval eval)
    - regulations: list of regulation keys like ["UU 40/2007"]
    """
    qa_path = Path(qa_path)
    if not qa_path.exists():
        raise FileNotFoundError(f"Golden QA not found: {qa_path}")

    with open(qa_path, "r", encoding="utf-8") as f:
        return json.load(f)


def embed_texts(
    texts: list[str],
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    batch_size: int = 64,
) -> np.ndarray:
    """
    Embed a list of texts using HuggingFace sentence-transformers.

    Returns a numpy array of shape (len(texts), embedding_dim).
    Uses the same model as the RAG pipeline to ensure evaluation
    reflects production behavior.
    """
    from langchain_huggingface import HuggingFaceEmbeddings

    embedder = HuggingFaceEmbeddings(model_name=model_name)

    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        batch_embeddings = embedder.embed_documents(batch)
        all_embeddings.extend(batch_embeddings)

    return np.array(all_embeddings, dtype=np.float32)


def cosine_similarity_matrix(
    query_embeddings: np.ndarray,
    corpus_embeddings: np.ndarray,
) -> np.ndarray:
    """
    Compute cosine similarity between query and corpus embeddings.

    Args:
        query_embeddings: shape (num_queries, dim)
        corpus_embeddings: shape (num_corpus, dim)

    Returns:
        Similarity matrix of shape (num_queries, num_corpus)
    """
    # Normalize to unit vectors
    query_norms = np.linalg.norm(query_embeddings, axis=1, keepdims=True)
    corpus_norms = np.linalg.norm(corpus_embeddings, axis=1, keepdims=True)

    # Avoid division by zero
    query_norms = np.maximum(query_norms, 1e-10)
    corpus_norms = np.maximum(corpus_norms, 1e-10)

    query_normalized = query_embeddings / query_norms
    corpus_normalized = corpus_embeddings / corpus_norms

    return query_normalized @ corpus_normalized.T


def evaluate_retrieval(
    corpus: list[dict[str, Any]],
    golden_qa: list[dict[str, Any]],
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    k_values: list[int] | None = None,
) -> EvalReport:
    """
    Run full retrieval evaluation.

    For each golden QA pair:
    1. Embed the question
    2. Compute cosine similarity against all corpus embeddings
    3. Rank corpus documents by similarity
    4. Check if any document from the expected regulation(s) appears in top-K

    Args:
        corpus: List of corpus documents with regulation_key
        golden_qa: List of golden QA pairs with expected regulations
        model_name: Embedding model to evaluate
        k_values: List of K values for Recall@K (default: [1, 3, 5, 10])

    Returns:
        EvalReport with aggregated and per-query metrics
    """
    if k_values is None:
        k_values = list(RECALL_K_VALUES)

    start_time = time.time()

    # Extract corpus texts and regulation keys
    corpus_texts = [doc["text"] for doc in corpus]
    corpus_regulation_keys = [doc["regulation_key"] for doc in corpus]

    # Extract query texts
    query_texts = [qa["question"] for qa in golden_qa]

    print(f"Embedding {len(corpus_texts)} corpus documents...")
    corpus_embeddings = embed_texts(corpus_texts, model_name=model_name)

    print(f"Embedding {len(query_texts)} queries...")
    query_embeddings = embed_texts(query_texts, model_name=model_name)

    print("Computing similarity matrix...")
    sim_matrix = cosine_similarity_matrix(query_embeddings, corpus_embeddings)

    # Evaluate each query
    max_k = max(k_values)
    per_query_results: list[RetrievalResult] = []
    reciprocal_ranks: list[float] = []
    recall_accumulators: dict[int, list[float]] = {k: [] for k in k_values}

    for qi, qa in enumerate(golden_qa):
        query_id = qa.get("id", f"qa_{qi}")
        question = qa["question"]
        expected_regs = set(qa.get("regulations", []))

        if not expected_regs:
            continue

        # Get similarity scores for this query
        scores = sim_matrix[qi]

        # Rank by descending similarity
        ranked_indices = np.argsort(scores)[::-1]

        # Find first relevant rank and top-K regulation keys
        first_relevant_rank = None
        top_k_reg_keys = []

        for rank, idx in enumerate(ranked_indices[:max(max_k, 50)], start=1):
            reg_key = corpus_regulation_keys[idx]
            if rank <= max_k:
                top_k_reg_keys.append(reg_key)
            if reg_key in expected_regs and first_relevant_rank is None:
                first_relevant_rank = rank

        # Compute reciprocal rank
        rr = 1.0 / first_relevant_rank if first_relevant_rank is not None else 0.0
        reciprocal_ranks.append(rr)

        # Compute recall at each K
        query_recall: dict[int, float] = {}
        for k in k_values:
            top_k_regs = set(corpus_regulation_keys[idx] for idx in ranked_indices[:k])
            # Binary recall: did ANY expected regulation appear in top-K?
            hit = 1.0 if top_k_regs & expected_regs else 0.0
            query_recall[k] = hit
            recall_accumulators[k].append(hit)

        per_query_results.append(RetrievalResult(
            query_id=query_id,
            question=question,
            expected_regulations=list(expected_regs),
            top_k_citations=top_k_reg_keys[:10],
            reciprocal_rank=rr,
            recall_at=query_recall,
            first_relevant_rank=first_relevant_rank,
        ))

    # Aggregate metrics
    mrr = float(np.mean(reciprocal_ranks)) if reciprocal_ranks else 0.0
    avg_recall = {
        k: float(np.mean(vals)) if vals else 0.0
        for k, vals in recall_accumulators.items()
    }
    hit_rate = avg_recall.get(1, 0.0)

    elapsed = time.time() - start_time

    return EvalReport(
        model_name=model_name,
        corpus_size=len(corpus),
        num_queries=len(per_query_results),
        mrr=mrr,
        hit_rate=hit_rate,
        recall_at=avg_recall,
        per_query=per_query_results,
        elapsed_seconds=elapsed,
    )


def format_report(report: EvalReport) -> str:
    """Format evaluation report as human-readable text."""
    lines = [
        "",
        "=" * 60,
        "  EMBEDDING RETRIEVAL EVALUATION REPORT",
        "=" * 60,
        "",
        f"  Model:        {report.model_name}",
        f"  Corpus size:  {report.corpus_size} articles",
        f"  Queries:      {report.num_queries}",
        f"  Time:         {report.elapsed_seconds:.1f}s",
        "",
        "-" * 60,
        "  AGGREGATE METRICS",
        "-" * 60,
        "",
        f"  MRR (Mean Reciprocal Rank):  {report.mrr:.4f}",
        f"  Hit Rate (Recall@1):         {report.hit_rate:.4f}  ({report.hit_rate * 100:.1f}%)",
    ]

    for k, recall in sorted(report.recall_at.items()):
        lines.append(f"  Recall@{k:<3d}                   {recall:.4f}  ({recall * 100:.1f}%)")

    lines.extend([
        "",
        "-" * 60,
        "  PER-QUERY RESULTS",
        "-" * 60,
    ])

    for r in report.per_query:
        status = "OK" if r.reciprocal_rank > 0 else "MISS"
        rank_str = f"rank {r.first_relevant_rank}" if r.first_relevant_rank else "not found"
        lines.append(
            f"  {status} [{r.query_id}] {r.question[:60]:<60s}  "
            f"-> {rank_str}  (RR={r.reciprocal_rank:.3f})"
        )
        lines.append(f"    Expected: {', '.join(r.expected_regulations)}")
        lines.append(f"    Top-3:    {', '.join(r.top_k_citations[:3])}")
        lines.append("")

    lines.extend([
        "=" * 60,
        f"  SUMMARY: MRR={report.mrr:.4f}  Hit Rate={report.hit_rate * 100:.1f}%  "
        f"Recall@5={report.recall_at.get(5, 0) * 100:.1f}%  "
        f"Recall@10={report.recall_at.get(10, 0) * 100:.1f}%",
        "=" * 60,
        "",
    ])

    return "\n".join(lines)


def report_to_dict(report: EvalReport) -> dict[str, Any]:
    """Convert report to JSON-serializable dict."""
    return {
        "model_name": report.model_name,
        "corpus_size": report.corpus_size,
        "num_queries": report.num_queries,
        "mrr": report.mrr,
        "hit_rate": report.hit_rate,
        "recall_at": {str(k): v for k, v in report.recall_at.items()},
        "elapsed_seconds": report.elapsed_seconds,
        "per_query": [
            {
                "query_id": r.query_id,
                "question": r.question,
                "expected_regulations": r.expected_regulations,
                "top_k_citations": r.top_k_citations[:5],
                "reciprocal_rank": r.reciprocal_rank,
                "recall_at": {str(k): v for k, v in r.recall_at.items()},
                "first_relevant_rank": r.first_relevant_rank,
            }
            for r in report.per_query
        ],
    }


def main() -> int:
    """CLI entry point for embedding evaluation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Evaluate embedding retrieval quality on golden QA pairs"
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_EMBEDDING_MODEL,
        help="HuggingFace embedding model to evaluate",
    )
    parser.add_argument(
        "--corpus-path",
        default=str(CORPUS_PATH),
        help="Path to regulations.json corpus",
    )
    parser.add_argument(
        "--qa-path",
        default=str(GOLDEN_QA_PATH),
        help="Path to golden_qa.json",
    )
    parser.add_argument(
        "--json-report",
        default=None,
        help="Optional path to write JSON report",
    )

    args = parser.parse_args()

    print(f"Loading corpus from {args.corpus_path}...")
    corpus = load_corpus(args.corpus_path)
    print(f"Loaded {len(corpus)} articles")

    print(f"Loading golden QA from {args.qa_path}...")
    golden_qa = load_golden_qa(args.qa_path)
    print(f"Loaded {len(golden_qa)} QA pairs")

    print(f"\nEvaluating model: {args.model}")
    report = evaluate_retrieval(
        corpus=corpus,
        golden_qa=golden_qa,
        model_name=args.model,
    )

    # Print human-readable report
    print(format_report(report))

    # Write JSON report if requested
    if args.json_report:
        report_dict = report_to_dict(report)
        with open(args.json_report, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        print(f"JSON report written to {args.json_report}")

    # Return non-zero if MRR is critically low (CI gate)
    if report.mrr < 0.3:
        print(f"\n[WARNING] MRR ({report.mrr:.4f}) is below 0.30 threshold")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
