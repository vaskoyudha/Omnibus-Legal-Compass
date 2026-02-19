"""
Download external Indonesian regulation datasets.

Supports two data sources:
1. HuggingFace Azzindani/ID_REG_Parsed — 3.63M parsed regulation rows
2. Open-Technology-Foundation/peraturan.go.id — 5,817 regulation markdown files

Usage:
    python -m backend.scripts.download_datasets --source all
    python -m backend.scripts.download_datasets --source huggingface
    python -m backend.scripts.download_datasets --source otf
    python -m backend.scripts.download_datasets --source all --force

Downloads are idempotent: existing data is skipped unless --force is used.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# NOTE: tqdm is a transitive dependency — `datasets` uses it for progress bars.
# We list it in requirements.txt to make the dependency explicit.

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_ROOT = Path("data/external")
AZZINDANI_DIR = DATA_ROOT / "azzindani"
OTF_DIR = DATA_ROOT / "otf_peraturan"

HF_DATASET_ID = "Azzindani/ID_REG_Parsed"
OTF_REPO_URL = (
    "https://github.com/Open-Technology-Foundation/peraturan.go.id.git"
)

# Minimum thresholds for validation
MIN_PARQUET_SIZE_MB = 100  # 3.63M rows should be well above 100 MB
MIN_OTF_MD_FILES = 1000  # Expect ~5,817 markdown files


# ---------------------------------------------------------------------------
# HuggingFace downloader
# ---------------------------------------------------------------------------


def download_huggingface(
    output_dir: Path = AZZINDANI_DIR,
    force: bool = False,
) -> dict[str, Any]:
    """Download Azzindani/ID_REG_Parsed from HuggingFace.

    Saves the dataset as a Parquet file for fast downstream loading.

    Args:
        output_dir: Directory to save downloaded dataset.
        force: Re-download even if data already exists.

    Returns:
        Status dict with row count and file paths.
    """
    parquet_path = output_dir / "data.parquet"

    # Idempotency check
    if parquet_path.exists() and not force:
        print(f"[skip] Dataset already exists at {parquet_path}")
        return {"status": "skipped", "reason": "already_exists"}

    # Late import so CLI --help stays fast when `datasets` is not installed
    try:
        from datasets import load_dataset  # type: ignore[import-untyped]
    except ImportError as exc:
        print(
            "ERROR: 'datasets' package is not installed.\n"
            "       Run: pip install datasets pyarrow tqdm"
        )
        raise SystemExit(1) from exc

    print(f"[download] Fetching {HF_DATASET_ID} from HuggingFace …")
    start = time.monotonic()

    dataset = load_dataset(HF_DATASET_ID)

    train_split = dataset["train"]  # type: ignore[index]
    row_count = len(train_split)
    print(f"[download] Received {row_count:,} rows in {time.monotonic() - start:.1f}s")

    # Persist to Parquet
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"[save]     Writing parquet to {parquet_path} …")
    train_split.to_parquet(str(parquet_path))

    size_mb = parquet_path.stat().st_size / (1024 * 1024)
    print(f"[save]     Parquet written ({size_mb:.1f} MB)")

    return {
        "status": "success",
        "rows": row_count,
        "size_mb": round(size_mb, 1),
        "output_path": str(output_dir),
    }


# ---------------------------------------------------------------------------
# OTF sparse clone
# ---------------------------------------------------------------------------


def clone_otf_repo(
    output_dir: Path = OTF_DIR,
    force: bool = False,
) -> dict[str, Any]:
    """Sparse-clone Open-Technology-Foundation/peraturan.go.id repository.

    Uses ``--filter=blob:none --sparse`` to avoid downloading the full
    7.1 GB history.  Only the ``embed_data.text/`` directory (regulation
    markdown files) is checked out.

    Args:
        output_dir: Directory to clone repository into.
        force: Re-clone even if the repository already exists.

    Returns:
        Status dict with file count and clone path.
    """
    embed_dir = output_dir / "embed_data.text"

    # Idempotency check
    if embed_dir.exists() and not force:
        md_count = len(list(embed_dir.glob("**/*.md")))
        print(f"[skip] Repository already cloned at {output_dir} ({md_count:,} .md files)")
        return {"status": "skipped", "reason": "already_exists"}

    # Verify git is available
    if shutil.which("git") is None:
        print(
            "ERROR: 'git' is not found on PATH.\n"
            "       Install git: https://git-scm.com/downloads"
        )
        raise SystemExit(1)

    # Clean up if forcing
    if output_dir.exists() and force:
        print(f"[clean] Removing existing clone at {output_dir} …")
        shutil.rmtree(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[clone] Sparse-cloning {OTF_REPO_URL} …")
    start = time.monotonic()

    try:
        # Step 1: sparse clone (blobs downloaded on demand)
        subprocess.run(
            [
                "git",
                "clone",
                "--filter=blob:none",
                "--sparse",
                OTF_REPO_URL,
                str(output_dir),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        # Step 2: set sparse-checkout to only materialise embed_data.text
        subprocess.run(
            [
                "git",
                "-C",
                str(output_dir),
                "sparse-checkout",
                "set",
                "embed_data.text",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr or "(no stderr)"
        print(f"ERROR: git command failed (exit {exc.returncode}):\n{stderr}")
        raise SystemExit(1) from exc

    elapsed = time.monotonic() - start

    # Count materialised markdown files
    md_files = list(embed_dir.glob("**/*.md"))
    print(
        f"[clone] Done in {elapsed:.1f}s — "
        f"{len(md_files):,} markdown files checked out"
    )

    return {
        "status": "success",
        "file_count": len(md_files),
        "elapsed_s": round(elapsed, 1),
        "output_path": str(output_dir),
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_download(source: str, data_dir: Path) -> bool:
    """Validate that downloaded data is usable.

    Performs lightweight sanity checks (file existence, size, count) without
    loading the full dataset into memory.

    Args:
        source: ``"huggingface"`` or ``"otf"``.
        data_dir: Root path for the downloaded data.

    Returns:
        ``True`` if validation passes.

    Raises:
        ValueError: If validation fails with a specific diagnostic message.
    """
    if source == "huggingface":
        parquet_file = data_dir / "data.parquet"
        if not parquet_file.exists():
            raise ValueError(f"Missing parquet file: {parquet_file}")

        size_mb = parquet_file.stat().st_size / (1024 * 1024)
        if size_mb < MIN_PARQUET_SIZE_MB:
            raise ValueError(
                f"Parquet file too small ({size_mb:.1f} MB); "
                f"expected ≥ {MIN_PARQUET_SIZE_MB} MB for 3.63M rows"
            )

        print(f"[validate] HuggingFace OK — {size_mb:.1f} MB parquet")
        return True

    if source == "otf":
        embed_dir = data_dir / "embed_data.text"
        if not embed_dir.exists():
            raise ValueError(
                f"Missing embed_data.text directory in {data_dir}"
            )

        md_files = list(embed_dir.glob("**/*.md"))
        if len(md_files) < MIN_OTF_MD_FILES:
            raise ValueError(
                f"Too few markdown files: {len(md_files):,}; "
                f"expected ≥ {MIN_OTF_MD_FILES:,}"
            )

        print(f"[validate] OTF OK — {len(md_files):,} markdown files")
        return True

    raise ValueError(f"Unknown source: {source!r}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry-point for downloading external regulation datasets."""
    parser = argparse.ArgumentParser(
        description="Download external Indonesian regulation datasets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m backend.scripts.download_datasets --source all\n"
            "  python -m backend.scripts.download_datasets --source huggingface\n"
            "  python -m backend.scripts.download_datasets --source otf --force\n"
        ),
    )
    parser.add_argument(
        "--source",
        choices=["huggingface", "otf", "all"],
        default="all",
        help="Which data source to download (default: all)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if data already exists",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=DATA_ROOT,
        help=f"Root directory for external data (default: {DATA_ROOT})",
    )

    args = parser.parse_args()

    results: dict[str, dict[str, Any]] = {}
    errors: list[str] = []

    # --- HuggingFace ---
    if args.source in ("huggingface", "all"):
        print(f"\n{'=' * 50}")
        print("=== Downloading HuggingFace Azzindani Dataset ===")
        print(f"{'=' * 50}")
        try:
            hf_dir = args.data_root / "azzindani"
            results["huggingface"] = download_huggingface(
                output_dir=hf_dir, force=args.force
            )
            if results["huggingface"]["status"] != "skipped":
                validate_download("huggingface", hf_dir)
        except ValueError as exc:
            errors.append(f"HuggingFace validation failed: {exc}")
            print(f"[ERROR] {exc}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"HuggingFace download failed: {exc}")
            print(f"[ERROR] {exc}")

    # --- OTF ---
    if args.source in ("otf", "all"):
        print(f"\n{'=' * 50}")
        print("=== Cloning OTF Peraturan Repository ===")
        print(f"{'=' * 50}")
        try:
            otf_dir = args.data_root / "otf_peraturan"
            results["otf"] = clone_otf_repo(
                output_dir=otf_dir, force=args.force
            )
            if results["otf"]["status"] != "skipped":
                validate_download("otf", otf_dir)
        except ValueError as exc:
            errors.append(f"OTF validation failed: {exc}")
            print(f"[ERROR] {exc}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"OTF clone failed: {exc}")
            print(f"[ERROR] {exc}")

    # --- Summary ---
    print(f"\n{'=' * 50}")
    print("=== Download Summary ===")
    print(f"{'=' * 50}")
    for source, result in results.items():
        status = result.get("status", "unknown")
        detail = ""
        if status == "success":
            if "rows" in result:
                detail = f" ({result['rows']:,} rows, {result.get('size_mb', '?')} MB)"
            elif "file_count" in result:
                detail = f" ({result['file_count']:,} files)"
        elif status == "skipped":
            detail = f" (reason: {result.get('reason', 'unknown')})"
        print(f"  {source}: {status}{detail}")

    if errors:
        print(f"\n⚠ {len(errors)} error(s):")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    print("\nDone.")


if __name__ == "__main__":
    main()
