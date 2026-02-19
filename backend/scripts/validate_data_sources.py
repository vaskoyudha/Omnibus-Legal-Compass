"""
Data source validation script.

Pre-flight checks for downloaded regulation datasets before ingestion.
Validates schema conformance, detects duplicates, checks content quality,
flags encoding issues, produces a coverage report, and prints sample
normalised chunks.

Usage:
    python -m backend.scripts.validate_data_sources --source all
    python -m backend.scripts.validate_data_sources --source all --sample 100
    python -m backend.scripts.validate_data_sources --source huggingface
    python -m backend.scripts.validate_data_sources --source otf
    python -m backend.scripts.validate_data_sources --source manual
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Windows console encoding fix
# ---------------------------------------------------------------------------

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


# ---------------------------------------------------------------------------
# Internal imports (deferred where heavy)
# ---------------------------------------------------------------------------

# format_converter lives next to this file; symbols are imported lazily
# so that ``--help`` stays fast and import errors are surfaced only when
# actually needed.
_RegulationChunk: type | None = None
_ManualAdapter: type | None = None
_AzzindaniAdapter: type | None = None


def _ensure_adapters() -> None:
    """Lazy-load format_converter symbols on first use."""
    global _RegulationChunk, _ManualAdapter, _AzzindaniAdapter  # noqa: PLW0603
    if _RegulationChunk is not None:
        return
    from backend.scripts.format_converter import (
        AzzindaniAdapter,
        ManualAdapter,
        RegulationChunk,
    )

    _RegulationChunk = RegulationChunk
    _ManualAdapter = ManualAdapter
    _AzzindaniAdapter = AzzindaniAdapter


# ---------------------------------------------------------------------------
# Validation: Schema Conformance
# ---------------------------------------------------------------------------


def validate_schema_conformance(
    data: list[dict[str, Any]],
    source: str,
) -> tuple[bool, list[str]]:
    """Validate that all records conform to expected schema.

    Args:
        data: List of records to validate.
        source: Source identifier ("huggingface", "otf", "manual").

    Returns:
        (is_valid, error_messages)
    """
    errors: list[str] = []

    required_fields: dict[str, list[str]] = {
        "huggingface": [
            "Regulation Name",
            "Regulation Number",
            "Year",
            "Content",
        ],
        "otf": ["type", "number", "year", "content"],
        "manual": ["jenis_dokumen", "nomor", "tahun", "text"],
    }

    fields = required_fields.get(source, [])
    if not fields:
        return False, [f"Unknown source: {source!r}"]

    # Sample first 1000 rows for schema validation
    sample = data[:1000]

    for idx, record in enumerate(sample):
        missing = [f for f in fields if f not in record or not record[f]]
        if missing:
            errors.append(f"Row {idx}: Missing fields {missing}")

    return len(errors) == 0, errors


# ---------------------------------------------------------------------------
# Validation: Duplicate Detection
# ---------------------------------------------------------------------------


def detect_duplicates(
    data: list[dict[str, Any]],
    source: str,
) -> tuple[int, list[str]]:
    """Detect duplicate records based on composite key.

    Args:
        data: List of records.
        source: Source identifier ("huggingface", "otf", "manual").

    Returns:
        (duplicate_count, sample_duplicate_ids)
    """
    seen: set[tuple[Any, ...]] = set()
    duplicates: list[str] = []

    for record in data:
        key: tuple[Any, ...] = ()

        if source == "huggingface":
            key = (
                record.get("Regulation Name"),
                record.get("Regulation Number"),
                record.get("Year"),
                record.get("Article"),
            )
        elif source == "manual":
            key = (
                record.get("jenis_dokumen"),
                record.get("nomor"),
                record.get("tahun"),
                record.get("pasal"),
                record.get("ayat"),
            )
        else:
            continue

        if key in seen:
            duplicates.append(str(key))
        seen.add(key)

    return len(duplicates), duplicates[:10]


# ---------------------------------------------------------------------------
# Validation: Content Quality
# ---------------------------------------------------------------------------


def validate_content_quality(
    data: list[dict[str, Any]],
    source: str,
    min_length: int = 50,
) -> tuple[int, list[str]]:
    """Check content quality: minimum length, non-empty.

    Args:
        data: List of records.
        source: Source identifier ("huggingface", "otf", "manual").
        min_length: Minimum content length in characters.

    Returns:
        (rejected_count, sample_rejected_ids)
    """
    rejected: list[str] = []

    content_field_map: dict[str, str] = {
        "huggingface": "Content",
        "otf": "content",
        "manual": "text",
    }
    content_field = content_field_map.get(source, "text")

    for idx, record in enumerate(data):
        content = record.get(content_field, "")
        if len(content) < min_length:
            rejected.append(
                f"Row {idx}: Content too short ({len(content)} chars)"
            )

    return len(rejected), rejected[:10]


# ---------------------------------------------------------------------------
# Validation: Encoding Issues
# ---------------------------------------------------------------------------


def validate_encoding(
    data: list[dict[str, Any]],
    source: str,
) -> tuple[int, list[str]]:
    """Detect mojibake and encoding issues.

    Args:
        data: List of records.
        source: Source identifier ("huggingface", "otf", "manual").

    Returns:
        (issue_count, sample_issues)
    """
    issues: list[str] = []

    content_field_map: dict[str, str] = {
        "huggingface": "Content",
        "otf": "content",
        "manual": "text",
    }
    content_field = content_field_map.get(source, "text")

    # Sample first 1000 rows for encoding validation
    sample = data[:1000]

    for idx, record in enumerate(sample):
        content = record.get(content_field, "")
        # U+FFFD replacement character
        if "\ufffd" in content:
            issues.append(
                f"Row {idx}: Potential encoding issue (U+FFFD)"
            )
        # Ã-prefix mojibake pattern (e.g. Ã© when UTF-8 is misread as
        # Latin-1).  Only flag when followed by a continuation byte.
        a_tilde_pos = content.find("\u00c3")
        if a_tilde_pos >= 0 and a_tilde_pos + 1 < len(content):
            next_char = ord(content[a_tilde_pos + 1])
            if 0x80 <= next_char <= 0xBF:
                issues.append(
                    f"Row {idx}: Potential encoding issue "
                    "(mojibake \\u00c3-prefix)"
                )

    return len(issues), issues[:10]


# ---------------------------------------------------------------------------
# Coverage Report
# ---------------------------------------------------------------------------


def print_coverage_report(
    data: list[dict[str, Any]],
    source: str,
) -> None:
    """Print a coverage report showing document type and year distribution.

    Args:
        data: List of records.
        source: Source identifier.
    """
    if not data:
        print("  (no data for coverage report)")
        return

    # Determine field names by source
    type_field: str = {
        "huggingface": "Regulation Name",
        "manual": "jenis_dokumen",
        "otf": "type",
    }.get(source, "jenis_dokumen")

    year_field: str = {
        "huggingface": "Year",
        "manual": "tahun",
        "otf": "year",
    }.get(source, "tahun")

    nomor_field: str = {
        "huggingface": "Regulation Number",
        "manual": "nomor",
        "otf": "number",
    }.get(source, "nomor")

    # Collect statistics
    type_counter: Counter[str] = Counter()
    year_counter: Counter[str] = Counter()
    unique_regulations: set[str] = set()

    for record in data:
        doc_type = str(record.get(type_field, "unknown"))
        # For huggingface, extract prefix (first word of reg name)
        if source == "huggingface":
            doc_type = doc_type.split()[0] if doc_type else "unknown"
        type_counter[doc_type] += 1

        year = str(record.get(year_field, "unknown"))
        year_counter[year] += 1

        nomor = str(record.get(nomor_field, ""))
        reg_key = f"{doc_type}_{nomor}_{year}"
        unique_regulations.add(reg_key)

    print("\n  --- Coverage Report ---")
    print(f"  Total records:        {len(data):,}")
    print(f"  Unique regulations:   {len(unique_regulations):,}")
    print(f"  Document types:       {len(type_counter)}")

    print("\n  Document Type Distribution:")
    for doc_type, count in type_counter.most_common():
        pct = count / len(data) * 100
        print(f"    {doc_type:15s}  {count:>6,}  ({pct:5.1f}%)")

    print("\n  Year Range:")
    years_int: list[int] = []
    for y in year_counter:
        try:
            years_int.append(int(y))
        except (ValueError, TypeError):
            pass
    if years_int:
        print(f"    {min(years_int)} - {max(years_int)}")
    else:
        print("    (no valid years)")

    print("\n  Top 5 Years:")
    for year, count in year_counter.most_common(5):
        print(f"    {year}: {count:>6,}")


# ---------------------------------------------------------------------------
# Sample Normalised Chunks
# ---------------------------------------------------------------------------


def print_sample_chunks(
    data: list[dict[str, Any]],
    source: str,
    n: int = 3,
) -> None:
    """Print sample records normalised to the internal RegulationChunk schema.

    Uses the format_converter adapters to demonstrate that raw source
    records can be successfully transformed.

    Args:
        data: List of raw source records.
        source: Source identifier.
        n: Number of samples to print.
    """
    _ensure_adapters()

    adapter_map: dict[str, type | None] = {
        "manual": _ManualAdapter,
        "huggingface": _AzzindaniAdapter,
    }
    adapter_cls = adapter_map.get(source)
    if adapter_cls is None:
        print(
            f"\n  (no adapter available for source={source!r}; "
            "skipping sample chunks)"
        )
        return

    adapter = adapter_cls()
    print(f"\n  --- Sample Normalised Chunks (up to {n}) ---")

    shown = 0
    for record in data:
        if shown >= n:
            break
        try:
            chunk = adapter.convert(record)
            print(
                f"\n  [{shown + 1}] {chunk.jenis_dokumen} No. {chunk.nomor} "
                f"Tahun {chunk.tahun}"
            )
            if chunk.pasal:
                line = f"      Pasal {chunk.pasal}"
                if chunk.ayat:
                    line += f" Ayat ({chunk.ayat})"
                print(line)
            print(f"      Source: {chunk.source}")
            # Truncate content for display
            display_isi = chunk.isi[:120].replace("\n", " ")
            if len(chunk.isi) > 120:
                display_isi += "..."
            print(f"      Isi:    {display_isi}")
            shown += 1
        except Exception:  # noqa: BLE001
            # Skip records that fail conversion (expected for some rows)
            continue

    if shown == 0:
        print("  (no records could be converted)")


# ---------------------------------------------------------------------------
# Source-specific validators
# ---------------------------------------------------------------------------


def validate_huggingface(sample_n: int | None = None) -> bool:
    """Validate HuggingFace Azzindani dataset.

    When no local data is available and the ``datasets`` library is not
    installed or the dataset cannot be fetched, the source is **skipped**
    (returns ``True``) so that ``--source all`` doesn't fail simply
    because an optional external dataset is unavailable.

    Args:
        sample_n: If set, limit validation to the first *N* records.

    Returns:
        True if all validations pass (or source is gracefully skipped).
    """
    print("\n=== Validating HuggingFace Azzindani Dataset ===")

    # ------------------------------------------------------------------
    # 1. Check for local converted.json first (preferred)
    # ------------------------------------------------------------------
    converted_path = Path("data/external/azzindani/converted.json")
    if converted_path.exists():
        try:
            with open(converted_path, encoding="utf-8") as f:
                raw_data: list[dict[str, Any]] = json.load(f)
            # converted.json uses ingest format (text, jenis_dokumen, ...)
            # Treat it like "manual" schema for validation purposes.
            data = raw_data[:sample_n] if sample_n else raw_data
            print(f"  Loaded {len(data):,} records from {converted_path}")
            print("  (using pre-converted local file)")

            valid, errors = validate_schema_conformance(data, "manual")
            if valid:
                print("  Schema conformance passed")
            else:
                print("  Schema errors (showing first 5):")
                for err in errors[:5]:
                    print(f"    {err}")

            dup_count, _ = detect_duplicates(data, "manual")
            print(f"  Duplicates: {dup_count:,}")

            rejected, _ = validate_content_quality(data, "manual")
            print(
                f"  Content quality: {rejected:,} records rejected "
                "(<50 chars)"
            )

            enc_issues, _ = validate_encoding(data, "manual")
            print(f"  Encoding issues: {enc_issues:,}")

            print_coverage_report(data, "manual")
            print_sample_chunks(data, "manual", n=3)

            return valid
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  Warning: Could not read {converted_path}: {exc}")

    # ------------------------------------------------------------------
    # 2. Check for parquet file (not converted yet)
    # ------------------------------------------------------------------
    parquet_path = Path("data/external/azzindani/data.parquet")
    if parquet_path.exists():
        try:
            import pyarrow.parquet as pq  # type: ignore[import-untyped]

            pf = pq.ParquetFile(str(parquet_path))
            num_rows = pf.metadata.num_rows
            size_mb = parquet_path.stat().st_size / (1024 * 1024)
            print(f"  Parquet file found: {num_rows:,} rows ({size_mb:.1f} MB)")
            print(
                "  (use convert_azzindani.py to convert before validation)"
            )
            return True
        except ImportError:
            print(
                "  Parquet file found but pyarrow not installed; "
                "skipping deep validation."
            )
            return True
        except Exception as exc:  # noqa: BLE001
            print(f"  Warning: Could not read parquet: {exc}")
            return True

    # ------------------------------------------------------------------
    # 3. No local data available — skip gracefully
    # ------------------------------------------------------------------
    print("  No local files found. Skipping HuggingFace validation.")
    print(
        "  To validate: run download_datasets.py or "
        "convert_azzindani.py first."
    )
    return True


def validate_otf(sample_n: int | None = None) -> bool:
    """Validate OTF Peraturan repository.

    When the OTF data directory is not present the source is **skipped**
    (returns ``True``).

    Args:
        sample_n: If set, limit file sampling to first *N* files.

    Returns:
        True if all validations pass (or source is gracefully skipped).
    """
    print("\n=== Validating OTF Peraturan Repository ===")

    otf_dir = Path("data/external/otf_peraturan/embed_data.text")
    if not otf_dir.exists():
        print(f"  Directory not found: {otf_dir}")
        print("  Skipping OTF validation (data not downloaded).")
        print(
            "  To download: "
            "python -m backend.scripts.download_datasets --source otf"
        )
        return True

    md_files = list(otf_dir.glob("**/*.md"))
    print(f"  Found {len(md_files):,} markdown files")

    if len(md_files) == 0:
        print("  No markdown files found in OTF directory.")
        return True

    # Sample validation
    sample = md_files[: (sample_n or 100)]
    issues = 0
    for path in sample:
        try:
            content = path.read_text(encoding="utf-8")
            if len(content) < 100:
                issues += 1
        except UnicodeDecodeError:
            issues += 1

    print(
        f"  Sampled {len(sample)} files: "
        f"{issues} had <100 chars or encoding issues"
    )

    return True


def validate_manual(sample_n: int | None = None) -> bool:
    """Validate existing manual regulations.json.

    Args:
        sample_n: If set, limit validation to the first *N* records.

    Returns:
        True if all validations pass.
    """
    print("\n=== Validating Manual Regulations ===")

    json_path = Path("data/peraturan/regulations.json")
    if not json_path.exists():
        print(f"  File not found: {json_path}")
        print("  Cannot validate manual source without data file.")
        return False

    try:
        with open(json_path, encoding="utf-8") as f:
            raw_data: list[dict[str, Any]] = json.load(f)
    except json.JSONDecodeError as exc:
        print(f"  Failed to parse JSON: {exc}")
        return False

    data = raw_data[:sample_n] if sample_n else raw_data
    print(f"  Loaded {len(data):,} records (of {len(raw_data):,} total)")

    # Schema conformance
    valid, errors = validate_schema_conformance(data, "manual")
    if valid:
        print("  Schema conformance passed")
    else:
        print("  Schema errors (showing first 5):")
        for err in errors[:5]:
            print(f"    {err}")

    # Duplicates
    dup_count, _dup_samples = detect_duplicates(data, "manual")
    print(f"  Duplicates: {dup_count:,}")

    # Content quality
    rejected_count, _rejected_samples = validate_content_quality(
        data, "manual"
    )
    print(
        f"  Content quality: {rejected_count:,} records rejected (<50 chars)"
    )

    # Encoding
    enc_issues, _enc_samples = validate_encoding(data, "manual")
    print(f"  Encoding issues: {enc_issues:,}")

    # Coverage report
    print_coverage_report(data, "manual")

    # Sample normalised chunks
    print_sample_chunks(data, "manual", n=3)

    return valid


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry-point for validating regulation data sources."""
    parser = argparse.ArgumentParser(
        description="Validate regulation data sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m backend.scripts.validate_data_sources --source all\n"
            "  python -m backend.scripts.validate_data_sources "
            "--source all --sample 100\n"
            "  python -m backend.scripts.validate_data_sources "
            "--source manual\n"
            "  python -m backend.scripts.validate_data_sources "
            "--source huggingface\n"
        ),
    )
    parser.add_argument(
        "--source",
        choices=["huggingface", "otf", "manual", "all"],
        default="all",
        help="Which source to validate (default: all)",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        metavar="N",
        help="Limit validation to the first N records per source",
    )

    args = parser.parse_args()
    sample_n: int | None = args.sample

    print("=" * 60)
    print("  Regulation Data Source Validator")
    print("=" * 60)
    if sample_n:
        print(f"  Sample limit: {sample_n} records per source")

    results: dict[str, bool] = {}

    if args.source in ["huggingface", "all"]:
        results["huggingface"] = validate_huggingface(sample_n)

    if args.source in ["otf", "all"]:
        results["otf"] = validate_otf(sample_n)

    if args.source in ["manual", "all"]:
        results["manual"] = validate_manual(sample_n)

    # ---- Summary ----
    print("\n" + "=" * 60)
    print("  Validation Summary")
    print("=" * 60)

    all_passed = True
    for source, passed in results.items():
        status = "PASS" if passed else "FAIL"
        icon = "+" if passed else "!"
        print(f"  [{icon}] {source}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n  All validated sources passed.")
    else:
        print("\n  Some sources failed validation.")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
