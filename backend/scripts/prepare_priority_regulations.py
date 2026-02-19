"""
Prepare priority regulations for QA dataset generation.

Extracts uncovered regulations from the merged corpus (those without existing
QA pairs in golden_qa.json), groups chunks, and writes output JSON matching
the schema expected by ``generate_qa_dataset.py``.

Usage::

    python -m backend.scripts.prepare_priority_regulations \\
        --corpus backend/data/peraturan/merged_corpus.json \\
        --existing-qa tests/deepeval/golden_qa.json \\
        --output backend/data/priority_regulations.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Regulation type ordering for output sorting (higher priority first).
REG_TYPE_ORDER: Dict[str, int] = {
    "UU": 0, "PP": 1, "Perpres": 2, "Permen": 3, "Perda": 4,
}

DEFAULT_MIN_TEXT_CHARS = 50

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def build_reg_key(chunk: Dict[str, Any]) -> str:
    """Build regulation key: ``{jenis_dokumen} {nomor}/{tahun}``."""
    return f"{chunk.get('jenis_dokumen', '?')} {chunk.get('nomor', '?')}/{chunk.get('tahun', '?')}"


def reg_sort_key(reg: Dict[str, Any]) -> Tuple[int, str, str]:
    """Sort key: type priority, then jenis alpha, then reg_key alpha."""
    jenis = reg.get("jenis_dokumen", "?")
    return (REG_TYPE_ORDER.get(jenis, 999), jenis, reg.get("reg_key", ""))


def extract_covered_keys(qa_pairs: List[Dict[str, Any]]) -> Set[str]:
    """Return set of regulation keys referenced in existing QA pairs."""
    covered: Set[str] = set()
    for pair in qa_pairs:
        for reg_key in pair.get("regulations", []):
            covered.add(reg_key)
    return covered


def group_chunks_by_regulation(
    corpus: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Group flat corpus chunks into regulation objects keyed by reg_key."""
    grouped: Dict[str, Dict[str, Any]] = {}
    chunk_lists: Dict[str, List[str]] = defaultdict(list)

    for chunk in corpus:
        key = build_reg_key(chunk)
        text = chunk.get("text", "")

        # First chunk for this regulation defines metadata
        if key not in grouped:
            grouped[key] = {
                "reg_key": key,
                "jenis_dokumen": chunk.get("jenis_dokumen", "?"),
                "nomor": str(chunk.get("nomor", "?")),
                "tahun": chunk.get("tahun", "?"),
                "judul": chunk.get("judul", ""),
                "tentang": chunk.get("tentang", ""),
                "chunks": [],
            }

        if text:
            chunk_lists[key].append(text)

    # Attach chunk text lists
    for key in grouped:
        grouped[key]["chunks"] = chunk_lists[key]

    return grouped


def partition_regulations(
    all_regs: Dict[str, Dict[str, Any]],
    covered_keys: Set[str],
    min_text_chars: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Partition uncovered regulations into output list and skip list."""
    output: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    for key, reg in all_regs.items():
        if key in covered_keys:
            continue

        total_chars = sum(len(t) for t in reg.get("chunks", []))

        if total_chars < min_text_chars:
            skipped.append({
                **reg,
                "total_text_chars": total_chars,
                "skip_reason": f"Total text ({total_chars} chars) below minimum ({min_text_chars})",
            })
        else:
            output.append(reg)

    output.sort(key=reg_sort_key)
    skipped.sort(key=reg_sort_key)
    return output, skipped


def print_summary(
    total_chunks: int,
    total_regs: int,
    covered_count: int,
    output_regs: List[Dict[str, Any]],
    skipped_regs: List[Dict[str, Any]],
) -> None:
    """Print a human-readable summary to stdout."""
    uncovered = total_regs - covered_count

    print("\n=== Priority Regulations Preparation ===")
    print(f"  Corpus: {total_chunks:,} chunks, {total_regs:,} regulations")
    print(f"  Covered: {covered_count} regulations (already in golden_qa.json)")
    print(f"  Uncovered: {uncovered} regulations")
    print(f"  Skipped: {len(skipped_regs)} regulations (less than minimum text chars)")
    print(f"  Output: {len(output_regs)} regulations ready for QA generation")

    # Count by type
    type_counts: Dict[str, int] = defaultdict(int)
    for reg in output_regs:
        jenis = reg.get("jenis_dokumen", "?")
        type_counts[jenis] += 1

    if type_counts:
        print("\n  By type:")
        for jenis in sorted(type_counts, key=lambda j: REG_TYPE_ORDER.get(j, 999)):
            print(f"    {jenis:<10s} {type_counts[jenis]} regulations")

    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    """CLI entry point for priority regulation preparation."""
    parser = argparse.ArgumentParser(
        description="Extract uncovered regulations from merged corpus for QA generation",
    )
    parser.add_argument(
        "--corpus", type=str, required=True,
        help="Path to merged_corpus.json (flat list of chunk dicts)")
    parser.add_argument(
        "--existing-qa", type=str, required=True,
        help="Path to golden_qa.json (existing QA pairs with regulation references)")
    parser.add_argument(
        "--output", type=str, required=True,
        help="Path to write priority_regulations.json (for generate_qa_dataset.py)")
    parser.add_argument(
        "--skip-list", type=str, default=None,
        help="Path to write skip list JSON (default: skip_regulations.json in output dir)")
    parser.add_argument(
        "--min-text-chars", type=int, default=DEFAULT_MIN_TEXT_CHARS,
        help=f"Minimum total text chars to include a regulation (default: {DEFAULT_MIN_TEXT_CHARS})")

    args = parser.parse_args()

    # ── Resolve paths ──────────────────────────────────────────────────
    corpus_path = Path(args.corpus)
    qa_path = Path(args.existing_qa)
    output_path = Path(args.output)
    skip_path = (
        Path(args.skip_list) if args.skip_list
        else output_path.parent / "skip_regulations.json"
    )

    # ── Validate inputs exist ──────────────────────────────────────────
    if not corpus_path.exists():
        print(f"ERROR: Corpus file not found: {corpus_path}", file=sys.stderr)
        return 1
    if not qa_path.exists():
        print(f"ERROR: Existing QA file not found: {qa_path}", file=sys.stderr)
        return 1

    # ── Load data ──────────────────────────────────────────────────────
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus: List[Dict[str, Any]] = json.load(f)

    with open(qa_path, "r", encoding="utf-8") as f:
        qa_pairs: List[Dict[str, Any]] = json.load(f)

    # ── Process ────────────────────────────────────────────────────────
    covered_keys = extract_covered_keys(qa_pairs)
    all_regs = group_chunks_by_regulation(corpus)
    output_regs, skipped_regs = partition_regulations(
        all_regs, covered_keys, args.min_text_chars
    )

    # ── Write outputs ──────────────────────────────────────────────────
    output_path.parent.mkdir(parents=True, exist_ok=True)
    skip_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_regs, f, ensure_ascii=False, indent=2)

    with open(skip_path, "w", encoding="utf-8") as f:
        json.dump(skipped_regs, f, ensure_ascii=False, indent=2)

    # ── Summary ────────────────────────────────────────────────────────
    print_summary(
        total_chunks=len(corpus),
        total_regs=len(all_regs),
        covered_count=len(covered_keys),
        output_regs=output_regs,
        skipped_regs=skipped_regs,
    )

    print(f"  Written: {output_path}")
    print(f"  Skip list: {skip_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
