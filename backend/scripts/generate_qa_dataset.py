"""
QA Dataset Generation & Validation Utilities.

LLM-assisted QA generation with automated QC gates for Indonesian legal domain.

Provides functions for generating, validating, merging, and analyzing QA datasets
used in the Indonesian legal AI evaluation pipeline.

Public API:
    - validate_qa_pair: Schema-level validation of a single QA pair
    - merge_qa_datasets: Merge two QA JSON files with semantic deduplication
    - compute_coverage_stats: Analyze regulation/category coverage
    - human_verification_report: Generate markdown checklist for human review

Usage:
    # As library
    from backend.scripts.generate_qa_dataset import (
        validate_qa_pair,
        merge_qa_datasets,
        compute_coverage_stats,
        human_verification_report,
    )

    # CLI — generate QA pairs from regulations
    python -m backend.scripts.generate_qa_dataset \\
        --input priority_regulations.json \\
        --output generated_qa_pairs.json \\
        --start-id 211 --max-regs 5

    # CLI — dry run (validate input, no LLM calls)
    python -m backend.scripts.generate_qa_dataset \\
        --input priority_regulations.json --dry-run --max-regs 3

    # CLI — merge mode
    python -m backend.scripts.generate_qa_dataset --merge \\
        --existing tests/deepeval/golden_qa.json \\
        --input new_pairs.json \\
        --output merged.json

    # CLI — verification report
    python -m backend.scripts.generate_qa_dataset --verification-report \\
        --input tests/deepeval/golden_qa.json \\
        --sample-pct 0.25 \\
        --report-output verification_report.md

    # CLI — coverage stats
    python -m backend.scripts.generate_qa_dataset --stats \\
        --input tests/deepeval/golden_qa.json
"""

from __future__ import annotations

import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

from backend.llm_client import create_llm_client, LLMClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_CATEGORIES: List[str] = [
    "factual",
    "definitional",
    "multi_hop",
    "comparative",
    "temporal",
]

REQUIRED_FIELDS: List[str] = [
    "id",
    "question",
    "expected_answer_contains",
    "regulations",
    "category",
]

QUESTION_MIN_LEN: int = 15
QUESTION_MAX_LEN: int = 300
KEYWORD_MIN_COUNT: int = 2
KEYWORD_MAX_COUNT: int = 5
KEYWORD_MIN_LEN: int = 2
KEYWORD_MAX_LEN: int = 100

DEFAULT_DEDUP_THRESHOLD: float = 0.85
CONTEXT_MAX_CHARS: int = 4000

# NVIDIA NIM configuration (mirrors backend/rag_chain.py)
NVIDIA_API_URL: str = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_MODEL: str = "moonshotai/kimi-k2-instruct"
GENERATION_TEMPERATURE: float = 0.7
GENERATION_MAX_TOKENS: int = 4096

# Retry backoff delays in seconds for 429/5xx
RETRY_DELAYS: List[int] = [5, 10, 20]

# Regulation format pattern: JENIS NOMOR/TAHUN (e.g. UU 40/2007, PP 24/2018)
REGULATION_FORMAT_RE = re.compile(
    r"^(UU|PP|Perpres|Permen|Perda|Kepmen|Keppres|Inpres|SE|Permendagri"
    r"|Permenkes|Permenhub|Perkaban|Permendag|Permenperin|Permentan"
    r"|Permenlhk|Permenaker)\s+\d+/\d{4}$"
)

# Groundedness: minimum fraction of keywords that must appear in source text
GROUNDEDNESS_MIN_RATIO: float = 0.5

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class QAPair(BaseModel):
    """Schema for a single generated QA pair."""

    id: str = ""
    question: str
    expected_answer_contains: List[str]
    regulations: List[str]
    category: str

    @field_validator("category")
    @classmethod
    def _check_category(cls, v: str) -> str:
        if v not in VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category '{v}', must be one of {VALID_CATEGORIES}"
            )
        return v

    @field_validator("expected_answer_contains")
    @classmethod
    def _check_keywords(cls, v: List[str]) -> List[str]:
        if not (KEYWORD_MIN_COUNT <= len(v) <= KEYWORD_MAX_COUNT):
            raise ValueError(
                f"Keyword count {len(v)} outside "
                f"[{KEYWORD_MIN_COUNT}, {KEYWORD_MAX_COUNT}]"
            )
        return v


class RejectedPair(BaseModel):
    """A QA pair that failed one or more QC gates."""

    pair: Dict[str, Any]
    reasons: List[str]
    regulation: str
    gate: str  # which gate rejected it


class GenerationReport(BaseModel):
    """Summary report for a generation run."""

    timestamp: str = ""
    total_regulations_processed: int = 0
    total_pairs_generated: int = 0
    total_pairs_accepted: int = 0
    total_pairs_rejected: int = 0
    total_api_calls: int = 0
    total_api_errors: int = 0
    regulations_skipped: int = 0
    dedup_removed: int = 0
    per_regulation: List[Dict[str, Any]] = Field(default_factory=list)
    category_distribution: Dict[str, int] = Field(default_factory=dict)
    rejection_reasons: Dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# LLM Client — uses shared backend/llm_client.py (no embedded copy)
# ---------------------------------------------------------------------------
# Imported at top: from backend.llm_client import create_llm_client, LLMClient


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------


def build_generation_prompt(
    reg_key: str, context_text: str, judul: str
) -> str:
    """Build Indonesian-language prompt for QA generation."""
    return f"""Anda adalah ahli hukum Indonesia. Berdasarkan teks peraturan berikut, buatlah 3-5 pasangan pertanyaan-jawaban (QA pairs) yang berkualitas tinggi untuk evaluasi sistem AI hukum.

PERATURAN: {reg_key}
JUDUL: {judul}

TEKS SUMBER:
{context_text}

INSTRUKSI:
1. Buat pertanyaan dalam Bahasa Indonesia yang alami dan spesifik
2. Setiap pertanyaan harus bisa dijawab HANYA dari teks sumber di atas
3. Sertakan 2-5 kata kunci jawaban yang HARUS ada dalam teks sumber
4. Setiap pasangan harus memiliki kategori: factual, definitional, multi_hop, comparative, atau temporal
5. Format referensi peraturan: "{reg_key}"
6. Pertanyaan harus realistis — seperti yang akan ditanyakan praktisi hukum atau pelaku usaha

FORMAT OUTPUT (JSON array):
[
  {{
    "question": "Pertanyaan spesifik tentang peraturan ini?",
    "expected_answer_contains": ["kata_kunci_1", "kata_kunci_2", "kata_kunci_3"],
    "regulations": ["{reg_key}"],
    "category": "factual"
  }}
]

PENTING:
- Jawab HANYA dengan JSON array, tanpa teks tambahan
- Pastikan setiap kata kunci benar-benar muncul dalam teks sumber
- Variasikan kategori pertanyaan (jangan semua factual)
- Panjang pertanyaan: 15-300 karakter
- Jumlah kata kunci: 2-5 per pertanyaan
"""


# ---------------------------------------------------------------------------
# QC Gates
# ---------------------------------------------------------------------------


def validate_regulation_format(reg: str) -> bool:
    """Check if regulation string matches JENIS NOMOR/TAHUN format."""
    return bool(REGULATION_FORMAT_RE.match(reg))


def check_groundedness(
    keywords: List[str], source_text: str
) -> Tuple[bool, float, List[str]]:
    """
    Check that keywords are grounded in the source text.

    Returns (is_grounded, ratio, missing_keywords).
    """
    source_lower = source_text.lower()
    missing: List[str] = []
    found = 0
    for kw in keywords:
        if kw.lower() in source_lower:
            found += 1
        else:
            missing.append(kw)
    ratio = found / len(keywords) if keywords else 0.0
    return ratio >= GROUNDEDNESS_MIN_RATIO, ratio, missing


def check_specificity(question: str) -> Tuple[bool, str]:
    """
    Reject overly generic questions.

    A question is considered too generic if it is shorter than 20 chars
    or consists only of very common words.
    """
    if len(question) < 20:
        return False, "question_too_short_for_specificity"
    # Check for overly generic patterns
    generic_patterns = [
        r"^apa itu\?$",
        r"^apa saja\?$",
        r"^bagaimana\?$",
        r"^jelaskan\?$",
    ]
    q_lower = question.lower().strip()
    for pat in generic_patterns:
        if re.match(pat, q_lower):
            return False, f"generic_question_pattern: {pat}"
    return True, ""


def compute_dedup_similarity(
    new_question: str,
    existing_questions: List[str],
    model: Any,
    threshold: float = DEFAULT_DEDUP_THRESHOLD,
) -> Tuple[bool, float]:
    """
    Check if new_question is semantically duplicate of any existing question.

    Returns (is_duplicate, max_similarity).
    """
    if not existing_questions or model is None:
        return False, 0.0

    try:
        from sentence_transformers import util as st_util
    except ImportError:
        logger.warning("sentence-transformers not available, skipping dedup")
        return False, 0.0

    new_emb = model.encode(new_question, convert_to_tensor=True, show_progress_bar=False)
    existing_embs = model.encode(
        existing_questions, convert_to_tensor=True, show_progress_bar=False
    )
    sims = st_util.cos_sim(new_emb, existing_embs)
    max_sim = float(sims.max().item()) if existing_embs.shape[0] > 0 else 0.0
    return max_sim >= threshold, max_sim


def validate_qa_pair_full(
    pair: Dict[str, Any],
    source_text: str,
    existing_questions: List[str],
    dedup_model: Any = None,
    skip_dedup: bool = False,
) -> Tuple[bool, List[str]]:
    """
    Full QC validation with all 7 gates.

    Gates:
        1. Schema validation (Pydantic)
        2. Length constraints (question length)
        3. Category validation
        4. Regulation format validation
        5. Groundedness check
        6. Specificity check
        7. Semantic deduplication

    Returns:
        (is_valid, list_of_rejection_reasons)
    """
    reasons: List[str] = []

    # ── Gate 1: Schema validation (Pydantic) ───────────────────────────
    try:
        QAPair(**pair)
    except Exception as exc:
        reasons.append(f"schema_validation_failed: {exc}")
        return False, reasons

    # ── Gate 2: Length constraints ──────────────────────────────────────
    q_len = len(pair.get("question", ""))
    if not (QUESTION_MIN_LEN <= q_len <= QUESTION_MAX_LEN):
        reasons.append(
            f"question_length_invalid: {q_len} "
            f"(must be {QUESTION_MIN_LEN}-{QUESTION_MAX_LEN})"
        )

    keywords = pair.get("expected_answer_contains", [])
    for kw in keywords:
        if isinstance(kw, str) and not (KEYWORD_MIN_LEN <= len(kw) <= KEYWORD_MAX_LEN):
            reasons.append(
                f"keyword_length_invalid: '{kw}' "
                f"({len(kw)} chars, must be {KEYWORD_MIN_LEN}-{KEYWORD_MAX_LEN})"
            )

    # ── Gate 3: Category validation ────────────────────────────────────
    cat = pair.get("category", "")
    if cat not in VALID_CATEGORIES:
        reasons.append(f"invalid_category: {cat}")

    # ── Gate 4: Regulation format validation ───────────────────────────
    for reg in pair.get("regulations", []):
        if not validate_regulation_format(reg):
            reasons.append(f"invalid_regulation_format: {reg}")

    # ── Gate 5: Groundedness check ─────────────────────────────────────
    if source_text and keywords:
        is_grounded, ratio, missing = check_groundedness(keywords, source_text)
        if not is_grounded:
            reasons.append(
                f"groundedness_failed: ratio={ratio:.2f}, "
                f"missing={missing}"
            )

    # ── Gate 6: Specificity check ──────────────────────────────────────
    question = pair.get("question", "")
    is_specific, spec_reason = check_specificity(question)
    if not is_specific:
        reasons.append(f"specificity_failed: {spec_reason}")

    # ── Gate 7: Semantic deduplication ─────────────────────────────────
    if not skip_dedup and existing_questions:
        is_dup, max_sim = compute_dedup_similarity(
            question, existing_questions, dedup_model
        )
        if is_dup:
            reasons.append(f"semantic_duplicate: max_sim={max_sim:.3f}")

    return len(reasons) == 0, reasons


# ---------------------------------------------------------------------------
# 1. validate_qa_pair (preserved public API — schema-only)
# ---------------------------------------------------------------------------


def validate_qa_pair(pair: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a QA pair against schema requirements.

    Pre-validation check (schema-only) before heavier QC gates.

    Args:
        pair: Dictionary with QA pair data.

    Returns:
        Tuple of ``(is_valid, list_of_reasons_if_invalid)``.
        When valid, returns ``(True, [])``.

    Example:
        >>> validate_qa_pair({
        ...     "id": "qa_001",
        ...     "question": "Apa syarat pendirian PT?",
        ...     "expected_answer_contains": ["2 orang", "akta notaris", "modal"],
        ...     "regulations": ["UU 40/2007"],
        ...     "category": "factual",
        ... })
        (True, [])
        >>> validate_qa_pair({"id": "qa_001"})
        (False, ['missing_field: question', ...])
    """
    reasons: List[str] = []

    # ── Required fields ────────────────────────────────────────────────
    for fld in REQUIRED_FIELDS:
        if fld not in pair:
            reasons.append(f"missing_field: {fld}")

    # ── Type checks ────────────────────────────────────────────────────
    if "expected_answer_contains" in pair and not isinstance(
        pair["expected_answer_contains"], list
    ):
        reasons.append("expected_answer_contains must be a list")

    if "regulations" in pair and not isinstance(pair["regulations"], list):
        reasons.append("regulations must be a list")

    # ── Question length ────────────────────────────────────────────────
    if "question" in pair:
        q_len = len(pair["question"])
        if not (QUESTION_MIN_LEN <= q_len <= QUESTION_MAX_LEN):
            reasons.append(
                f"question_length_invalid: {q_len} "
                f"(must be {QUESTION_MIN_LEN}-{QUESTION_MAX_LEN})"
            )

    # ── Keyword count & length ─────────────────────────────────────────
    if "expected_answer_contains" in pair and isinstance(
        pair["expected_answer_contains"], list
    ):
        keywords: List[str] = pair["expected_answer_contains"]
        kw_count = len(keywords)
        if not (KEYWORD_MIN_COUNT <= kw_count <= KEYWORD_MAX_COUNT):
            reasons.append(
                f"keyword_count_invalid: {kw_count} "
                f"(must be {KEYWORD_MIN_COUNT}-{KEYWORD_MAX_COUNT})"
            )
        for kw in keywords:
            if isinstance(kw, str) and not (KEYWORD_MIN_LEN <= len(kw) <= KEYWORD_MAX_LEN):
                reasons.append(
                    f"keyword_length_invalid: '{kw}' "
                    f"({len(kw)} chars, must be {KEYWORD_MIN_LEN}-{KEYWORD_MAX_LEN})"
                )

    # ── Category check ─────────────────────────────────────────────────
    if "category" in pair and pair["category"] not in VALID_CATEGORIES:
        reasons.append(
            f"invalid_category: {pair['category']} "
            f"(must be one of {VALID_CATEGORIES})"
        )

    return (len(reasons) == 0, reasons)


# ---------------------------------------------------------------------------
# 2. compute_coverage_stats
# ---------------------------------------------------------------------------


def compute_coverage_stats(qa_path: str | Path) -> Dict[str, Any]:
    """
    Compute coverage statistics for a QA dataset.

    Analyzes regulation coverage, category distribution, and document-type
    breakdown from a golden QA JSON file.

    Args:
        qa_path: Path to QA dataset JSON (list of QA pair dicts).

    Returns:
        Dictionary with coverage metrics::

            {
                "total_pairs": int,
                "unique_regulations": int,
                "category_distribution": {
                    "counts": {"factual": 88, ...},
                    "percentages": {"factual": 41.9, ...},
                },
                "doc_type_distribution": {"UU": 120, "PP": 30, ...},
                "pairs_per_regulation": {"min": 1, "max": 8, "avg": 2.3},
            }
    """
    qa_path = Path(qa_path)
    with open(qa_path, "r", encoding="utf-8") as f:
        qa_pairs: List[Dict[str, Any]] = json.load(f)

    regulations: set[str] = set()
    categories: Dict[str, int] = {}
    doc_types: Dict[str, int] = {}
    pairs_per_reg: Dict[str, int] = {}

    for pair in qa_pairs:
        # Regulations
        for reg in pair.get("regulations", []):
            regulations.add(reg)
            pairs_per_reg[reg] = pairs_per_reg.get(reg, 0) + 1

            # Doc type: first token before space (UU, PP, Perpres, etc.)
            doc_type = reg.split()[0] if " " in reg else "unknown"
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1

        # Categories
        cat = pair.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    total_pairs = len(qa_pairs)
    category_pct: Dict[str, float] = {}
    if total_pairs > 0:
        category_pct = {k: (v / total_pairs) * 100 for k, v in categories.items()}

    pairs_counts = list(pairs_per_reg.values())

    return {
        "total_pairs": total_pairs,
        "unique_regulations": len(regulations),
        "category_distribution": {
            "counts": categories,
            "percentages": category_pct,
        },
        "doc_type_distribution": doc_types,
        "pairs_per_regulation": {
            "min": min(pairs_counts) if pairs_counts else 0,
            "max": max(pairs_counts) if pairs_counts else 0,
            "avg": (
                sum(pairs_counts) / len(pairs_counts) if pairs_counts else 0.0
            ),
        },
    }


# ---------------------------------------------------------------------------
# 3. merge_qa_datasets
# ---------------------------------------------------------------------------


def merge_qa_datasets(
    existing_path: str | Path,
    new_path: str | Path,
    output_path: str | Path,
    dedup_threshold: float = DEFAULT_DEDUP_THRESHOLD,
) -> Dict[str, Any]:
    """
    Merge two QA datasets with semantic deduplication.

    Loads ``existing_path`` and ``new_path`` JSON files, uses a sentence
    transformer to compute cosine similarity between questions, and only
    adds new pairs whose maximum similarity to any existing question is
    below ``dedup_threshold``.

    The merged dataset is validated and written to ``output_path``.

    Args:
        existing_path: Path to existing golden QA JSON.
        new_path: Path to newly generated QA pairs JSON.
        output_path: Where to write the merged dataset.
        dedup_threshold: Cosine similarity threshold for duplicate detection
            (default ``0.85``). Pairs above this threshold are considered
            duplicates and skipped.

    Returns:
        Statistics dictionary::

            {
                "total_pairs": int,
                "new_added": int,
                "duplicates_removed": int,
                "unique_regulations": int,
                "category_distribution": {...},
                ...
            }

    Raises:
        ValueError: If any pair in the merged dataset fails validation.
        ImportError: If ``sentence-transformers`` is not installed.
    """
    try:
        from sentence_transformers import SentenceTransformer, util as st_util
    except ImportError as exc:
        raise ImportError(
            "sentence-transformers is required for merge_qa_datasets. "
            "Install with: pip install sentence-transformers"
        ) from exc

    existing_path = Path(existing_path)
    new_path = Path(new_path)
    output_path = Path(output_path)

    # Load datasets
    with open(existing_path, "r", encoding="utf-8") as f:
        existing: List[Dict[str, Any]] = json.load(f)

    with open(new_path, "r", encoding="utf-8") as f:
        new_pairs: List[Dict[str, Any]] = json.load(f)

    if not new_pairs:
        # Nothing to merge — write existing as-is
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        stats = compute_coverage_stats(output_path)
        stats.update({"new_added": 0, "duplicates_removed": 0})
        return stats

    # Initialise dedup model
    model = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")

    # Encode existing questions
    existing_questions = [pair["question"] for pair in existing]
    existing_embeddings = model.encode(
        existing_questions, convert_to_tensor=True, show_progress_bar=False
    )

    added = 0
    duplicates = 0

    for new_pair in new_pairs:
        new_embedding = model.encode(
            new_pair["question"], convert_to_tensor=True, show_progress_bar=False
        )
        similarities = st_util.cos_sim(new_embedding, existing_embeddings)

        max_sim = float(similarities.max().item()) if existing_embeddings.shape[0] > 0 else 0.0

        if max_sim < dedup_threshold:
            existing.append(new_pair)
            added += 1
            # Update embeddings tensor for subsequent comparisons
            import torch

            existing_embeddings = torch.cat(
                [existing_embeddings, new_embedding.unsqueeze(0)]
            )
        else:
            duplicates += 1

    # Sort by ID
    existing.sort(key=lambda x: x.get("id", ""))

    # Validate every pair in the merged dataset
    for pair in existing:
        is_valid, reasons = validate_qa_pair(pair)
        if not is_valid:
            raise ValueError(
                f"Invalid pair in merged dataset: {pair.get('id', '?')} — {reasons}"
            )

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    # Compute final stats
    stats = compute_coverage_stats(output_path)
    stats.update({
        "new_added": added,
        "duplicates_removed": duplicates,
    })
    return stats


# ---------------------------------------------------------------------------
# 4. human_verification_report
# ---------------------------------------------------------------------------


def human_verification_report(
    qa_path: str | Path,
    sample_pct: float,
    output_path: str | Path | None = None,
) -> str:
    """
    Generate a markdown report with checkboxes for human verification.

    Samples a percentage of QA pairs and produces a structured markdown
    document that reviewers can use to accept/reject individual pairs.

    Args:
        qa_path: Path to QA dataset JSON.
        sample_pct: Fraction of pairs to sample (``0.0``–``1.0``).
        output_path: Optional path to write the report. If ``None``, the
            report is only returned as a string.

    Returns:
        Markdown-formatted report string.
    """
    qa_path = Path(qa_path)
    with open(qa_path, "r", encoding="utf-8") as f:
        qa_pairs: List[Dict[str, Any]] = json.load(f)

    # Clamp sample_pct
    sample_pct = max(0.0, min(1.0, sample_pct))
    sample_size = max(1, int(len(qa_pairs) * sample_pct))
    sampled = random.sample(qa_pairs, min(sample_size, len(qa_pairs)))

    lines: List[str] = [
        "# Human Verification Report",
        "",
        f"**Dataset**: `{qa_path}`",
        f"**Total pairs**: {len(qa_pairs)}",
        f"**Sample size**: {sample_size} ({sample_pct * 100:.1f}%)",
        "",
        "## Verification Checklist",
        "",
        "For each QA pair below, verify:",
        "- [ ] **Answerability**: Can the question be answered from the source regulation?",
        "- [ ] **Citation accuracy**: Are the expected keywords actually in the regulation text?",
        "- [ ] **Question clarity**: Is there only ONE correct interpretation?",
        "- [ ] **Answer completeness**: Do the keywords fully address the question?",
        "- [ ] **Domain realism**: Would compliance practitioners ask this?",
        "",
        "---",
        "",
    ]

    for i, pair in enumerate(sampled, 1):
        pair_id = pair.get("id", f"unknown_{i}")
        regs = ", ".join(pair.get("regulations", []))
        category = pair.get("category", "unknown")
        question = pair.get("question", "")
        keywords: List[str] = pair.get("expected_answer_contains", [])

        lines.extend([
            "",
            f"### QA Pair {i}/{sample_size}: `{pair_id}`",
            "",
            f"**Regulation(s)**: {regs}",
            f"**Category**: {category}",
            "",
            "**Question**:",
            f"> {question}",
            "",
            "**Expected answer keywords**:",
            "",
        ])

        for kw in keywords:
            lines.append(f"- `{kw}`")

        lines.extend([
            "",
            "**Verification** (check all that apply):",
            "- [ ] Answerable from source",
            "- [ ] Keywords present in regulation",
            "- [ ] Question is clear and unambiguous",
            "- [ ] Answer complete",
            "- [ ] Domain realistic",
            "",
            "**Action**: ACCEPT / REJECT",
            "",
            "**Notes**:",
            "",
            "---",
            "",
        ])

    report = "\n".join(lines)

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)

    return report


# ---------------------------------------------------------------------------
# Helper functions for generation
# ---------------------------------------------------------------------------


def prepare_context(chunks: List[str], max_chars: int = CONTEXT_MAX_CHARS) -> str:
    """Concatenate regulation chunks up to max_chars."""
    context_parts: List[str] = []
    total = 0
    for chunk in chunks:
        if total + len(chunk) > max_chars:
            remaining = max_chars - total
            if remaining > 100:  # only add if meaningful
                context_parts.append(chunk[:remaining])
            break
        context_parts.append(chunk)
        total += len(chunk)
    return "\n\n".join(context_parts)


def build_reg_key(reg: Dict[str, Any]) -> str:
    """Build regulation key from regulation metadata (JENIS NOMOR/TAHUN)."""
    return reg.get("reg_key", f"{reg.get('jenis_dokumen', '?')} {reg.get('nomor', '?')}/{reg.get('tahun', '?')}")


def parse_llm_response(raw: str) -> List[Dict[str, Any]]:
    """
    Parse LLM response into list of QA pair dicts.

    Handles:
    - Raw JSON array
    - JSON wrapped in ```json ... ``` code blocks
    - JSON with trailing text
    """
    text = raw.strip()

    # Try to extract from code blocks first
    code_block_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if code_block_match:
        text = code_block_match.group(1).strip()

    # Find the JSON array
    bracket_start = text.find("[")
    bracket_end = text.rfind("]")
    if bracket_start != -1 and bracket_end != -1 and bracket_end > bracket_start:
        text = text[bracket_start : bracket_end + 1]

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            return [parsed]
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse LLM response as JSON: %s", exc)

    return []


# ---------------------------------------------------------------------------
# Per-regulation generation
# ---------------------------------------------------------------------------


def generate_qa_for_regulation(
    reg: Dict[str, Any],
    client: LLMClient,
    start_id: int,
    existing_questions: List[str],
    dedup_model: Any,
    skip_dedup: bool,
    report: GenerationReport,
    rejected_pairs: List[RejectedPair],
) -> List[Dict[str, Any]]:
    """
    Generate QA pairs for a single regulation.

    Returns list of accepted QA pair dicts with assigned IDs.
    """
    reg_key = build_reg_key(reg)
    judul = reg.get("judul", reg.get("tentang", ""))
    chunks = reg.get("chunks", [])

    if not chunks:
        logger.warning("Regulation %s has no chunks, skipping", reg_key)
        report.regulations_skipped += 1
        return []

    context_text = prepare_context(chunks)
    prompt = build_generation_prompt(reg_key, context_text, judul)

    # Call LLM
    report.total_api_calls += 1
    try:
        raw_response = client.generate(prompt)
    except RuntimeError as exc:
        logger.error("API failed for %s: %s", reg_key, exc)
        report.total_api_errors += 1
        return []

    # Parse response
    raw_pairs = parse_llm_response(raw_response)
    if not raw_pairs:
        logger.warning("No parseable QA pairs from LLM for %s", reg_key)
        report.total_api_errors += 1
        return []

    report.total_pairs_generated += len(raw_pairs)

    accepted: List[Dict[str, Any]] = []
    current_id = start_id

    reg_stats: Dict[str, Any] = {
        "regulation": reg_key,
        "generated": len(raw_pairs),
        "accepted": 0,
        "rejected": 0,
    }

    for raw_pair in raw_pairs:
        # Ensure regulations field uses the canonical reg_key
        if "regulations" not in raw_pair:
            raw_pair["regulations"] = [reg_key]

        # Assign ID
        pair_id = f"qa_{current_id:03d}"
        raw_pair["id"] = pair_id

        # Run full QC gates
        is_valid, reasons = validate_qa_pair_full(
            pair=raw_pair,
            source_text=context_text,
            existing_questions=existing_questions,
            dedup_model=dedup_model,
            skip_dedup=skip_dedup,
        )

        if is_valid:
            accepted.append(raw_pair)
            existing_questions.append(raw_pair["question"])
            current_id += 1
            reg_stats["accepted"] += 1
            report.total_pairs_accepted += 1

            # Track category distribution
            cat = raw_pair.get("category", "unknown")
            report.category_distribution[cat] = (
                report.category_distribution.get(cat, 0) + 1
            )
        else:
            gate = reasons[0].split(":")[0] if reasons else "unknown"
            rejected_pairs.append(
                RejectedPair(
                    pair=raw_pair,
                    reasons=reasons,
                    regulation=reg_key,
                    gate=gate,
                )
            )
            reg_stats["rejected"] += 1
            report.total_pairs_rejected += 1

            # Track rejection reasons
            for reason in reasons:
                reason_key = reason.split(":")[0]
                report.rejection_reasons[reason_key] = (
                    report.rejection_reasons.get(reason_key, 0) + 1
                )

            logger.info(
                "Rejected pair for %s: %s", reg_key, reasons
            )

    report.per_regulation.append(reg_stats)
    return accepted


# ---------------------------------------------------------------------------
# Dry run
# ---------------------------------------------------------------------------


def run_dry_run(
    regulations: List[Dict[str, Any]], max_regs: Optional[int]
) -> int:
    """Validate input data without making LLM calls. Returns exit code."""
    regs_to_check = regulations[:max_regs] if max_regs else regulations

    print(f"\n=== DRY RUN — Validating {len(regs_to_check)} regulations ===\n")

    issues = 0
    for i, reg in enumerate(regs_to_check):
        reg_key = build_reg_key(reg)
        chunks = reg.get("chunks", [])
        context = prepare_context(chunks)

        problems: List[str] = []
        if not chunks:
            problems.append("no chunks")
        if not reg.get("judul") and not reg.get("tentang"):
            problems.append("missing judul/tentang")
        if not validate_regulation_format(reg_key):
            problems.append(f"invalid reg_key format: {reg_key}")
        if len(context) < 50:
            problems.append(f"context too short: {len(context)} chars")

        status = "OK" if not problems else f"ISSUES: {', '.join(problems)}"
        print(f"  [{i+1}/{len(regs_to_check)}] {reg_key}: {status}")
        if problems:
            issues += 1

        # Show prompt preview for first regulation
        if i == 0:
            prompt = build_generation_prompt(
                reg_key, context, reg.get("judul", reg.get("tentang", ""))
            )
            print(f"\n  --- Prompt preview (first reg, {len(prompt)} chars) ---")
            print(f"  {prompt[:500]}...")
            print("  --- End preview ---\n")

    print(f"\nDry run complete: {len(regs_to_check) - issues}/{len(regs_to_check)} regulations OK")
    if issues:
        print(f"  {issues} regulation(s) with issues")
    return 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> int:
    """CLI entry point for QA dataset generation & utilities."""
    import argparse

    parser = argparse.ArgumentParser(
        description="QA dataset generation, validation, merge & coverage utilities",
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to input (priority_regulations.json for generation, QA JSON for utilities)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to write output (generated pairs or merged dataset)",
    )

    # ── Generation mode flags ──────────────────────────────────────────
    parser.add_argument(
        "--start-id",
        type=int,
        default=211,
        help="Starting QA pair ID number (default: 211)",
    )
    parser.add_argument(
        "--max-regs",
        type=int,
        default=None,
        help="Maximum number of regulations to process",
    )
    parser.add_argument(
        "--skip-first",
        type=int,
        default=0,
        help="Skip the first N regulations",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1,
        help="Number of regulations per batch (default: 1)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay in seconds between API calls (default: 2.0)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate input without making LLM calls",
    )
    parser.add_argument(
        "--skip-dedup",
        action="store_true",
        help="Skip semantic deduplication (faster, less accurate)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing output file (skip already-processed regulations)",
    )
    parser.add_argument(
        "--report-path",
        type=str,
        default=None,
        help="Path for generation report JSON (default: <output_dir>/generation_report.json)",
    )
    parser.add_argument(
        "--rejected-path",
        type=str,
        default=None,
        help="Path for rejected pairs JSON (default: <output_dir>/rejected_pairs.json)",
    )

    # ── Merge mode ─────────────────────────────────────────────────────
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge mode: merge new pairs into existing dataset",
    )
    parser.add_argument(
        "--existing",
        type=str,
        default=None,
        help="Path to existing QA dataset (for merge mode)",
    )
    parser.add_argument(
        "--dedup-threshold",
        type=float,
        default=DEFAULT_DEDUP_THRESHOLD,
        help=f"Cosine similarity threshold for duplicates (default: {DEFAULT_DEDUP_THRESHOLD})",
    )

    # ── Verification report ────────────────────────────────────────────
    parser.add_argument(
        "--verification-report",
        action="store_true",
        help="Generate human verification report",
    )
    parser.add_argument(
        "--sample-pct",
        type=float,
        default=0.25,
        help="Percentage to sample for verification (0.0-1.0, default: 0.25)",
    )
    parser.add_argument(
        "--report-output",
        type=str,
        default="verification_report.md",
        help="Verification report output path (default: verification_report.md)",
    )

    # ── Coverage stats ─────────────────────────────────────────────────
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print coverage statistics for the input dataset",
    )

    # ── Validate ───────────────────────────────────────────────────────
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate all pairs in the input dataset",
    )

    args = parser.parse_args()

    # ── Merge ──────────────────────────────────────────────────────────
    if args.merge:
        if not args.existing:
            print("ERROR: --merge requires --existing path", file=sys.stderr)
            return 1
        if not args.output:
            print("ERROR: --merge requires --output path", file=sys.stderr)
            return 1

        stats = merge_qa_datasets(
            existing_path=args.existing,
            new_path=args.input,
            output_path=args.output,
            dedup_threshold=args.dedup_threshold,
        )
        print("Merge complete:")
        print(f"  Total pairs:        {stats['total_pairs']}")
        print(f"  New added:          {stats['new_added']}")
        print(f"  Duplicates removed: {stats['duplicates_removed']}")
        print(f"  Unique regulations: {stats['unique_regulations']}")
        cat_counts = stats.get("category_distribution", {}).get("counts", {})
        if cat_counts:
            print("  Category distribution:")
            for cat, count in sorted(cat_counts.items()):
                print(f"    {cat}: {count}")
        return 0

    # ── Verification report ────────────────────────────────────────────
    if args.verification_report:
        report_out = args.report_output
        report = human_verification_report(
            qa_path=args.input,
            sample_pct=args.sample_pct,
            output_path=report_out,
        )
        print(f"Verification report written to: {report_out}")
        print(f"Report length: {len(report)} characters")
        return 0

    # ── Coverage stats ─────────────────────────────────────────────────
    if args.stats:
        stats = compute_coverage_stats(args.input)
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        return 0

    # ── Validate ───────────────────────────────────────────────────────
    if args.validate:
        with open(args.input, "r", encoding="utf-8") as f:
            qa_pairs: List[Dict[str, Any]] = json.load(f)

        invalid_count = 0
        for pair in qa_pairs:
            is_valid, reasons = validate_qa_pair(pair)
            if not is_valid:
                invalid_count += 1
                pair_id = pair.get("id", "?")
                print(f"INVALID [{pair_id}]: {reasons}")

        total = len(qa_pairs)
        valid_count = total - invalid_count
        print(f"\nValidation: {valid_count}/{total} pairs valid")
        if invalid_count > 0:
            print(f"  {invalid_count} invalid pair(s) found")
            return 1
        print("  All pairs valid!")
        return 0

    # ── Dry run ────────────────────────────────────────────────────────
    if args.dry_run:
        input_path = Path(args.input)
        with open(input_path, "r", encoding="utf-8") as f:
            regulations: List[Dict[str, Any]] = json.load(f)

        # Apply skip_first
        regulations = regulations[args.skip_first :]
        return run_dry_run(regulations, args.max_regs)

    # ── Generation mode (default) ──────────────────────────────────────
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        return 1

    output_path = Path(args.output) if args.output else input_path.parent / "generated_qa_pairs.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report_path = Path(args.report_path) if args.report_path else output_path.parent / "generation_report.json"
    rejected_path = Path(args.rejected_path) if args.rejected_path else output_path.parent / "rejected_pairs.json"

    # Load regulations
    with open(input_path, "r", encoding="utf-8") as f:
        regulations = json.load(f)

    # Apply skip_first and max_regs
    regulations = regulations[args.skip_first :]
    if args.max_regs:
        regulations = regulations[: args.max_regs]

    if not regulations:
        print("ERROR: No regulations to process after skip/max filters", file=sys.stderr)
        return 1

    print(f"\n=== QA Generation Pipeline ===")
    print(f"  Input: {input_path}")
    print(f"  Output: {output_path}")
    print(f"  Regulations: {len(regulations)}")
    print(f"  Start ID: {args.start_id}")
    print(f"  Delay: {args.delay}s")
    print(f"  Skip dedup: {args.skip_dedup}")
    print()

    # Initialize client
    client = create_llm_client(provider="nvidia")

    # Initialize dedup model
    dedup_model = None
    if not args.skip_dedup:
        try:
            from sentence_transformers import SentenceTransformer
            dedup_model = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")
            logger.info("Dedup model loaded: paraphrase-multilingual-mpnet-base-v2")
        except ImportError:
            logger.warning(
                "sentence-transformers not available, disabling dedup"
            )
            args.skip_dedup = True

    # Track state
    report = GenerationReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    rejected_list: List[RejectedPair] = []
    all_accepted: List[Dict[str, Any]] = []
    existing_questions: List[str] = []
    next_id = args.start_id

    # Resume: load existing output and skip processed regulations
    previously_accepted: List[Dict[str, Any]] = []
    processed_reg_keys: set[str] = set()

    if args.resume and output_path.exists():
        with open(output_path, "r", encoding="utf-8") as f:
            previously_accepted = json.load(f)

        # Extract processed regulation keys
        for pair in previously_accepted:
            for reg in pair.get("regulations", []):
                processed_reg_keys.add(reg)

        # Compute next_id from existing pairs
        max_numeric = 0
        for pair in previously_accepted:
            pair_id = pair.get("id", "")
            match = re.match(r"qa_(\d+)", pair_id)
            if match:
                max_numeric = max(max_numeric, int(match.group(1)))
        if max_numeric > 0:
            next_id = max_numeric + 1

        # Also seed existing_questions for dedup
        existing_questions = [p.get("question", "") for p in previously_accepted]

        # Filter regulations to skip already-processed ones
        original_count = len(regulations)
        regulations = [r for r in regulations if build_reg_key(r) not in processed_reg_keys]

        logger.info(
            "Resume: loaded %d existing pairs from %s, "
            "skipping %d already-processed regulations, "
            "continuing with %d remaining, next_id=%d",
            len(previously_accepted),
            output_path,
            original_count - len(regulations),
            len(regulations),
            next_id,
        )

    # Import tqdm for progress
    try:
        from tqdm import tqdm
        reg_iter = tqdm(regulations, desc="Generating QA pairs", unit="reg")
    except ImportError:
        logger.warning("tqdm not available, using plain iteration")
        reg_iter = regulations

    # Main generation loop
    for reg in reg_iter:
        reg_key = build_reg_key(reg)
        report.total_regulations_processed += 1

        accepted = generate_qa_for_regulation(
            reg=reg,
            client=client,
            start_id=next_id,
            existing_questions=existing_questions,
            dedup_model=dedup_model,
            skip_dedup=args.skip_dedup,
            report=report,
            rejected_pairs=rejected_list,
        )

        all_accepted.extend(accepted)
        next_id += len(accepted)

        # Rate limiting
        time.sleep(args.delay)

    # Write outputs
    # Merge with previously accepted pairs (resume mode)
    if args.resume and previously_accepted:
        logger.info(
            "Resume: merged %d previous + %d new = %d total accepted pairs",
            len(previously_accepted),
            len(all_accepted),
            len(previously_accepted) + len(all_accepted),
        )
        all_accepted = previously_accepted + all_accepted

    # 1. Accepted pairs
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_accepted, f, ensure_ascii=False, indent=2)
    print(f"\nAccepted pairs written to: {output_path}")

    # 2. Generation report
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, ensure_ascii=False, indent=2)
    print(f"Generation report written to: {report_path}")

    # 3. Rejected pairs
    rejected_dicts = [rp.model_dump() for rp in rejected_list]
    with open(rejected_path, "w", encoding="utf-8") as f:
        json.dump(rejected_dicts, f, ensure_ascii=False, indent=2)
    print(f"Rejected pairs written to: {rejected_path}")

    # Summary
    print(f"\n=== Generation Summary ===")
    print(f"  Regulations processed: {report.total_regulations_processed}")
    print(f"  Pairs generated:       {report.total_pairs_generated}")
    print(f"  Pairs accepted:        {report.total_pairs_accepted}")
    print(f"  Pairs rejected:        {report.total_pairs_rejected}")
    print(f"  API calls:             {report.total_api_calls}")
    print(f"  API errors:            {report.total_api_errors}")
    if report.category_distribution:
        print(f"  Category distribution:")
        for cat, count in sorted(report.category_distribution.items()):
            print(f"    {cat}: {count}")
    if report.rejection_reasons:
        print(f"  Rejection reasons:")
        for reason, count in sorted(
            report.rejection_reasons.items(), key=lambda x: -x[1]
        ):
            print(f"    {reason}: {count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
