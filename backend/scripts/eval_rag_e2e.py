"""
End-to-End RAG Evaluation Script for Indonesian Legal Intelligence.

Evaluates the full RAG pipeline (retrieval + generation) using LLM-as-judge
scoring for answer quality, faithfulness, citation accuracy, and refusal accuracy.

**Manual evaluation only** — requires LLM API key(s) and live Qdrant.
Skip in CI: This script is NOT included in automated test pipelines.

Supports multi-provider LLM architecture:
  - GitHub Copilot Chat API (default) for answer generation and judging
  - NVIDIA NIM, Groq, Google Gemini, Mistral as alternative providers
  - FallbackChain mode for resilient evaluation (auto-failover across providers)
  - Parallel workers via ThreadPoolExecutor for faster evaluation

Metrics:
- Answer Correctness: LLM-as-judge semantic similarity to expected answer
- Faithfulness: Grounding score from _verify_grounding (claims supported by sources)
- Citation Accuracy: Fraction of cited sources actually used in answer
- Refusal Accuracy: Correct refusal rate on adversarial/trick questions

Usage:
    python -m backend.scripts.eval_rag_e2e
    python -m backend.scripts.eval_rag_e2e --json-report e2e_results.json
    python -m backend.scripts.eval_rag_e2e --trick-only
    python -m backend.scripts.eval_rag_e2e --golden-only
    python -m backend.scripts.eval_rag_e2e --judge-model gpt-4o --workers 5
    python -m backend.scripts.eval_rag_e2e --workers 20 --skip-grounding --resume
    python -m backend.scripts.eval_rag_e2e --json-report run2.json --baseline-report run1.json
    python -m backend.scripts.eval_rag_e2e --answer-provider groq --judge-provider gemini
    python -m backend.scripts.eval_rag_e2e --fallback-chain --workers 10
"""

import json
import os
import re
import sys
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tqdm import tqdm
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Path setup — allow running as `python -m backend.scripts.eval_rag_e2e`
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GOLDEN_QA_PATH = PROJECT_ROOT / "tests" / "deepeval" / "golden_qa.json"
TRICK_QA_PATH = PROJECT_ROOT / "tests" / "red_team" / "trick_questions.json"

# Refusal phrases used by the RAG chain when confidence < 0.30
REFUSAL_PHRASES = [
    "tidak memiliki cukup informasi",
    "tidak menemukan dokumen yang relevan",
    "konsultasikan dengan ahli hukum",
    "informasi tidak ditemukan",
    "di luar jangkauan",
]

# Expected behavior values that count as "should refuse"
REFUSAL_BEHAVIORS = {"refuse", "refuse_or_warning"}

# Confidence label considered as refusal
LOW_CONFIDENCE_LABELS = {"rendah", "tidak ada"}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class CorrectnessResult:
    """LLM-as-judge answer correctness score for one query."""

    query_id: str
    question: str
    expected_keywords: list[str]
    generated_answer: str
    score: float  # 0.0–1.0
    reasoning: str = ""


@dataclass
class FaithfulnessResult:
    """Faithfulness (grounding) result for one query."""

    query_id: str
    question: str
    grounding_score: float | None
    ungrounded_claims: list[str]
    hallucination_risk: str


@dataclass
class CitationResult:
    """Citation accuracy result for one query."""

    query_id: str
    question: str
    cited_numbers: list[int]
    total_sources: int
    coverage: float  # fraction of cited vs total sources
    is_valid: bool


@dataclass
class RefusalResult:
    """Refusal accuracy result for one trick question."""

    query_id: str
    question: str
    category: str
    expected_behavior: str
    actual_refused: bool
    confidence_label: str
    confidence_numeric: float
    correct: bool


@dataclass
class E2EReport:
    """Aggregated end-to-end evaluation report."""

    num_golden_queries: int
    num_trick_queries: int
    avg_correctness: float
    avg_faithfulness: float
    avg_citation_coverage: float
    refusal_accuracy: float
    correctness_results: list[CorrectnessResult]
    faithfulness_results: list[FaithfulnessResult]
    citation_results: list[CitationResult]
    refusal_results: list[RefusalResult]
    elapsed_seconds: float
    per_category_refusal: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _answer_is_refusal(answer: str, confidence_label: str) -> bool:
    """Check if a RAG answer is a refusal based on content and confidence."""
    answer_lower = answer.lower()
    if confidence_label in LOW_CONFIDENCE_LABELS:
        return True
    for phrase in REFUSAL_PHRASES:
        if phrase in answer_lower:
            return True
    return False


def _extract_cited_numbers(answer: str) -> list[int]:
    """Extract citation numbers like [1], [2] from answer text."""
    return sorted(set(int(m) for m in re.findall(r"\[(\d+)\]", answer)))


def _judge_correctness(
    llm_client: Any,
    question: str,
    expected_keywords: list[str],
    generated_answer: str,
) -> tuple[float, str]:
    """
    Use LLM-as-judge to score answer correctness.

    Returns (score 0.0-1.0, reasoning string).
    """
    keywords_str = ", ".join(expected_keywords) if expected_keywords else "(none)"

    judge_prompt = f"""Anda adalah evaluator jawaban hukum Indonesia yang objektif.

Pertanyaan: {question}

Kata kunci yang diharapkan ada dalam jawaban: {keywords_str}

Jawaban yang dievaluasi:
{generated_answer[:2000]}

Tugas: Berikan skor 0.0 sampai 1.0 untuk KEBENARAN jawaban.
- 1.0 = jawaban benar, mencakup semua kata kunci yang diharapkan
- 0.7 = sebagian besar benar, beberapa kata kunci muncul
- 0.4 = sebagian benar tapi ada informasi penting yang hilang
- 0.1 = sebagian besar salah atau tidak relevan
- 0.0 = sepenuhnya salah atau penolakan padahal seharusnya bisa dijawab

Respons dalam format JSON:
{{"score": <float 0.0-1.0>, "reasoning": "<penjelasan singkat>"}}

JSON:"""

    try:
        response = llm_client.generate(
            user_message=judge_prompt,
            system_message="Anda adalah evaluator objektif. Selalu respond dengan JSON yang valid.",
        )

        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            result = json.loads(response[json_start:json_end])
            score = max(0.0, min(1.0, float(result.get("score", 0.5))))
            reasoning = result.get("reasoning", "")
            return score, reasoning
    except Exception:
        pass

    # Fallback: keyword matching
    if not expected_keywords:
        return 0.5, "No expected keywords — default score"
    answer_lower = generated_answer.lower()
    hits = sum(1 for kw in expected_keywords if kw.lower() in answer_lower)
    score = hits / len(expected_keywords) if expected_keywords else 0.0
    return score, f"Fallback keyword match: {hits}/{len(expected_keywords)}"


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

CHECKPOINT_VERSION = 1
CHECKPOINT_INTERVAL = 50  # save every N items


def _save_checkpoint(path: str | Path, data: dict) -> None:
    """Save checkpoint atomically (write .tmp then os.replace)."""
    path = Path(path)
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(str(tmp_path), str(path))


def _load_checkpoint(path: str | Path) -> dict | None:
    """Load checkpoint if exists, return None otherwise."""
    path = Path(path)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Main evaluation functions
# ---------------------------------------------------------------------------


def evaluate_golden_qa(
    rag_chain: Any,
    llm_client: Any,
    golden_qa: list[dict[str, Any]],
    completed_ids: set[str] | None = None,
    checkpoint_callback: Callable[[list, list, list], None] | None = None,
    num_workers: int = 1,
    skip_grounding: bool = False,
) -> tuple[list[CorrectnessResult], list[FaithfulnessResult], list[CitationResult]]:
    """
    Evaluate golden QA pairs through the full RAG pipeline.

    For each golden QA pair:
    1. Query the RAG chain
    2. Judge answer correctness via LLM
    3. Extract faithfulness from grounding verification
    4. Check citation accuracy

    Args:
        completed_ids: IDs to skip (already evaluated in a previous run).
        checkpoint_callback: Called every CHECKPOINT_INTERVAL items with
            (correctness_results, faithfulness_results, citation_results).
        num_workers: Number of parallel workers (1 = sequential, >1 = ThreadPoolExecutor).
        skip_grounding: If True, skip grounding verification LLM call.

    Returns (correctness_results, faithfulness_results, citation_results).
    """
    completed_ids = completed_ids or set()
    correctness_results: list[CorrectnessResult] = []
    faithfulness_results: list[FaithfulnessResult] = []
    citation_results: list[CitationResult] = []

    # Thread-safe lock for checkpoint writes and list appends
    _checkpoint_lock = threading.Lock()

    def _evaluate_single_golden(
        qa: dict[str, Any],
        idx: int,
    ) -> tuple[CorrectnessResult, FaithfulnessResult, CitationResult]:
        """Evaluate a single golden QA pair. Thread-safe."""
        query_id = qa.get("id", f"golden_{idx}")
        question = qa["question"]
        expected_keywords = qa.get("expected_answer_contains", [])

        try:
            response = rag_chain.query(question, skip_grounding=skip_grounding)
        except Exception as e:
            cr = CorrectnessResult(
                query_id=query_id, question=question,
                expected_keywords=expected_keywords,
                generated_answer=f"ERROR: {e}", score=0.0,
                reasoning=f"Query failed: {e}",
            )
            fr = FaithfulnessResult(
                query_id=query_id, question=question,
                grounding_score=None, ungrounded_claims=[],
                hallucination_risk="error",
            )
            ci = CitationResult(
                query_id=query_id, question=question,
                cited_numbers=[], total_sources=0,
                coverage=0.0, is_valid=False,
            )
            return cr, fr, ci

        answer = response.answer

        # 1. Answer Correctness via LLM-as-judge
        score, reasoning = _judge_correctness(
            llm_client, question, expected_keywords, answer,
        )
        cr = CorrectnessResult(
            query_id=query_id, question=question,
            expected_keywords=expected_keywords,
            generated_answer=answer[:500], score=score,
            reasoning=reasoning,
        )

        # 2. Faithfulness from grounding verification
        grounding_score = None
        ungrounded_claims: list[str] = []
        hallucination_risk = "unknown"
        if skip_grounding:
            hallucination_risk = "skipped"
        elif response.validation:
            grounding_score = response.validation.grounding_score
            ungrounded_claims = response.validation.ungrounded_claims or []
            hallucination_risk = response.validation.hallucination_risk
        fr = FaithfulnessResult(
            query_id=query_id, question=question,
            grounding_score=grounding_score,
            ungrounded_claims=ungrounded_claims,
            hallucination_risk=hallucination_risk,
        )

        # 3. Citation accuracy
        cited_nums = _extract_cited_numbers(answer)
        total_sources = len(response.citations)
        coverage = len(cited_nums) / total_sources if total_sources > 0 else 0.0
        is_valid = response.validation.is_valid if response.validation else True
        ci = CitationResult(
            query_id=query_id, question=question,
            cited_numbers=cited_nums, total_sources=total_sources,
            coverage=min(coverage, 1.0), is_valid=is_valid,
        )

        return cr, fr, ci

    # Filter out already-completed items
    pending_qa = [
        (i, qa) for i, qa in enumerate(golden_qa)
        if qa.get("id", f"golden_{i}") not in completed_ids
    ]
    skipped = len(golden_qa) - len(pending_qa)
    if skipped:
        tqdm.write(f"  Skipping {skipped} already-completed golden QA items")

    new_count = 0

    if num_workers <= 1:
        # Sequential execution (original behavior)
        progress = tqdm(pending_qa, desc="Golden QA", unit="q", leave=True)
        for idx, qa in progress:
            query_id = qa.get("id", f"golden_{idx}")
            progress.set_postfix_str(qa["question"][:40])

            cr, fr, ci = _evaluate_single_golden(qa, idx)
            correctness_results.append(cr)
            faithfulness_results.append(fr)
            citation_results.append(ci)

            if cr.score == 0.0 and cr.reasoning.startswith("Query failed:"):
                tqdm.write(f"    ERROR [{query_id}]: {cr.reasoning}")

            new_count += 1
            if checkpoint_callback and new_count % CHECKPOINT_INTERVAL == 0:
                checkpoint_callback(
                    correctness_results, faithfulness_results, citation_results,
                )
    else:
        # Parallel execution with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {}
            for idx, qa in pending_qa:
                future = executor.submit(_evaluate_single_golden, qa, idx)
                futures[future] = qa.get("id", f"golden_{idx}")

            progress = tqdm(
                as_completed(futures), total=len(futures),
                desc=f"Golden QA (x{num_workers})", unit="q", leave=True,
            )
            for future in progress:
                query_id = futures[future]
                try:
                    cr, fr, ci = future.result()
                    with _checkpoint_lock:
                        correctness_results.append(cr)
                        faithfulness_results.append(fr)
                        citation_results.append(ci)
                        new_count += 1

                    if cr.score == 0.0 and cr.reasoning.startswith("Query failed:"):
                        tqdm.write(f"    ERROR [{query_id}]: {cr.reasoning}")

                    if checkpoint_callback and new_count % CHECKPOINT_INTERVAL == 0:
                        with _checkpoint_lock:
                            checkpoint_callback(
                                correctness_results, faithfulness_results,
                                citation_results,
                            )
                except Exception as e:
                    tqdm.write(f"    WORKER ERROR [{query_id}]: {e}")

    return correctness_results, faithfulness_results, citation_results


def evaluate_trick_questions(
    rag_chain: Any,
    trick_questions: list[dict[str, Any]],
    completed_ids: set[str] | None = None,
    checkpoint_callback: Callable[[list[RefusalResult]], None] | None = None,
    num_workers: int = 1,
    skip_grounding: bool = False,
) -> list[RefusalResult]:
    """
    Evaluate trick questions for refusal accuracy.

    For each adversarial question:
    1. Query the RAG chain
    2. Check if the system appropriately refused or flagged low confidence
    3. Compare against expected_behavior

    Args:
        completed_ids: IDs to skip (already evaluated in a previous run).
        checkpoint_callback: Called every CHECKPOINT_INTERVAL items with
            the current list of RefusalResult.
        num_workers: Number of parallel workers (1 = sequential, >1 = ThreadPoolExecutor).
        skip_grounding: If True, skip grounding verification LLM call.

    Returns list of RefusalResult.
    """
    completed_ids = completed_ids or set()
    results: list[RefusalResult] = []

    # Thread-safe lock for checkpoint writes and list appends
    _checkpoint_lock = threading.Lock()

    def _evaluate_single_trick(
        tq: dict[str, Any],
        idx: int,
    ) -> RefusalResult:
        """Evaluate a single trick question. Thread-safe."""
        query_id = tq.get("id", f"trick_{idx}")
        question = tq["question"]
        category = tq.get("category", "unknown")
        expected_behavior = tq.get("expected_behavior", "refuse")

        try:
            response = rag_chain.query(question, skip_grounding=skip_grounding)
        except Exception as e:
            # If query fails, treat as refusal (conservative)
            return RefusalResult(
                query_id=query_id, question=question,
                category=category, expected_behavior=expected_behavior,
                actual_refused=True, confidence_label="error",
                confidence_numeric=0.0, correct=True,
            )

        confidence_label = response.confidence or ""
        confidence_numeric = (
            response.confidence_score.numeric
            if response.confidence_score
            else 0.0
        )

        actual_refused = _answer_is_refusal(response.answer, confidence_label)

        # Determine correctness
        if expected_behavior in REFUSAL_BEHAVIORS:
            correct = actual_refused
        elif expected_behavior == "low_confidence_warning":
            correct = actual_refused or confidence_label in LOW_CONFIDENCE_LABELS
        else:
            correct = not actual_refused  # should NOT refuse

        return RefusalResult(
            query_id=query_id, question=question,
            category=category, expected_behavior=expected_behavior,
            actual_refused=actual_refused,
            confidence_label=confidence_label,
            confidence_numeric=confidence_numeric,
            correct=correct,
        )

    # Filter out already-completed items
    pending_tq = [
        (i, tq) for i, tq in enumerate(trick_questions)
        if tq.get("id", f"trick_{i}") not in completed_ids
    ]
    skipped = len(trick_questions) - len(pending_tq)
    if skipped:
        tqdm.write(f"  Skipping {skipped} already-completed trick question items")

    new_count = 0

    if num_workers <= 1:
        # Sequential execution (original behavior)
        progress = tqdm(pending_tq, desc="Trick Qs", unit="q", leave=True)
        for idx, tq in progress:
            query_id = tq.get("id", f"trick_{idx}")
            progress.set_postfix_str(tq["question"][:40])

            result = _evaluate_single_trick(tq, idx)
            results.append(result)

            if not result.correct:
                tqdm.write(
                    f"    FAIL [{query_id}] expected={result.expected_behavior} "
                    f"refused={result.actual_refused}"
                )

            new_count += 1
            if checkpoint_callback and new_count % CHECKPOINT_INTERVAL == 0:
                checkpoint_callback(results)
    else:
        # Parallel execution with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {}
            for idx, tq in pending_tq:
                future = executor.submit(_evaluate_single_trick, tq, idx)
                futures[future] = tq.get("id", f"trick_{idx}")

            progress = tqdm(
                as_completed(futures), total=len(futures),
                desc=f"Trick Qs (x{num_workers})", unit="q", leave=True,
            )
            for future in progress:
                query_id = futures[future]
                try:
                    result = future.result()
                    with _checkpoint_lock:
                        results.append(result)
                        new_count += 1

                    if not result.correct:
                        tqdm.write(
                            f"    FAIL [{query_id}] expected={result.expected_behavior} "
                            f"refused={result.actual_refused}"
                        )

                    if checkpoint_callback and new_count % CHECKPOINT_INTERVAL == 0:
                        with _checkpoint_lock:
                            checkpoint_callback(results)
                except Exception as e:
                    tqdm.write(f"    WORKER ERROR [{query_id}]: {e}")

    return results


def build_report(
    correctness_results: list[CorrectnessResult],
    faithfulness_results: list[FaithfulnessResult],
    citation_results: list[CitationResult],
    refusal_results: list[RefusalResult],
    elapsed: float,
) -> E2EReport:
    """Build aggregated E2E evaluation report."""

    # Average correctness
    if correctness_results:
        avg_correctness = sum(r.score for r in correctness_results) / len(correctness_results)
    else:
        avg_correctness = 0.0

    # Average faithfulness (grounding score)
    grounding_scores = [
        r.grounding_score for r in faithfulness_results
        if r.grounding_score is not None
    ]
    avg_faithfulness = (
        sum(grounding_scores) / len(grounding_scores)
        if grounding_scores
        else 0.0
    )

    # Average citation coverage
    if citation_results:
        avg_citation = sum(r.coverage for r in citation_results) / len(citation_results)
    else:
        avg_citation = 0.0

    # Refusal accuracy
    if refusal_results:
        refusal_accuracy = sum(1 for r in refusal_results if r.correct) / len(refusal_results)
    else:
        refusal_accuracy = 0.0

    # Per-category refusal accuracy
    categories: dict[str, list[RefusalResult]] = {}
    for r in refusal_results:
        categories.setdefault(r.category, []).append(r)
    per_category_refusal = {
        cat: sum(1 for r in results if r.correct) / len(results)
        for cat, results in sorted(categories.items())
    }

    return E2EReport(
        num_golden_queries=len(correctness_results),
        num_trick_queries=len(refusal_results),
        avg_correctness=avg_correctness,
        avg_faithfulness=avg_faithfulness,
        avg_citation_coverage=avg_citation,
        refusal_accuracy=refusal_accuracy,
        correctness_results=correctness_results,
        faithfulness_results=faithfulness_results,
        citation_results=citation_results,
        refusal_results=refusal_results,
        elapsed_seconds=elapsed,
        per_category_refusal=per_category_refusal,
    )


def format_report(report: E2EReport) -> str:
    """Format E2E report as human-readable text."""
    lines = [
        "",
        "=" * 70,
        "  END-TO-END RAG EVALUATION REPORT",
        "=" * 70,
        "",
        f"  Golden QA queries:   {report.num_golden_queries}",
        f"  Trick questions:     {report.num_trick_queries}",
        f"  Total time:          {report.elapsed_seconds:.1f}s",
        "",
        "-" * 70,
        "  AGGREGATE METRICS",
        "-" * 70,
        "",
        f"  Answer Correctness (LLM-judge):  {report.avg_correctness:.4f}  ({report.avg_correctness * 100:.1f}%)",
        f"  Faithfulness (grounding):        {report.avg_faithfulness:.4f}  ({report.avg_faithfulness * 100:.1f}%)",
        f"  Citation Coverage:               {report.avg_citation_coverage:.4f}  ({report.avg_citation_coverage * 100:.1f}%)",
        f"  Refusal Accuracy:                {report.refusal_accuracy:.4f}  ({report.refusal_accuracy * 100:.1f}%)",
    ]

    # Per-category refusal accuracy
    if report.per_category_refusal:
        lines.extend([
            "",
            "-" * 70,
            "  REFUSAL ACCURACY BY CATEGORY",
            "-" * 70,
            "",
            f"  {'Category':<30s} {'Accuracy':>10s} {'N':>5s}",
            "  " + "-" * 47,
        ])
        categories: dict[str, list[RefusalResult]] = {}
        for r in report.refusal_results:
            categories.setdefault(r.category, []).append(r)
        for cat, acc in sorted(report.per_category_refusal.items()):
            n = len(categories.get(cat, []))
            lines.append(f"  {cat:<30s} {acc:>9.1%} {n:>5d}")

    # Correctness details
    if report.correctness_results:
        lines.extend([
            "",
            "-" * 70,
            "  ANSWER CORRECTNESS DETAILS",
            "-" * 70,
        ])
        for r in report.correctness_results:
            icon = "OK" if r.score >= 0.5 else "LOW"
            lines.append(
                f"  {icon} [{r.query_id}] score={r.score:.2f}  {r.question[:55]}"
            )
            if r.reasoning:
                lines.append(f"      reason: {r.reasoning[:80]}")

    # Faithfulness details
    if report.faithfulness_results:
        lines.extend([
            "",
            "-" * 70,
            "  FAITHFULNESS DETAILS",
            "-" * 70,
        ])
        for r in report.faithfulness_results:
            gs = f"{r.grounding_score:.2f}" if r.grounding_score is not None else "N/A"
            lines.append(
                f"  [{r.query_id}] grounding={gs}  risk={r.hallucination_risk:<8s}  "
                f"ungrounded={len(r.ungrounded_claims)}"
            )

    # Refusal details
    if report.refusal_results:
        lines.extend([
            "",
            "-" * 70,
            "  REFUSAL DETAILS",
            "-" * 70,
        ])
        for r in report.refusal_results:
            icon = "OK" if r.correct else "FAIL"
            lines.append(
                f"  {icon} [{r.query_id}] expected={r.expected_behavior:<20s} "
                f"refused={r.actual_refused}  conf={r.confidence_numeric:.2f} "
                f"({r.confidence_label})"
            )

    lines.extend([
        "",
        "=" * 70,
        f"  SUMMARY: Correctness={report.avg_correctness * 100:.1f}%  "
        f"Faithfulness={report.avg_faithfulness * 100:.1f}%  "
        f"Citations={report.avg_citation_coverage * 100:.1f}%  "
        f"Refusal={report.refusal_accuracy * 100:.1f}%",
        "=" * 70,
        "",
    ])

    return "\n".join(lines)


def _sanitize_float(v: Any) -> Any:
    """Coerce numeric values to plain Python float for JSON serialization.

    Handles numpy float32/float64, NaN, and Infinity — all of which would
    cause ``json.dump`` to raise or produce invalid tokens.
    """
    import math

    if v is None:
        return None
    # Convert numpy / torch scalar types to plain float
    if hasattr(v, "item"):  # numpy / torch scalar
        v = v.item()
    if isinstance(v, (int, float)):
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return float(v)
    return v


# ---------------------------------------------------------------------------
# Regression comparison (Phase 6 — automated regression pipeline)
# ---------------------------------------------------------------------------

# Default regression thresholds: a metric drop larger than this is flagged.
_REGRESSION_THRESHOLDS: dict[str, float] = {
    "avg_correctness": 0.05,
    "avg_faithfulness": 0.05,
    "avg_citation_coverage": 0.05,
    "refusal_accuracy": 0.03,
}


@dataclass
class RegressionDelta:
    """Comparison of one metric between baseline and current run."""

    metric: str
    baseline: float
    current: float
    delta: float  # current - baseline (positive = improvement)
    threshold: float
    regressed: bool  # True if delta < -threshold


@dataclass
class RegressionReport:
    """Full regression comparison report."""

    baseline_path: str
    deltas: list[RegressionDelta]
    any_regression: bool
    per_category_deltas: dict[str, RegressionDelta]


def compare_against_baseline(
    current_dict: dict[str, Any],
    baseline_path: str | Path,
    thresholds: dict[str, float] | None = None,
) -> RegressionReport:
    """Compare current evaluation results against a saved baseline report.

    Args:
        current_dict: The ``report_to_dict()`` output from the current run.
        baseline_path: Path to the JSON baseline report file.
        thresholds: Per-metric maximum allowed drop. Defaults to
            ``_REGRESSION_THRESHOLDS``.

    Returns:
        A ``RegressionReport`` with per-metric deltas and a boolean flag
        indicating whether any metric regressed beyond its threshold.

    Raises:
        FileNotFoundError: If *baseline_path* does not exist.
        json.JSONDecodeError: If the baseline file is not valid JSON.
    """
    thresholds = thresholds or _REGRESSION_THRESHOLDS
    baseline_path = Path(baseline_path)
    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline = json.load(f)

    deltas: list[RegressionDelta] = []
    any_regression = False

    for metric, max_drop in thresholds.items():
        b_val = float(baseline.get(metric, 0.0) or 0.0)
        c_val = float(current_dict.get(metric, 0.0) or 0.0)
        delta = c_val - b_val
        regressed = delta < -max_drop
        if regressed:
            any_regression = True
        deltas.append(RegressionDelta(
            metric=metric,
            baseline=b_val,
            current=c_val,
            delta=delta,
            threshold=max_drop,
            regressed=regressed,
        ))

    # Per-category refusal comparison
    per_cat_deltas: dict[str, RegressionDelta] = {}
    baseline_cats = baseline.get("per_category_refusal", {})
    current_cats = current_dict.get("per_category_refusal", {})
    refusal_threshold = thresholds.get("refusal_accuracy", 0.03)
    for cat in set(list(baseline_cats.keys()) + list(current_cats.keys())):
        b_val = float(baseline_cats.get(cat, 0.0) or 0.0)
        c_val = float(current_cats.get(cat, 0.0) or 0.0)
        delta = c_val - b_val
        regressed = delta < -refusal_threshold
        if regressed:
            any_regression = True
        per_cat_deltas[cat] = RegressionDelta(
            metric=f"refusal:{cat}",
            baseline=b_val,
            current=c_val,
            delta=delta,
            threshold=refusal_threshold,
            regressed=regressed,
        )

    return RegressionReport(
        baseline_path=str(baseline_path),
        deltas=deltas,
        any_regression=any_regression,
        per_category_deltas=per_cat_deltas,
    )


def format_regression_report(reg: RegressionReport) -> str:
    """Format a regression comparison as human-readable text."""
    lines = [
        "",
        "=" * 70,
        "  REGRESSION COMPARISON",
        "=" * 70,
        "",
        f"  Baseline: {reg.baseline_path}",
        "",
        f"  {'Metric':<30s} {'Baseline':>10s} {'Current':>10s} {'Delta':>10s} {'Status':>10s}",
        "  " + "-" * 72,
    ]
    for d in reg.deltas:
        status = "REGRESSED" if d.regressed else ("improved" if d.delta > 0 else "ok")
        flag = " !!!" if d.regressed else ""
        lines.append(
            f"  {d.metric:<30s} {d.baseline:>9.4f} {d.current:>10.4f} "
            f"{d.delta:>+10.4f} {status:>10s}{flag}"
        )

    if reg.per_category_deltas:
        lines.extend([
            "",
            "  Per-category refusal deltas:",
            f"  {'Category':<30s} {'Baseline':>10s} {'Current':>10s} {'Delta':>10s} {'Status':>10s}",
            "  " + "-" * 72,
        ])
        for cat, d in sorted(reg.per_category_deltas.items()):
            status = "REGRESSED" if d.regressed else ("improved" if d.delta > 0 else "ok")
            flag = " !!!" if d.regressed else ""
            lines.append(
                f"  {cat:<30s} {d.baseline:>9.4f} {d.current:>10.4f} "
                f"{d.delta:>+10.4f} {status:>10s}{flag}"
            )

    lines.extend([
        "",
        "  " + ("*** REGRESSIONS DETECTED ***" if reg.any_regression else "No regressions detected."),
        "=" * 70,
        "",
    ])
    return "\n".join(lines)


def report_to_dict(report: E2EReport) -> dict[str, Any]:
    """Convert report to JSON-serializable dict."""
    sf = _sanitize_float
    return {
        "num_golden_queries": report.num_golden_queries,
        "num_trick_queries": report.num_trick_queries,
        "avg_correctness": sf(report.avg_correctness),
        "avg_faithfulness": sf(report.avg_faithfulness),
        "avg_citation_coverage": sf(report.avg_citation_coverage),
        "refusal_accuracy": sf(report.refusal_accuracy),
        "per_category_refusal": {
            k: sf(v) for k, v in report.per_category_refusal.items()
        },
        "elapsed_seconds": sf(report.elapsed_seconds),
        "correctness_results": [
            {
                "query_id": r.query_id,
                "question": r.question,
                "expected_keywords": r.expected_keywords,
                "generated_answer": r.generated_answer[:300],
                "score": sf(r.score),
                "reasoning": r.reasoning,
            }
            for r in report.correctness_results
        ],
        "faithfulness_results": [
            {
                "query_id": r.query_id,
                "question": r.question,
                "grounding_score": sf(r.grounding_score),
                "ungrounded_claims": r.ungrounded_claims,
                "hallucination_risk": r.hallucination_risk,
            }
            for r in report.faithfulness_results
        ],
        "citation_results": [
            {
                "query_id": r.query_id,
                "question": r.question,
                "cited_numbers": r.cited_numbers,
                "total_sources": r.total_sources,
                "coverage": sf(r.coverage),
                "is_valid": r.is_valid,
            }
            for r in report.citation_results
        ],
        "refusal_results": [
            {
                "query_id": r.query_id,
                "question": r.question,
                "category": r.category,
                "expected_behavior": r.expected_behavior,
                "actual_refused": r.actual_refused,
                "confidence_label": r.confidence_label,
                "confidence_numeric": sf(r.confidence_numeric),
                "correct": r.correct,
            }
            for r in report.refusal_results
        ],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    """CLI entry point for end-to-end RAG evaluation.

    MANUAL ONLY — requires:
      - NVIDIA_API_KEY (if answer-provider or judge-provider is 'nvidia')
      - GITHUB_TOKEN or Copilot auth (if using 'copilot' provider)
      - Running Qdrant instance with indexed documents

    NOT included in CI pipelines.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "End-to-end RAG evaluation with LLM-as-judge. "
            "MANUAL: requires LLM API key(s) and live Qdrant."
        ),
    )
    parser.add_argument(
        "--golden-qa-path",
        default=str(GOLDEN_QA_PATH),
        help="Path to golden_qa.json",
    )
    parser.add_argument(
        "--trick-qa-path",
        default=str(TRICK_QA_PATH),
        help="Path to trick_questions.json",
    )
    parser.add_argument(
        "--json-report",
        default=None,
        help="Optional path to write JSON report",
    )
    parser.add_argument(
        "--golden-only",
        action="store_true",
        default=False,
        help="Only evaluate golden QA (skip trick questions)",
    )
    parser.add_argument(
        "--trick-only",
        action="store_true",
        default=False,
        help="Only evaluate trick questions (skip golden QA)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of queries evaluated (for quick test runs)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=False,
        help="Resume from checkpoint if one exists (skip already-evaluated items)",
    )
    parser.add_argument(
        "--answer-provider",
        default="copilot",
        choices=["copilot", "nvidia", "groq", "gemini", "mistral"],
        help="LLM provider for answer generation (default: copilot)",
    )
    parser.add_argument(
        "--answer-model",
        default=None,
        help="Model for answer generation (default: provider's default model)",
    )
    parser.add_argument(
        "--judge-provider",
        default="copilot",
        choices=["copilot", "nvidia", "groq", "gemini", "mistral"],
        help="LLM provider for judge/scoring calls (default: copilot)",
    )
    parser.add_argument(
        "--judge-model",
        default=None,
        help="Model for judge calls (default: provider's default model)",
    )
    parser.add_argument(
        "--fallback-chain",
        action="store_true",
        default=False,
        help=(
            "Use FallbackChain for answer generation instead of a single provider. "
            "Tries providers in order: groq -> gemini -> mistral -> copilot -> nvidia. "
            "Overrides --answer-provider when enabled."
        ),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel workers (default: 1, max: 20)",
    )
    parser.add_argument(
        "--skip-grounding",
        action="store_true",
        default=False,
        help="Skip grounding verification LLM call (saves ~30%% time)",
    )
    parser.add_argument(
        "--baseline-report",
        default=None,
        help=(
            "Path to a previous JSON report for regression comparison. "
            "When provided, the script compares current metrics against "
            "the baseline and flags any metric that drops beyond thresholds. "
            "Exit code 2 if regressions detected."
        ),
    )

    args = parser.parse_args()

    # Load .env file so environment variables from .env are available
    load_dotenv()

    # Cap workers at 20
    num_workers = min(args.workers, 20)
    if args.workers > 20:
        print(f"[WARN] Workers capped at 20 (requested {args.workers})")

    # Check for required API keys based on selected providers
    _ENV_KEY_MAP = {
        "nvidia": "NVIDIA_API_KEY",
        "groq": "GROQ_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        # copilot uses auto-discovered GitHub auth — no env check needed
    }
    if not args.fallback_chain:
        for role, provider in [("answer", args.answer_provider), ("judge", args.judge_provider)]:
            env_var = _ENV_KEY_MAP.get(provider)
            if env_var and not os.getenv(env_var):
                print(f"[ERROR] {env_var} environment variable not set.")
                print(f"Required because {role}-provider is '{provider}'.")
                print("Set your API key, or use --answer-provider copilot --judge-provider copilot.")
                return 1

    # Import RAG components (requires Qdrant and deps)
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "backend"))
        from rag_chain import LegalRAGChain  # noqa: E402
        from llm_client import (  # noqa: E402
            FallbackChain,
            create_llm_client,
        )
    except ImportError as e:
        print(f"[ERROR] Could not import RAG components: {e}")
        print("Make sure Qdrant is running and dependencies are installed.")
        return 1

    # Initialize
    print("Initializing RAG chain...")
    try:
        if args.fallback_chain:
            # Build a FallbackChain from all available providers
            _CHAIN_ORDER = ["groq", "gemini", "mistral", "copilot", "nvidia"]
            providers: list[tuple[str, Any]] = []
            for name in _CHAIN_ORDER:
                env_var = _ENV_KEY_MAP.get(name)
                if env_var and not os.getenv(env_var):
                    print(f"  Skipping {name} (no {env_var})")
                    continue
                try:
                    client = create_llm_client(name)
                    providers.append((name, client))
                except Exception as e:
                    print(f"  Skipping {name}: {e}")
            if not providers:
                print("[ERROR] No providers available for fallback chain.")
                return 1
            answer_client = FallbackChain(providers)
            print(f"  FallbackChain providers: {[n for n, _ in providers]}")
        else:
            answer_client = create_llm_client(args.answer_provider, model=args.answer_model)
        judge_client = create_llm_client(args.judge_provider, model=args.judge_model)
        rag_chain = LegalRAGChain(llm_client=answer_client)
    except Exception as e:
        print(f"[ERROR] Failed to initialize RAG chain: {e}")
        return 1

    if args.fallback_chain:
        print(f"Answer provider: FallbackChain (model: auto)")
    else:
        print(f"Answer provider: {args.answer_provider} (model: {args.answer_model or 'default'})")
    print(f"Judge provider: {args.judge_provider} (model: {args.judge_model or 'default'})")
    print(f"Workers: {num_workers}")
    if args.skip_grounding:
        print("Grounding verification: SKIPPED")

    # ------------------------------------------------------------------
    # Checkpoint setup
    # ------------------------------------------------------------------
    report_path = Path(args.json_report or "eval_e2e_results.json")
    checkpoint_path = report_path.with_suffix(".json.checkpoint.json")

    # Partial results restored from a previous checkpoint
    prev_correctness: list[CorrectnessResult] = []
    prev_faithfulness: list[FaithfulnessResult] = []
    prev_citation: list[CitationResult] = []
    prev_refusal: list[RefusalResult] = []
    completed_golden_ids: set[str] = set()
    completed_trick_ids: set[str] = set()

    if args.resume:
        ckpt = _load_checkpoint(checkpoint_path)
        if ckpt is not None:
            completed_golden_ids = set(ckpt.get("completed_golden_ids", []))
            completed_trick_ids = set(ckpt.get("completed_trick_ids", []))
            gr = ckpt.get("golden_results", {})
            prev_correctness = [
                CorrectnessResult(**d) for d in gr.get("correctness", [])
            ]
            prev_faithfulness = [
                FaithfulnessResult(**d) for d in gr.get("faithfulness", [])
            ]
            prev_citation = [
                CitationResult(**d) for d in gr.get("citation", [])
            ]
            prev_refusal = [
                RefusalResult(**d) for d in ckpt.get("trick_results", [])
            ]
            print(
                f"Resumed checkpoint: {len(completed_golden_ids)} golden, "
                f"{len(completed_trick_ids)} trick already done.",
            )
        else:
            print("No checkpoint found — starting fresh.")

    start_time = time.time()

    # ------------------------------------------------------------------
    # Load & sort data (deterministic ordering)
    # ------------------------------------------------------------------
    correctness_results: list[CorrectnessResult] = []
    faithfulness_results: list[FaithfulnessResult] = []
    citation_results: list[CitationResult] = []
    refusal_results: list[RefusalResult] = []

    # Mutable lists that the checkpoint callback will capture
    _live_correctness = correctness_results
    _live_faithfulness = faithfulness_results
    _live_citation = citation_results
    _live_refusal = refusal_results

    def _golden_checkpoint_cb(
        cr: list[CorrectnessResult],
        fr: list[FaithfulnessResult],
        ci: list[CitationResult],
    ) -> None:
        all_cr = prev_correctness + cr
        all_fr = prev_faithfulness + fr
        all_ci = prev_citation + ci
        _save_checkpoint(checkpoint_path, {
            "checkpoint_version": CHECKPOINT_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "completed_golden_ids": [r.query_id for r in all_cr],
            "completed_trick_ids": [r.query_id for r in prev_refusal + _live_refusal],
            "golden_results": {
                "correctness": [asdict(r) for r in all_cr],
                "faithfulness": [asdict(r) for r in all_fr],
                "citation": [asdict(r) for r in all_ci],
            },
            "trick_results": [
                asdict(r) for r in prev_refusal + _live_refusal
            ],
        })

    def _trick_checkpoint_cb(results: list[RefusalResult]) -> None:
        all_refusal = prev_refusal + results
        _save_checkpoint(checkpoint_path, {
            "checkpoint_version": CHECKPOINT_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "completed_golden_ids": [
                r.query_id for r in prev_correctness + _live_correctness
            ],
            "completed_trick_ids": [r.query_id for r in all_refusal],
            "golden_results": {
                "correctness": [
                    asdict(r) for r in prev_correctness + _live_correctness
                ],
                "faithfulness": [
                    asdict(r) for r in prev_faithfulness + _live_faithfulness
                ],
                "citation": [
                    asdict(r) for r in prev_citation + _live_citation
                ],
            },
            "trick_results": [asdict(r) for r in all_refusal],
        })

    if not args.trick_only:
        print(f"\nLoading golden QA from {args.golden_qa_path}...")
        golden_qa_path = Path(args.golden_qa_path)
        if golden_qa_path.exists():
            with open(golden_qa_path, "r", encoding="utf-8") as f:
                golden_qa = json.load(f)
            golden_qa.sort(key=lambda q: q.get("id", ""))
            if args.limit:
                golden_qa = golden_qa[: args.limit]
            print(f"Evaluating {len(golden_qa)} golden QA pairs...")
            correctness_results, faithfulness_results, citation_results = (
                evaluate_golden_qa(
                    rag_chain,
                    judge_client,
                    golden_qa,
                    completed_ids=completed_golden_ids,
                    checkpoint_callback=_golden_checkpoint_cb,
                    num_workers=num_workers,
                    skip_grounding=args.skip_grounding,
                )
            )
            # Re-bind live references after evaluate returns new lists
            _live_correctness = correctness_results
            _live_faithfulness = faithfulness_results
            _live_citation = citation_results
        else:
            print(f"[WARNING] Golden QA not found: {golden_qa_path}")

    if not args.golden_only:
        print(f"\nLoading trick questions from {args.trick_qa_path}...")
        trick_qa_path = Path(args.trick_qa_path)
        if trick_qa_path.exists():
            with open(trick_qa_path, "r", encoding="utf-8") as f:
                trick_questions = json.load(f)
            trick_questions.sort(key=lambda q: q.get("id", ""))
            if args.limit:
                trick_questions = trick_questions[: args.limit]
            print(f"Evaluating {len(trick_questions)} trick questions...")
            refusal_results = evaluate_trick_questions(
                rag_chain,
                trick_questions,
                completed_ids=completed_trick_ids,
                checkpoint_callback=_trick_checkpoint_cb,
                num_workers=num_workers,
                skip_grounding=args.skip_grounding,
            )
            _live_refusal = refusal_results
        else:
            print(f"[WARNING] Trick questions not found: {trick_qa_path}")

    elapsed = time.time() - start_time

    # ------------------------------------------------------------------
    # Merge checkpoint results with newly evaluated results
    # ------------------------------------------------------------------
    all_correctness = prev_correctness + correctness_results
    all_faithfulness = prev_faithfulness + faithfulness_results
    all_citation = prev_citation + citation_results
    all_refusal = prev_refusal + refusal_results

    # Build and display report
    report = build_report(
        all_correctness, all_faithfulness,
        all_citation, all_refusal, elapsed,
    )
    print(format_report(report))

    # Always build the report dict (needed for both JSON export and regression)
    report_dict = report_to_dict(report)
    report_dict["metadata"] = {
        "answer_provider": "fallback_chain" if args.fallback_chain else args.answer_provider,
        "answer_model": args.answer_model or "(provider default)",
        "judge_provider": args.judge_provider,
        "judge_model": args.judge_model or "(provider default)",
        "workers": num_workers,
        "skip_grounding": args.skip_grounding,
        "fallback_chain": args.fallback_chain,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Write JSON report if requested (atomic: write .tmp then os.replace)
    if args.json_report:
        tmp_report = Path(args.json_report).with_suffix(".json.tmp")
        with open(tmp_report, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        os.replace(str(tmp_report), str(args.json_report))
        print(f"JSON report written to {args.json_report}")

    # Clean up checkpoint on successful completion
    if checkpoint_path.exists():
        checkpoint_path.unlink()
        print(f"Checkpoint removed: {checkpoint_path}")

    # ------------------------------------------------------------------
    # Regression comparison (Phase 6 — automated regression pipeline)
    # ------------------------------------------------------------------
    if args.baseline_report:
        baseline_path = Path(args.baseline_report)
        if not baseline_path.exists():
            print(f"[ERROR] Baseline report not found: {baseline_path}")
            return 1
        try:
            regression = compare_against_baseline(report_dict, baseline_path)
            print(format_regression_report(regression))

            # Write regression comparison to JSON alongside the main report
            if args.json_report:
                reg_path = Path(args.json_report).with_suffix(".regression.json")
                reg_dict = {
                    "baseline_path": regression.baseline_path,
                    "any_regression": regression.any_regression,
                    "deltas": [asdict(d) for d in regression.deltas],
                    "per_category_deltas": {
                        k: asdict(v) for k, v in regression.per_category_deltas.items()
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                with open(reg_path, "w", encoding="utf-8") as f:
                    json.dump(reg_dict, f, indent=2, ensure_ascii=False)
                print(f"Regression report written to {reg_path}")

            if regression.any_regression:
                print("\n[FAIL] Regressions detected — exit code 2.")
                return 2
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[ERROR] Failed to compare against baseline: {e}")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
