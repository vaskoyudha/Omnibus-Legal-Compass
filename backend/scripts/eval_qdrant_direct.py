"""
Qdrant Direct Retrieval Evaluation for Indonesian Legal Corpus.

Evaluates retrieval quality by querying the production Qdrant instance via
the HybridRetriever from retriever.py. Unlike eval_embeddings.py (which
runs offline with in-memory cosine similarity), this script measures the
actual production retrieval pipeline including:
  - Dense vector search (Jina / NVIDIA / HuggingFace embeddings)
  - BM25 sparse retrieval
  - Reciprocal Rank Fusion (RRF)
  - CrossEncoder re-ranking
  - Query expansion (synonym-based)
  - Legal reference auto-detection

This gives **production-parity metrics** against the full Qdrant corpus
(27,239 chunks), eliminating the embedding mismatch that can cause metric
collapse in offline evaluation.

Metrics:
- MRR (Mean Reciprocal Rank): Average of 1/rank for first relevant result
- Hit Rate (Recall@1): Fraction of queries where relevant doc is rank 1
- Recall@K (K=1,3,5,10): Fraction of queries with relevant doc in top-K
- NDCG@K (K=5,10): Normalized Discounted Cumulative Gain
- Per-category MRR/Recall/NDCG breakdown
- Latency percentiles (p50, p95, p99) — real retrieval latency

Usage:
    python -m backend.scripts.eval_qdrant_direct
    python -m backend.scripts.eval_qdrant_direct --dry-run
    python -m backend.scripts.eval_qdrant_direct --top-k 10 --output results.json
    python -m backend.scripts.eval_qdrant_direct --qa-file tests/deepeval/golden_qa.json
"""

import argparse
import json
import math
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GOLDEN_QA_PATH = PROJECT_ROOT / "tests" / "deepeval" / "golden_qa.json"
DEFAULT_OUTPUT = "eval_results_phase4_qdrant.json"

RECALL_K_VALUES = [1, 3, 5, 10]
NDCG_K_VALUES = [5, 10]


# ---------------------------------------------------------------------------
# Data classes (mirrors eval_embeddings.py for report compatibility)
# ---------------------------------------------------------------------------

@dataclass
class RetrievalResult:
    """Result for a single query evaluation."""

    query_id: str
    question: str
    expected_regulations: list[str]
    top_k_citations: list[str]
    reciprocal_rank: float
    recall_at: dict[int, float] = field(default_factory=dict)
    ndcg_at: dict[int, float] = field(default_factory=dict)
    first_relevant_rank: int | None = None
    category: str = "factual"
    latency_ms: float = 0.0


@dataclass
class CategoryMetrics:
    """Aggregated metrics for a single category."""

    category: str
    num_queries: int
    mrr: float
    recall_at: dict[int, float]
    ndcg_at: dict[int, float]


@dataclass
class LatencyStats:
    """Latency statistics for query evaluation."""

    p50_ms: float
    p95_ms: float
    p99_ms: float
    mean_ms: float
    min_ms: float
    max_ms: float


@dataclass
class EvalReport:
    """Aggregated evaluation report."""

    model_name: str
    corpus_size: int
    num_queries: int
    mrr: float
    hit_rate: float
    recall_at: dict[int, float]
    ndcg_at: dict[int, float]
    per_query: list[RetrievalResult]
    per_category: list[CategoryMetrics]
    latency: LatencyStats | None
    elapsed_seconds: float


# ---------------------------------------------------------------------------
# Metric helpers (reused from eval_embeddings.py formulas)
# ---------------------------------------------------------------------------

def compute_ndcg(ranked_relevance: list[int], k: int) -> float:
    """
    Compute NDCG@K with binary relevance.

    Args:
        ranked_relevance: List of binary relevance labels (1=relevant, 0=not)
                          in ranked order (index 0 = rank 1).
        k: Number of top positions to evaluate.

    Returns:
        NDCG@K score in [0, 1]. Returns 0.0 if no relevant documents exist.
    """
    ranked_relevance = ranked_relevance[:k]

    # DCG: sum of rel_i / log2(i + 2) for i in [0..k-1]
    dcg = 0.0
    for i, rel in enumerate(ranked_relevance):
        dcg += rel / math.log2(i + 2)

    # Ideal DCG: sort relevance descending, compute same formula
    ideal_relevance = sorted(ranked_relevance, reverse=True)
    idcg = 0.0
    for i, rel in enumerate(ideal_relevance):
        idcg += rel / math.log2(i + 2)

    if idcg == 0.0:
        return 0.0
    return dcg / idcg


def compute_category_metrics(
    per_query: list[RetrievalResult],
    k_values: list[int],
    ndcg_k_values: list[int],
) -> list[CategoryMetrics]:
    """
    Compute per-category aggregated metrics.

    Groups queries by their category field, then computes MRR, Recall@K,
    and NDCG@K for each group.
    """
    categories: dict[str, list[RetrievalResult]] = {}
    for r in per_query:
        categories.setdefault(r.category, []).append(r)

    results = []
    for cat, queries in sorted(categories.items()):
        cat_mrr = float(np.mean([q.reciprocal_rank for q in queries]))
        cat_recall: dict[int, float] = {}
        for k in k_values:
            vals = [q.recall_at.get(k, 0.0) for q in queries]
            cat_recall[k] = float(np.mean(vals)) if vals else 0.0
        cat_ndcg: dict[int, float] = {}
        for k in ndcg_k_values:
            vals = [q.ndcg_at.get(k, 0.0) for q in queries]
            cat_ndcg[k] = float(np.mean(vals)) if vals else 0.0
        results.append(CategoryMetrics(
            category=cat,
            num_queries=len(queries),
            mrr=cat_mrr,
            recall_at=cat_recall,
            ndcg_at=cat_ndcg,
        ))
    return results


def compute_latency_stats(latencies_ms: list[float]) -> LatencyStats | None:
    """
    Compute latency percentiles from per-query latency measurements.

    Returns None if no latency data is available.
    """
    if not latencies_ms:
        return None
    arr = np.array(latencies_ms)
    return LatencyStats(
        p50_ms=float(np.percentile(arr, 50)),
        p95_ms=float(np.percentile(arr, 95)),
        p99_ms=float(np.percentile(arr, 99)),
        mean_ms=float(np.mean(arr)),
        min_ms=float(np.min(arr)),
        max_ms=float(np.max(arr)),
    )


# ---------------------------------------------------------------------------
# QA loading
# ---------------------------------------------------------------------------

def load_golden_qa(qa_path: str | Path) -> list[dict[str, Any]]:
    """
    Load golden QA pairs from JSON.

    Each entry has:
    - id: unique identifier (e.g. "qa_001")
    - question: query string
    - expected_answer_contains: keywords (unused for retrieval eval)
    - regulations: list of regulation keys like ["UU 40/2007"]
    - category (optional): defaults to "factual"
    """
    qa_path = Path(qa_path)
    if not qa_path.exists():
        raise FileNotFoundError(f"Golden QA not found: {qa_path}")

    with open(qa_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Regulation ID extraction from retriever SearchResult
# ---------------------------------------------------------------------------

def extract_regulation_id(result: Any) -> str:
    """
    Extract regulation ID from a SearchResult's metadata.

    Builds the canonical format "{jenis_dokumen} {nomor}/{tahun}"
    (e.g. "UU 40/2007") to match the golden_qa.json regulation references.

    Args:
        result: A SearchResult object from HybridRetriever.hybrid_search()

    Returns:
        Regulation ID string, or "" if metadata is incomplete.
    """
    metadata = result.metadata if hasattr(result, "metadata") else {}
    jenis = str(metadata.get("jenis_dokumen", "")).strip()
    nomor = str(metadata.get("nomor", "")).strip()
    tahun = str(metadata.get("tahun", "")).strip()

    if jenis and nomor and tahun:
        return f"{jenis} {nomor}/{tahun}"
    return ""


# ---------------------------------------------------------------------------
# Core evaluation
# ---------------------------------------------------------------------------

def evaluate_qdrant_direct(
    golden_qa: list[dict[str, Any]],
    retriever: Any,
    top_k: int = 10,
    k_values: list[int] | None = None,
    ndcg_k_values: list[int] | None = None,
) -> EvalReport:
    """
    Run full retrieval evaluation against production Qdrant via HybridRetriever.

    For each golden QA pair:
    1. Call retriever.hybrid_search(question, top_k=top_k)
    2. Extract regulation IDs from retrieved chunks
    3. Compute reciprocal rank, Recall@K, NDCG@K
    4. Track per-query latency (real retrieval latency)

    Args:
        golden_qa: List of golden QA pairs with expected regulations
        retriever: HybridRetriever instance (from backend.retriever)
        top_k: Number of results to retrieve per query
        k_values: List of K values for Recall@K (default: [1, 3, 5, 10])
        ndcg_k_values: List of K values for NDCG@K (default: [5, 10])

    Returns:
        EvalReport with aggregated and per-query metrics
    """
    if k_values is None:
        k_values = list(RECALL_K_VALUES)
    if ndcg_k_values is None:
        ndcg_k_values = list(NDCG_K_VALUES)

    start_time = time.time()

    # Get corpus size from retriever stats
    try:
        stats = retriever.get_stats()
        corpus_size = stats.get("total_documents", 0) or 0
    except Exception:
        corpus_size = 0

    # Determine model name from retriever configuration
    model_name = "unknown"
    if hasattr(retriever, "use_jina") and retriever.use_jina:
        model_name = "jina-embeddings-v3 (qdrant-direct)"
    elif hasattr(retriever, "use_nvidia") and retriever.use_nvidia:
        model_name = "nvidia/nv-embedqa-e5-v5 (qdrant-direct)"
    else:
        model_name = "paraphrase-multilingual-MiniLM-L12-v2 (qdrant-direct)"

    max_k = max(max(k_values), max(ndcg_k_values), top_k)

    per_query_results: list[RetrievalResult] = []
    reciprocal_ranks: list[float] = []
    recall_accumulators: dict[int, list[float]] = {k: [] for k in k_values}
    ndcg_accumulators: dict[int, list[float]] = {k: [] for k in ndcg_k_values}
    latencies_ms: list[float] = []

    total = len(golden_qa)

    for qi, qa in enumerate(golden_qa):
        query_id = qa.get("id", f"qa_{qi}")
        question = qa["question"]
        expected_regs = set(qa.get("regulations", []))
        category = qa.get("category", "factual")

        if not expected_regs:
            continue

        # --- Call production retriever ---
        query_start = time.perf_counter()
        try:
            results = retriever.hybrid_search(query=question, top_k=max_k)
        except Exception as e:
            print(f"  ERROR [{query_id}] Retrieval failed: {e}")
            results = []
        query_elapsed_ms = (time.perf_counter() - query_start) * 1000.0
        latencies_ms.append(query_elapsed_ms)

        # --- Extract regulation IDs from retrieved chunks ---
        top_k_regulations: list[str] = []
        for result in results:
            reg_id = extract_regulation_id(result)
            top_k_regulations.append(reg_id)

        # --- Build binary relevance list for NDCG ---
        ranked_relevance: list[int] = [
            1 if reg_id in expected_regs else 0
            for reg_id in top_k_regulations
        ]

        # --- Compute reciprocal rank ---
        first_relevant_rank: int | None = None
        for rank, reg_id in enumerate(top_k_regulations, start=1):
            if reg_id in expected_regs:
                first_relevant_rank = rank
                break

        rr = 1.0 / first_relevant_rank if first_relevant_rank is not None else 0.0
        reciprocal_ranks.append(rr)

        # --- Compute Recall@K ---
        query_recall: dict[int, float] = {}
        for k in k_values:
            top_k_slice = set(top_k_regulations[:k])
            hit = 1.0 if top_k_slice & expected_regs else 0.0
            query_recall[k] = hit
            recall_accumulators[k].append(hit)

        # --- Compute NDCG@K ---
        query_ndcg: dict[int, float] = {}
        for k in ndcg_k_values:
            ndcg_val = compute_ndcg(ranked_relevance, k)
            query_ndcg[k] = ndcg_val
            ndcg_accumulators[k].append(ndcg_val)

        # --- Per-query result ---
        status = "OK" if rr > 0 else "MISS"
        rank_str = f"rank {first_relevant_rank}" if first_relevant_rank else "not found"

        per_query_results.append(RetrievalResult(
            query_id=query_id,
            question=question,
            expected_regulations=list(expected_regs),
            top_k_citations=top_k_regulations[:top_k],
            reciprocal_rank=rr,
            recall_at=query_recall,
            ndcg_at=query_ndcg,
            first_relevant_rank=first_relevant_rank,
            category=category,
            latency_ms=query_elapsed_ms,
        ))

        # --- Progress logging ---
        progress = f"[{qi + 1:>3d}/{total}]"
        print(
            f"  {status:<4s} {progress} {query_id:<8s} "
            f"{question[:50]:<50s} -> {rank_str:<15s} "
            f"(RR={rr:.3f}, {query_elapsed_ms:.0f}ms)"
        )

    # --- Aggregate metrics ---
    mrr = float(np.mean(reciprocal_ranks)) if reciprocal_ranks else 0.0
    avg_recall = {
        k: float(np.mean(vals)) if vals else 0.0
        for k, vals in recall_accumulators.items()
    }
    avg_ndcg = {
        k: float(np.mean(vals)) if vals else 0.0
        for k, vals in ndcg_accumulators.items()
    }
    hit_rate = avg_recall.get(1, 0.0)

    # Per-category metrics
    per_category = compute_category_metrics(per_query_results, k_values, ndcg_k_values)

    # Latency stats
    latency_stats = compute_latency_stats(latencies_ms)

    elapsed = time.time() - start_time

    return EvalReport(
        model_name=model_name,
        corpus_size=corpus_size,
        num_queries=len(per_query_results),
        mrr=mrr,
        hit_rate=hit_rate,
        recall_at=avg_recall,
        ndcg_at=avg_ndcg,
        per_query=per_query_results,
        per_category=per_category,
        latency=latency_stats,
        elapsed_seconds=elapsed,
    )


# ---------------------------------------------------------------------------
# Report formatting (mirrors eval_embeddings.py format)
# ---------------------------------------------------------------------------

def format_report(report: EvalReport) -> str:
    """Format evaluation report as human-readable text."""
    lines = [
        "",
        "=" * 70,
        "  QDRANT DIRECT RETRIEVAL EVALUATION REPORT",
        "=" * 70,
        "",
        f"  Model:        {report.model_name}",
        f"  Corpus size:  {report.corpus_size} chunks",
        f"  Queries:      {report.num_queries}",
        f"  Time:         {report.elapsed_seconds:.1f}s",
        "",
        "-" * 70,
        "  AGGREGATE METRICS",
        "-" * 70,
        "",
        f"  MRR (Mean Reciprocal Rank):  {report.mrr:.4f}",
        f"  Hit Rate (Recall@1):         {report.hit_rate:.4f}  ({report.hit_rate * 100:.1f}%)",
    ]

    for k, recall in sorted(report.recall_at.items()):
        lines.append(f"  Recall@{k:<3d}                   {recall:.4f}  ({recall * 100:.1f}%)")

    # NDCG@K
    lines.append("")
    for k, ndcg in sorted(report.ndcg_at.items()):
        lines.append(f"  NDCG@{k:<4d}                   {ndcg:.4f}  ({ndcg * 100:.1f}%)")

    # Latency stats
    if report.latency:
        lines.extend([
            "",
            "-" * 70,
            "  LATENCY (real retrieval: embed + search + rerank)",
            "-" * 70,
            "",
            f"  p50:   {report.latency.p50_ms:8.2f} ms",
            f"  p95:   {report.latency.p95_ms:8.2f} ms",
            f"  p99:   {report.latency.p99_ms:8.2f} ms",
            f"  mean:  {report.latency.mean_ms:8.2f} ms",
            f"  min:   {report.latency.min_ms:8.2f} ms",
            f"  max:   {report.latency.max_ms:8.2f} ms",
        ])

    # Per-category breakdown
    if report.per_category:
        lines.extend([
            "",
            "-" * 70,
            "  PER-CATEGORY METRICS",
            "-" * 70,
            "",
        ])
        # Table header
        header = f"  {'Category':<20s} {'N':>4s} {'MRR':>7s} {'R@1':>7s} {'R@5':>7s} {'R@10':>7s}"
        for k in sorted(report.ndcg_at.keys()):
            header += f" {'NDCG@' + str(k):>8s}"
        lines.append(header)
        lines.append("  " + "-" * (len(header) - 2))

        for cat in report.per_category:
            row = (
                f"  {cat.category:<20s} {cat.num_queries:>4d} "
                f"{cat.mrr:>7.4f} "
                f"{cat.recall_at.get(1, 0.0):>7.4f} "
                f"{cat.recall_at.get(5, 0.0):>7.4f} "
                f"{cat.recall_at.get(10, 0.0):>7.4f}"
            )
            for k in sorted(cat.ndcg_at.keys()):
                row += f" {cat.ndcg_at.get(k, 0.0):>8.4f}"
            lines.append(row)

    # Per-query results
    lines.extend([
        "",
        "-" * 70,
        "  PER-QUERY RESULTS",
        "-" * 70,
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
        "=" * 70,
        f"  SUMMARY: MRR={report.mrr:.4f}  Hit Rate={report.hit_rate * 100:.1f}%  "
        f"Recall@5={report.recall_at.get(5, 0) * 100:.1f}%  "
        f"Recall@10={report.recall_at.get(10, 0) * 100:.1f}%  "
        f"NDCG@5={report.ndcg_at.get(5, 0) * 100:.1f}%  "
        f"NDCG@10={report.ndcg_at.get(10, 0) * 100:.1f}%",
        "=" * 70,
        "",
    ])

    return "\n".join(lines)


def report_to_dict(report: EvalReport) -> dict[str, Any]:
    """Convert report to JSON-serializable dict (same schema as eval_embeddings.py)."""
    result: dict[str, Any] = {
        "model_name": report.model_name,
        "corpus_size": report.corpus_size,
        "num_queries": report.num_queries,
        "mrr": report.mrr,
        "hit_rate": report.hit_rate,
        "recall_at": {str(k): v for k, v in report.recall_at.items()},
        "ndcg_at": {str(k): v for k, v in report.ndcg_at.items()},
        "elapsed_seconds": report.elapsed_seconds,
        "per_query": [
            {
                "query_id": r.query_id,
                "question": r.question,
                "expected_regulations": r.expected_regulations,
                "top_k_citations": r.top_k_citations[:5],
                "reciprocal_rank": r.reciprocal_rank,
                "recall_at": {str(k): v for k, v in r.recall_at.items()},
                "ndcg_at": {str(k): v for k, v in r.ndcg_at.items()},
                "first_relevant_rank": r.first_relevant_rank,
                "category": r.category,
                "latency_ms": r.latency_ms,
            }
            for r in report.per_query
        ],
        "per_category": [
            {
                "category": cat.category,
                "num_queries": cat.num_queries,
                "mrr": cat.mrr,
                "recall_at": {str(k): v for k, v in cat.recall_at.items()},
                "ndcg_at": {str(k): v for k, v in cat.ndcg_at.items()},
            }
            for cat in report.per_category
        ],
    }

    if report.latency:
        result["latency"] = {
            "p50_ms": report.latency.p50_ms,
            "p95_ms": report.latency.p95_ms,
            "p99_ms": report.latency.p99_ms,
            "mean_ms": report.latency.mean_ms,
            "min_ms": report.latency.min_ms,
            "max_ms": report.latency.max_ms,
        }

    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """CLI entry point for Qdrant direct retrieval evaluation."""
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate retrieval quality by querying Qdrant directly "
            "via the production HybridRetriever"
        ),
    )
    parser.add_argument(
        "--qa-file",
        default=str(GOLDEN_QA_PATH),
        help="Path to golden QA JSON (default: tests/deepeval/golden_qa.json)",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="Path to save JSON results (default: eval_results_phase4_qdrant.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print summary only, don't save file",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of results to retrieve per query (default: 10)",
    )

    args = parser.parse_args()

    # --- Load golden QA ---
    print(f"Loading golden QA from {args.qa_file}...")
    golden_qa = load_golden_qa(args.qa_file)
    print(f"Loaded {len(golden_qa)} QA pairs")

    # --- Initialize production retriever ---
    print("\nInitializing production HybridRetriever...")
    try:
        from backend.retriever import HybridRetriever, get_retriever
    except ImportError:
        print("[ERROR] Cannot import backend.retriever. Run from project root:")
        print("  python -m backend.scripts.eval_qdrant_direct")
        return 1

    try:
        retriever = get_retriever()
    except Exception as e:
        print(f"[ERROR] Failed to initialize retriever: {e}")
        print("Ensure Qdrant is running and accessible.")
        return 1

    stats = retriever.get_stats()
    corpus_size = stats.get("total_documents", 0) or stats.get("corpus_loaded", 0)
    print(f"Connected to Qdrant: {corpus_size} chunks in collection '{stats.get('collection_name', 'unknown')}'")

    # --- Run evaluation ---
    print(f"\nEvaluating against Qdrant ({corpus_size} chunks) via production retriever...")
    print(f"  top_k={args.top_k}")
    print()

    report = evaluate_qdrant_direct(
        golden_qa=golden_qa,
        retriever=retriever,
        top_k=args.top_k,
    )

    # --- Print human-readable report ---
    print(format_report(report))

    # --- Save JSON results (unless --dry-run) ---
    if not args.dry_run:
        report_dict = report_to_dict(report)
        output_path = Path(args.output)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        print(f"JSON report written to {output_path}")
    else:
        print("[DRY RUN] Skipping JSON output (use without --dry-run to save)")

    # Return non-zero if MRR is critically low (CI gate)
    if report.mrr < 0.3:
        print(f"\n[WARNING] MRR ({report.mrr:.4f}) is below 0.30 threshold")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
