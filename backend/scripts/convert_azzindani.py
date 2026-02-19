"""
Convert HuggingFace Azzindani/ID_REG_Parsed dataset to internal schema.

Batch conversion pipeline with quality filtering, deduplication, and
progress tracking.  Outputs a JSON file ready for ingestion into Qdrant.

Uses streaming row-group iteration to handle the 1.5 GB parquet file
without loading it entirely into memory.

Usage:
    # Analyze dataset structure (no conversion)
    python -m backend.scripts.convert_azzindani --analyze

    # Dry-run on 1,000 rows
    python -m backend.scripts.convert_azzindani --sample 1000

    # Full conversion (capped at 10K chunks)
    python -m backend.scripts.convert_azzindani \\
        --max-chunks 10000 \\
        --output data/external/azzindani/converted.json

    # Show 5 sample conversions
    python -m backend.scripts.convert_azzindani --sample 5 --show-samples
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

from pydantic import ValidationError

from backend.scripts.format_converter import AzzindaniAdapter, RegulationChunk

# ---------------------------------------------------------------------------
# Windows console encoding fix
# ---------------------------------------------------------------------------

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PARQUET_PATH = Path("data/external/azzindani/data.parquet")
DEFAULT_OUTPUT = Path("data/external/azzindani/converted.json")
DEFAULT_MAX_CHUNKS = 10_000

# Mojibake detection patterns (duplicated from format_converter for
# pre-filtering speed — avoids Pydantic overhead on obvious rejects)
_MOJIBAKE_UFFFD = "\ufffd"
_MOJIBAKE_C3_RE = re.compile(r"\u00c3[\u0080-\u00bf]")

# Strip "Pasal " prefix from Article field (OCR artefact in Azzindani dataset).
# Handles "Pasal 1", "Pasal  5" (double-space), "PASAL 1" (caps).
_PASAL_PREFIX_RE = re.compile(r"^[Pp][Aa][Ss][Aa][Ll]\s+", re.UNICODE)

# Known document type prefixes (short form — from format_converter)
_JENIS_PATTERN_SHORT = re.compile(
    r"^(UU|PP|Perpres|Permen|Perda)\b", re.IGNORECASE
)

# Full-form Indonesian regulation name patterns (OCR-extracted dataset)
# Order matters — more specific patterns first.
_JENIS_FULLFORM: list[tuple[str, str]] = [
    ("PERATURAN PEMERINTAH", "PP"),
    ("PERATURAN PRESIDEN", "Perpres"),
    # Regional regulations (all mapped to "Perda" bucket)
    ("PERATURAN DAERAH", "Perda"),
    ("PERATURAN GUBERNUR", "Perda"),
    ("PERATURAN BUPATI", "Perda"),
    ("PERATURAN WALIKOTA", "Perda"),
    ("PERATURAN WALI KOTA", "Perda"),
    # Ministerial
    ("PERATURAN MENTERI", "Permen"),
    # Laws (handle OCR space artifacts: "UNDANG -UNDANG")
    ("UNDANG-UNDANG", "UU"),
    ("UNDANG -UNDANG", "UU"),
    ("UNDANG- UNDANG", "UU"),
]


def _parse_jenis_expanded(regulation_name: str) -> str | None:
    """Parse document type from short prefix or full Indonesian name.

    Returns:
        Canonical type code or ``None`` if unrecognised.
    """
    name = regulation_name.strip()

    # Try short prefix first (fast path)
    m = _JENIS_PATTERN_SHORT.match(name)
    if m:
        raw = m.group(1)
        return {
            "uu": "UU", "pp": "PP", "perpres": "Perpres",
            "permen": "Permen", "perda": "Perda",
        }.get(raw.lower(), raw)

    # Try full-form patterns (case-insensitive)
    name_upper = name.upper()
    for pattern, jenis in _JENIS_FULLFORM:
        if pattern in name_upper:
            return jenis

    return None


# ---------------------------------------------------------------------------
# Dataset loading (streaming via row groups)
# ---------------------------------------------------------------------------


def _get_parquet_file(path: Path = PARQUET_PATH) -> Any:
    """Open a ParquetFile handle (lazy, no full read).

    Returns:
        A ``pyarrow.parquet.ParquetFile`` instance.

    Raises:
        FileNotFoundError: If the parquet file does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Parquet file not found: {path}\n"
            "Run: python -m backend.scripts.download_datasets --source huggingface"
        )

    import pyarrow.parquet as pq  # type: ignore[import-untyped]

    return pq.ParquetFile(str(path))


def _iter_row_dicts(
    pf: Any,
    *,
    max_rows: int | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield rows as dicts by streaming one row group at a time.

    Args:
        pf: ``pyarrow.parquet.ParquetFile``.
        max_rows: Stop after this many rows (``None`` = all).

    Yields:
        One dict per row.
    """
    emitted = 0
    for rg_idx in range(pf.metadata.num_row_groups):
        table = pf.read_row_group(rg_idx)
        cols = table.to_pydict()
        n = table.num_rows

        for i in range(n):
            if max_rows is not None and emitted >= max_rows:
                return
            yield {col: cols[col][i] for col in cols}
            emitted += 1


# ---------------------------------------------------------------------------
# Analysis (streaming)
# ---------------------------------------------------------------------------


def analyze_dataset(pf: Any, parquet_path: Path) -> dict[str, Any]:
    """Print dataset statistics without performing conversion.

    Streams through the file one row group at a time to avoid OOM.

    Args:
        pf: ``pyarrow.parquet.ParquetFile``.
        parquet_path: Path for printing file size.

    Returns:
        Statistics dictionary.
    """
    meta = pf.metadata
    num_rows = meta.num_rows
    schema = pf.schema_arrow
    columns = schema.names

    print(f"\n{'=' * 60}")
    print("=== Azzindani Dataset Analysis ===")
    print(f"{'=' * 60}")
    print(f"Total rows:       {num_rows:,}")
    print(f"Row groups:       {meta.num_row_groups}")
    print(f"Columns:          {columns}")
    print(f"File size:        {parquet_path.stat().st_size / (1024 * 1024):.1f} MB")

    # Column type info from schema
    print(f"\n--- Column Types ---")
    for i in range(len(schema)):
        field = schema.field(i)
        print(f"  {field.name:25s}  type={field.type}")

    # Streaming analysis
    type_counter: Counter[str] = Counter()
    unknown_samples: list[str] = []
    year_counter: Counter[str] = Counter()
    unique_reg_names: set[str] = set()
    total_content_len = 0
    null_counts: Counter[str] = Counter()
    min_content_len = float("inf")
    max_content_len = 0
    short_50 = 0
    short_100 = 0

    print(f"\nStreaming through {num_rows:,} rows ...")
    start = time.monotonic()

    for row_idx, row in enumerate(_iter_row_dicts(pf)):
        # Track nulls
        for col in columns:
            if row.get(col) is None:
                null_counts[col] += 1

        # Regulation Name analysis
        reg_name = row.get("Regulation Name")
        if reg_name and isinstance(reg_name, str):
            unique_reg_names.add(reg_name)
            jenis = _parse_jenis_expanded(reg_name)
            if jenis:
                type_counter[jenis] += 1
            else:
                type_counter["UNKNOWN"] += 1
                if len(unknown_samples) < 10:
                    unknown_samples.append(reg_name[:100])

        # Year
        year = row.get("Year")
        if year is not None:
            year_counter[str(year)] += 1

        # Content length
        content = row.get("Content", "")
        if content and isinstance(content, str):
            clen = len(content)
            total_content_len += clen
            if clen < min_content_len:
                min_content_len = clen
            if clen > max_content_len:
                max_content_len = clen
            if clen < 50:
                short_50 += 1
            if clen < 100:
                short_100 += 1
        else:
            short_50 += 1
            short_100 += 1

        # Progress every 500K
        if (row_idx + 1) % 500_000 == 0:
            elapsed = time.monotonic() - start
            print(f"  ... {row_idx + 1:,} rows scanned ({elapsed:.0f}s)")

    elapsed = time.monotonic() - start
    print(f"  ... done ({elapsed:.1f}s)")

    # Print results
    print(f"\n--- Null Counts ---")
    for col in columns:
        nc = null_counts.get(col, 0)
        print(f"  {col:25s}  nulls={nc:,}")

    print(f"\n--- Document Type Distribution ---")
    for doc_type, count in type_counter.most_common():
        pct = count / num_rows * 100
        print(f"  {doc_type:12s}  {count:>10,}  ({pct:5.1f}%)")

    if unknown_samples:
        print(f"\n  Sample unknown prefixes:")
        for s in unknown_samples:
            print(f"    {s!r}")

    print(f"\n--- Unique Regulations ---")
    print(f"  Unique 'Regulation Name': {len(unique_reg_names):,}")

    mean_len = total_content_len / max(num_rows, 1)
    print(f"\n--- Content Length ---")
    print(f"  Mean:   {mean_len:,.0f} chars")
    print(f"  Min:    {min_content_len:,} chars")
    print(f"  Max:    {max_content_len:,} chars")
    print(f"  < 50:   {short_50:,} rows")
    print(f"  < 100:  {short_100:,} rows")

    print(f"\n--- Year Distribution (top 10) ---")
    for year, count in year_counter.most_common(10):
        print(f"  {year}:  {count:>10,}")

    stats = {
        "total_rows": num_rows,
        "columns": columns,
        "type_distribution": dict(type_counter.most_common()),
        "unique_regulations": len(unique_reg_names),
        "content_length_mean": mean_len,
        "short_content_count": short_50,
    }

    return stats


# ---------------------------------------------------------------------------
# Conversion with quality filters
# ---------------------------------------------------------------------------


class RejectionStats:
    """Track rejection reasons during conversion."""

    def __init__(self) -> None:
        self.total_processed = 0
        self.total_converted = 0
        self.rejections: Counter[str] = Counter()
        self.unique_regulations: set[str] = set()
        self.type_counts: Counter[str] = Counter()
        self.dedup_keys: set[tuple[str, ...]] = set()
        self.dedup_rejected = 0

    def reject(self, reason: str) -> None:
        self.rejections[reason] += 1

    def accept(self, chunk: RegulationChunk) -> None:
        self.total_converted += 1
        reg_key = f"{chunk.jenis_dokumen} No. {chunk.nomor} Tahun {chunk.tahun}"
        self.unique_regulations.add(reg_key)
        self.type_counts[chunk.jenis_dokumen] += 1

    def summary(self) -> dict[str, Any]:
        return {
            "total_processed": self.total_processed,
            "total_converted": self.total_converted,
            "total_rejected": sum(self.rejections.values()),
            "dedup_rejected": self.dedup_rejected,
            "rejection_breakdown": dict(self.rejections.most_common()),
            "unique_regulations": len(self.unique_regulations),
            "type_distribution": dict(self.type_counts.most_common()),
        }


def _pre_filter(row: dict[str, Any]) -> str | None:
    """Fast pre-filter before Pydantic validation.

    Returns:
        ``None`` if the row passes, or a rejection reason string.
    """
    content = row.get("Content", "")
    if not content or not isinstance(content, str):
        return "empty_content"

    if len(content) < 50:
        return "short_content"

    if _MOJIBAKE_UFFFD in content:
        return "mojibake_ufffd"

    if _MOJIBAKE_C3_RE.search(content):
        return "mojibake_c3"

    reg_name = row.get("Regulation Name", "")
    if not reg_name or not isinstance(reg_name, str):
        return "empty_regulation_name"

    if not _parse_jenis_expanded(reg_name):
        return "unknown_jenis_dokumen"

    return None


def convert_dataset(
    pf: Any,
    *,
    max_chunks: int = DEFAULT_MAX_CHUNKS,
    sample_size: int | None = None,
    show_samples: int = 0,
) -> tuple[list[dict[str, Any]], RejectionStats]:
    """Convert Azzindani dataset rows to internal schema.

    Streams through the parquet row groups to avoid loading the full
    dataset into memory.  Applies pre-filtering, Pydantic validation,
    and deduplication.

    Args:
        pf: ``pyarrow.parquet.ParquetFile``.
        max_chunks: Maximum number of output chunks.
        sample_size: If set, only process the first N rows.
        show_samples: Number of sample conversions to print.

    Returns:
        (converted_records, rejection_stats)
    """
    adapter = AzzindaniAdapter()
    stats = RejectionStats()
    results: list[dict[str, Any]] = []

    total_rows = pf.metadata.num_rows
    process_rows = min(sample_size, total_rows) if sample_size else total_rows

    print(f"\n{'=' * 60}")
    print(f"=== Converting Azzindani Dataset ===")
    print(f"{'=' * 60}")
    print(f"Processing: {process_rows:,} / {total_rows:,} rows")
    print(f"Max chunks: {max_chunks:,}")
    print()

    start = time.monotonic()
    samples_shown = 0
    done = False

    for row in _iter_row_dicts(pf, max_rows=process_rows):
        stats.total_processed += 1

        # --- Pre-filter (fast, no Pydantic overhead) ---
        reject_reason = _pre_filter(row)
        if reject_reason:
            stats.reject(reject_reason)
        else:
            # --- Conversion + validation ---
            # Try the standard adapter first (handles short prefixes).
            # Fall back to direct construction with the expanded parser
            # for full-form Indonesian regulation names.
            chunk: RegulationChunk | None = None
            try:
                chunk = adapter.convert(row)
            except (ValueError, ValidationError) as exc:
                err_msg = str(exc)
                if "Cannot determine jenis_dokumen" in err_msg:
                    # Adapter failed on jenis_dokumen — try expanded parser
                    jenis = _parse_jenis_expanded(
                        row.get("Regulation Name", "")
                    )
                    if jenis:
                        try:
                            chunk = RegulationChunk(
                                jenis_dokumen=jenis,
                                nomor=str(row.get("Regulation Number", "")),
                                tahun=str(row.get("Year", "")),
                                judul=row.get("About", ""),
                                isi=row.get("Content", ""),
                                bab=row.get("Chapter") or None,
                                pasal=(
                                    str(row["Article"])
                                    if row.get("Article")
                                    else None
                                ),
                                source="huggingface_azzindani",
                            )
                        except (ValueError, ValidationError):
                            stats.reject("validation_error")
                    else:
                        stats.reject("jenis_parse_error")
                elif "Content too short" in err_msg:
                    stats.reject("short_content_pydantic")
                elif "encoding issue" in err_msg:
                    stats.reject("mojibake_pydantic")
                else:
                    stats.reject("validation_error")

            if chunk is not None:
                # --- Strip "Pasal " prefix from Article field ---
                # The Azzindani dataset stores "Pasal 1" not "1".
                # Both the AzzindaniAdapter and fallback paths pass it
                # through as-is, producing "Pasal Pasal 1" in display.
                if chunk.pasal:
                    cleaned = _PASAL_PREFIX_RE.sub("", chunk.pasal).strip()
                    if cleaned != chunk.pasal:
                        chunk = chunk.model_copy(update={"pasal": cleaned})

                # --- Deduplication by (jenis_dokumen, nomor, tahun, pasal) ---
                dedup_key = (
                    chunk.jenis_dokumen,
                    chunk.nomor,
                    chunk.tahun,
                    chunk.pasal or "",
                )
                if dedup_key in stats.dedup_keys:
                    stats.dedup_rejected += 1
                    stats.reject("duplicate")
                else:
                    stats.dedup_keys.add(dedup_key)

                    # --- Accept ---
                    chunk_dict = chunk.to_ingest_format()
                    results.append(chunk_dict)
                    stats.accept(chunk)

                    # Show sample conversions
                    if samples_shown < show_samples:
                        samples_shown += 1
                        print(f"--- Sample {samples_shown} ---")
                        print(f"  Input:  {row.get('Regulation Name', '')}")
                        print(
                            f"  Output: {chunk.jenis_dokumen} No.{chunk.nomor} "
                            f"Tahun {chunk.tahun} Pasal {chunk.pasal}"
                        )
                        print(f"  Isi:    {chunk.isi[:80]}...")
                        print()

                    # --- Cap check ---
                    if len(results) >= max_chunks:
                        done = True

        # Progress every 100K rows
        if stats.total_processed % 100_000 == 0 or done:
            elapsed = time.monotonic() - start
            rate = stats.total_processed / elapsed if elapsed > 0 else 0
            print(
                f"  [{stats.total_processed:>10,} / {process_rows:,}] "
                f"converted={len(results):,}  "
                f"rejected={sum(stats.rejections.values()):,}  "
                f"({rate:,.0f} rows/s)"
            )

        if done:
            print(f"\n  Reached max_chunks cap ({max_chunks:,}). Stopping.")
            break

    elapsed = time.monotonic() - start

    # Final progress line if not already printed
    if stats.total_processed % 100_000 != 0 and not done:
        rate = stats.total_processed / elapsed if elapsed > 0 else 0
        print(
            f"  [{stats.total_processed:>10,} / {process_rows:,}] "
            f"converted={len(results):,}  "
            f"rejected={sum(stats.rejections.values()):,}  "
            f"({rate:,.0f} rows/s)"
        )

    print(f"\nConversion completed in {elapsed:.1f}s")

    return results, stats


# ---------------------------------------------------------------------------
# Statistics printing
# ---------------------------------------------------------------------------


def print_stats(stats: RejectionStats) -> None:
    """Print detailed conversion statistics."""
    summary = stats.summary()

    print(f"\n{'=' * 60}")
    print("=== Conversion Statistics ===")
    print(f"{'=' * 60}")
    print(f"Total processed:     {summary['total_processed']:>10,}")
    print(f"Total converted:     {summary['total_converted']:>10,}")
    print(f"Total rejected:      {summary['total_rejected']:>10,}")
    print(f"  (dedup rejected):  {summary['dedup_rejected']:>10,}")
    print(f"Unique regulations:  {summary['unique_regulations']:>10,}")

    print(f"\n--- Rejection Breakdown ---")
    for reason, count in sorted(
        summary["rejection_breakdown"].items(), key=lambda x: -x[1]
    ):
        pct = count / max(summary["total_processed"], 1) * 100
        print(f"  {reason:30s}  {count:>10,}  ({pct:5.1f}%)")

    print(f"\n--- Document Type Distribution ---")
    for doc_type, count in sorted(
        summary["type_distribution"].items(), key=lambda x: -x[1]
    ):
        print(f"  {doc_type:12s}  {count:>10,}")


# ---------------------------------------------------------------------------
# Output writing
# ---------------------------------------------------------------------------


def write_output(
    results: list[dict[str, Any]],
    output_path: Path,
) -> None:
    """Write converted records to JSON file.

    Args:
        results: List of RegulationChunk dicts.
        output_path: Destination file path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"\nOutput written to: {output_path}")
    print(f"  Records: {len(results):,}")
    print(f"  Size:    {size_mb:.1f} MB")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry-point for Azzindani dataset conversion."""
    parser = argparse.ArgumentParser(
        description="Convert HuggingFace Azzindani dataset to internal schema",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m backend.scripts.convert_azzindani --analyze\n"
            "  python -m backend.scripts.convert_azzindani --sample 1000\n"
            "  python -m backend.scripts.convert_azzindani --max-chunks 10000\n"
            "  python -m backend.scripts.convert_azzindani --sample 5 --show-samples\n"
        ),
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analyze dataset structure without conversion",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        metavar="N",
        help="Only process first N rows (dry-run mode)",
    )
    parser.add_argument(
        "--max-chunks",
        type=int,
        default=DEFAULT_MAX_CHUNKS,
        metavar="N",
        help=f"Maximum output chunks (default: {DEFAULT_MAX_CHUNKS:,})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        metavar="PATH",
        help=f"Output JSON file path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--show-samples",
        action="store_true",
        help="Print 5 sample conversions during processing",
    )
    parser.add_argument(
        "--parquet",
        type=Path,
        default=PARQUET_PATH,
        metavar="PATH",
        help=f"Path to input parquet file (default: {PARQUET_PATH})",
    )

    args = parser.parse_args()

    # Open parquet file (lazy — no full load)
    print(f"Opening parquet: {args.parquet}")
    pf = _get_parquet_file(args.parquet)
    print(
        f"Metadata: {pf.metadata.num_rows:,} rows, "
        f"{pf.metadata.num_row_groups} row groups"
    )

    # Analysis mode
    if args.analyze:
        analyze_dataset(pf, args.parquet)
        return

    # Conversion
    show_n = 5 if args.show_samples else 0
    results, stats = convert_dataset(
        pf,
        max_chunks=args.max_chunks,
        sample_size=args.sample,
        show_samples=show_n,
    )

    print_stats(stats)

    # Write output
    if results:
        write_output(results, args.output)

        # Quick validation summary
        summary = stats.summary()
        unique = summary["unique_regulations"]
        types_present = len(summary["type_distribution"])
        print(f"\n{'=' * 60}")
        print("=== Phase 1 Readiness Check ===")
        print(f"{'=' * 60}")
        print(f"  Chunks:       {len(results):>6,}  (target: >= 5,000)")
        print(f"  Unique regs:  {unique:>6,}  (target: >= 500)")
        print(f"  Doc types:    {types_present:>6,}  (target: >= 4)")
        ok_chunks = len(results) >= 5_000
        ok_regs = unique >= 500
        ok_types = types_present >= 4
        status = "PASS" if (ok_chunks and ok_regs and ok_types) else "PARTIAL"
        print(f"  Status:       {status}")
    else:
        print("\nNo records converted. Check filters and input data.")


if __name__ == "__main__":
    main()
