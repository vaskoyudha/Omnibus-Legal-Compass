"""
Embedding Evaluation Script for Indonesian Legal Corpus.

Benchmarks retrieval quality of the embedding model used in the RAG pipeline.
Runs entirely offline (no Qdrant required) — loads corpus from regulations.json,
embeds queries and documents in-memory, and measures retrieval metrics.

Metrics:
- MRR (Mean Reciprocal Rank): Average of 1/rank for first relevant result
- Recall@K (K=1,3,5,10): Fraction of queries where any relevant doc is in top-K
- Hit Rate: Same as Recall@1
- NDCG@K (K=5,10): Normalized Discounted Cumulative Gain
- Per-category MRR/Recall breakdown
- Latency percentiles (p50, p95, p99)
- Regression detection against baseline (warn >2%, fail >5%)

Usage:
    python -m backend.scripts.eval_embeddings
    python -m backend.scripts.eval_embeddings --model "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    python -m backend.scripts.eval_embeddings --json-report results.json
    python -m backend.scripts.eval_embeddings --baseline baseline.json
"""

import json
import math
import sys
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

import numpy as np


# Constants — must match ingest.py / retriever.py
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
NVIDIA_EMBEDDING_MODEL = "nvidia/nv-embedqa-e5-v5"
JINA_EMBEDDING_MODEL = "jina-embeddings-v3"

# Paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CORPUS_PATH = PROJECT_ROOT / "backend" / "data" / "peraturan" / "merged_corpus.json"
GOLDEN_QA_PATH = PROJECT_ROOT / "tests" / "deepeval" / "golden_qa.json"

# Recall@K values to evaluate
RECALL_K_VALUES = [1, 3, 5, 10]

# NDCG@K values to evaluate
NDCG_K_VALUES = [5, 10]

# Regression detection thresholds
REGRESSION_WARN_THRESHOLD = 0.02  # warn if metric drops by >2%
REGRESSION_FAIL_THRESHOLD = 0.05  # fail if metric drops by >5%


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
class RegressionResult:
    """Result of regression detection against baseline."""

    metric_name: str
    current: float
    baseline: float
    delta: float
    delta_pct: float
    status: str  # "ok", "warn", "fail"


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
    regression: list[RegressionResult] = field(default_factory=list)


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


def detect_regression(
    current_report: dict[str, Any],
    baseline: dict[str, Any],
    warn_threshold: float = REGRESSION_WARN_THRESHOLD,
    fail_threshold: float = REGRESSION_FAIL_THRESHOLD,
) -> list[RegressionResult]:
    """
    Compare current metrics against a baseline JSON report.

    Checks MRR, hit_rate, and each Recall@K / NDCG@K value.
    Returns a RegressionResult per metric with status:
      - "ok": delta <= warn_threshold
      - "warn": warn_threshold < delta <= fail_threshold
      - "fail": delta > fail_threshold
    """
    results: list[RegressionResult] = []

    # Scalar metrics to compare
    scalar_metrics = ["mrr", "hit_rate"]
    for metric in scalar_metrics:
        cur = current_report.get(metric, 0.0)
        base = baseline.get(metric, 0.0)
        delta = cur - base
        delta_pct = (delta / base) if base != 0 else 0.0
        if delta < -fail_threshold:
            status = "fail"
        elif delta < -warn_threshold:
            status = "warn"
        else:
            status = "ok"
        results.append(RegressionResult(
            metric_name=metric, current=cur, baseline=base,
            delta=delta, delta_pct=delta_pct, status=status,
        ))

    # Dict metrics: recall_at, ndcg_at
    for dict_key in ["recall_at", "ndcg_at"]:
        cur_dict = current_report.get(dict_key, {})
        base_dict = baseline.get(dict_key, {})
        all_keys = set(list(cur_dict.keys()) + list(base_dict.keys()))
        for k in sorted(all_keys, key=lambda x: int(x) if x.isdigit() else x):
            cur = float(cur_dict.get(k, 0.0))
            base = float(base_dict.get(k, 0.0))
            delta = cur - base
            delta_pct = (delta / base) if base != 0 else 0.0
            metric_name = f"{dict_key}@{k}"
            if delta < -fail_threshold:
                status = "fail"
            elif delta < -warn_threshold:
                status = "warn"
            else:
                status = "ok"
            results.append(RegressionResult(
                metric_name=metric_name, current=cur, baseline=base,
                delta=delta, delta_pct=delta_pct, status=status,
            ))

    return results


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
    - category (optional): question category, defaults to "factual"
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
    use_nvidia: bool = False,
    use_jina: bool = False,
) -> np.ndarray:
    """
    Embed a list of texts using HuggingFace, NVIDIA NIM, or Jina AI embeddings.

    Provider precedence: Jina > NVIDIA > HuggingFace (matches retriever.py).

    Returns a numpy array of shape (len(texts), embedding_dim).
    Uses the same model as the RAG pipeline to ensure evaluation
    reflects production behavior.
    """
    if use_jina:
        from backend.retriever import JinaEmbedder

        embedder = JinaEmbedder()
    elif use_nvidia:
        from backend.retriever import NVIDIAEmbedder

        embedder = NVIDIAEmbedder()
    else:
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
    ndcg_k_values: list[int] | None = None,
    use_nvidia: bool = False,
    use_jina: bool = False,
) -> EvalReport:
    """
    Run full retrieval evaluation.

    For each golden QA pair:
    1. Embed the question
    2. Compute cosine similarity against all corpus embeddings
    3. Rank corpus documents by similarity
    4. Check if any document from the expected regulation(s) appears in top-K
    5. Compute NDCG@K with binary relevance
    6. Track per-query latency

    Args:
        corpus: List of corpus documents with regulation_key
        golden_qa: List of golden QA pairs with expected regulations
        model_name: Embedding model to evaluate
        k_values: List of K values for Recall@K (default: [1, 3, 5, 10])
        ndcg_k_values: List of K values for NDCG@K (default: [5, 10])
        use_nvidia: Use NVIDIA NIM embeddings
        use_jina: Use Jina AI embeddings (takes precedence over NVIDIA)

    Returns:
        EvalReport with aggregated and per-query metrics
    """
    if k_values is None:
        k_values = list(RECALL_K_VALUES)
    if ndcg_k_values is None:
        ndcg_k_values = list(NDCG_K_VALUES)

    start_time = time.time()

    # Extract corpus texts and regulation keys
    corpus_texts = [doc["text"] for doc in corpus]
    corpus_regulation_keys = [doc["regulation_key"] for doc in corpus]

    # Extract query texts
    query_texts = [qa["question"] for qa in golden_qa]

    print(f"Embedding {len(corpus_texts)} corpus documents...")
    corpus_embeddings = embed_texts(corpus_texts, model_name=model_name, use_nvidia=use_nvidia, use_jina=use_jina)

    print(f"Embedding {len(query_texts)} queries...")
    query_embeddings = embed_texts(query_texts, model_name=model_name, use_nvidia=use_nvidia, use_jina=use_jina)

    print("Computing similarity matrix...")
    sim_matrix = cosine_similarity_matrix(query_embeddings, corpus_embeddings)

    # Evaluate each query
    max_k = max(max(k_values), max(ndcg_k_values))
    per_query_results: list[RetrievalResult] = []
    reciprocal_ranks: list[float] = []
    recall_accumulators: dict[int, list[float]] = {k: [] for k in k_values}
    ndcg_accumulators: dict[int, list[float]] = {k: [] for k in ndcg_k_values}
    latencies_ms: list[float] = []

    for qi, qa in enumerate(golden_qa):
        query_start = time.perf_counter()

        query_id = qa.get("id", f"qa_{qi}")
        question = qa["question"]
        expected_regs = set(qa.get("regulations", []))
        category = qa.get("category", "factual")

        if not expected_regs:
            continue

        # Get similarity scores for this query
        scores = sim_matrix[qi]

        # Rank by descending similarity
        ranked_indices = np.argsort(scores)[::-1]

        # Find first relevant rank and top-K regulation keys
        first_relevant_rank = None
        top_k_reg_keys = []

        # Build binary relevance list for NDCG computation
        ranked_relevance: list[int] = []

        for rank, idx in enumerate(ranked_indices[:max(max_k, 50)], start=1):
            reg_key = corpus_regulation_keys[idx]
            if rank <= max_k:
                top_k_reg_keys.append(reg_key)
                ranked_relevance.append(1 if reg_key in expected_regs else 0)
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

        # Compute NDCG at each K
        query_ndcg: dict[int, float] = {}
        for k in ndcg_k_values:
            ndcg_val = compute_ndcg(ranked_relevance, k)
            query_ndcg[k] = ndcg_val
            ndcg_accumulators[k].append(ndcg_val)

        query_elapsed_ms = (time.perf_counter() - query_start) * 1000.0
        latencies_ms.append(query_elapsed_ms)

        per_query_results.append(RetrievalResult(
            query_id=query_id,
            question=question,
            expected_regulations=list(expected_regs),
            top_k_citations=top_k_reg_keys[:10],
            reciprocal_rank=rr,
            recall_at=query_recall,
            ndcg_at=query_ndcg,
            first_relevant_rank=first_relevant_rank,
            category=category,
            latency_ms=query_elapsed_ms,
        ))

    # Aggregate metrics
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

    effective_model = JINA_EMBEDDING_MODEL if use_jina else (NVIDIA_EMBEDDING_MODEL if use_nvidia else model_name)
    return EvalReport(
        model_name=effective_model,
        corpus_size=len(corpus),
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


def format_report(report: EvalReport) -> str:
    """Format evaluation report as human-readable text."""
    lines = [
        "",
        "=" * 70,
        "  EMBEDDING RETRIEVAL EVALUATION REPORT",
        "=" * 70,
        "",
        f"  Model:        {report.model_name}",
        f"  Corpus size:  {report.corpus_size} articles",
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
            "  LATENCY (per-query ranking, excludes embedding)",
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

    # Regression detection
    if report.regression:
        lines.extend([
            "",
            "-" * 70,
            "  REGRESSION DETECTION",
            "-" * 70,
            "",
        ])
        any_fail = False
        any_warn = False
        for reg in report.regression:
            icon = "  " if reg.status == "ok" else "! " if reg.status == "warn" else "X "
            lines.append(
                f"  {icon}{reg.metric_name:<20s}  "
                f"current={reg.current:.4f}  baseline={reg.baseline:.4f}  "
                f"delta={reg.delta:+.4f} ({reg.delta_pct:+.1%})  [{reg.status.upper()}]"
            )
            if reg.status == "fail":
                any_fail = True
            if reg.status == "warn":
                any_warn = True
        if any_fail:
            lines.append("\n  ** REGRESSION DETECTED: One or more metrics dropped >5% **")
        elif any_warn:
            lines.append("\n  ** WARNING: One or more metrics dropped >2% **")
        else:
            lines.append("\n  All metrics within acceptable range vs baseline.")

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
    """Convert report to JSON-serializable dict."""
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

    if report.regression:
        result["regression"] = [
            {
                "metric_name": reg.metric_name,
                "current": reg.current,
                "baseline": reg.baseline,
                "delta": reg.delta,
                "delta_pct": reg.delta_pct,
                "status": reg.status,
            }
            for reg in report.regression
        ]

    return result


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
    parser.add_argument(
        "--use-nvidia",
        action="store_true",
        default=False,
        help="Use NVIDIA NIM embeddings (nv-embedqa-e5-v5) instead of HuggingFace",
    )
    parser.add_argument(
        "--use-jina",
        action="store_true",
        default=False,
        help="Use Jina AI embeddings (jina-embeddings-v3) instead of HuggingFace",
    )
    parser.add_argument(
        "--baseline",
        default=None,
        help="Path to baseline JSON report for regression detection",
    )

    args = parser.parse_args()

    print(f"Loading corpus from {args.corpus_path}...")
    corpus = load_corpus(args.corpus_path)
    print(f"Loaded {len(corpus)} articles")

    print(f"Loading golden QA from {args.qa_path}...")
    golden_qa = load_golden_qa(args.qa_path)
    print(f"Loaded {len(golden_qa)} QA pairs")

    print(f"\nEvaluating model: {JINA_EMBEDDING_MODEL if args.use_jina else (NVIDIA_EMBEDDING_MODEL if args.use_nvidia else args.model)}")
    report = evaluate_retrieval(
        corpus=corpus,
        golden_qa=golden_qa,
        model_name=args.model,
        use_nvidia=args.use_nvidia,
        use_jina=args.use_jina,
    )

    # Regression detection against baseline
    if args.baseline:
        baseline_path = Path(args.baseline)
        if baseline_path.exists():
            with open(baseline_path, "r", encoding="utf-8") as f:
                baseline_data = json.load(f)
            current_data = report_to_dict(report)
            report.regression = detect_regression(current_data, baseline_data)
            print(f"Regression detection: comparing against {args.baseline}")
        else:
            print(f"[WARNING] Baseline file not found: {args.baseline}")

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

    # Return non-zero if regression detected (>5% drop)
    if any(r.status == "fail" for r in report.regression):
        failed = [r for r in report.regression if r.status == "fail"]
        print(f"\n[FAIL] Regression detected in {len(failed)} metric(s):")
        for r in failed:
            print(f"  {r.metric_name}: {r.baseline:.4f} -> {r.current:.4f} ({r.delta_pct:+.1%})")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
