"""
Export Qdrant collection to JSON for offline evaluation.

Scrolls through all points in a Qdrant collection via the REST API and
writes a flat JSON array compatible with ``load_corpus()`` in
``eval_embeddings.py``.  Each exported chunk has top-level keys:

    text, jenis_dokumen, nomor, tahun, judul, bab, pasal

Optionally includes embedding vectors with ``--include-embeddings``.

Usage:
    python -m backend.scripts.export_qdrant_corpus
    python -m backend.scripts.export_qdrant_corpus --collection indonesian_legal_docs
    python -m backend.scripts.export_qdrant_corpus --output backend/data/exports/corpus.json
    python -m backend.scripts.export_qdrant_corpus --include-embeddings
    python -m backend.scripts.export_qdrant_corpus --text-only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Windows console encoding fix
# ---------------------------------------------------------------------------

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_QDRANT_URL = "http://localhost:6333"
DEFAULT_COLLECTION = "indonesian_legal_docs"
DEFAULT_OUTPUT = Path("backend/data/exports/qdrant_corpus_full.json")
SCROLL_BATCH_SIZE = 100
MAX_RETRIES = 3
INITIAL_BACKOFF_S = 1.0

# Flat payload keys expected by eval_embeddings.py load_corpus()
PAYLOAD_KEYS = ("text", "jenis_dokumen", "nomor", "tahun", "judul", "bab", "pasal")


# ---------------------------------------------------------------------------
# Qdrant REST helpers
# ---------------------------------------------------------------------------


def _scroll_page(
    qdrant_url: str,
    collection: str,
    *,
    offset: int | str | None = None,
    with_vectors: bool = False,
) -> dict[str, Any]:
    """Fetch one page of points from the Qdrant scroll endpoint.

    Retries up to *MAX_RETRIES* times with exponential backoff on transient
    HTTP errors (5xx, connection failures).
    """
    url = f"{qdrant_url}/collections/{collection}/points/scroll"
    body: dict[str, Any] = {
        "limit": SCROLL_BATCH_SIZE,
        "with_payload": True,
        "with_vectors": with_vectors,
    }
    if offset is not None:
        body["offset"] = offset

    backoff = INITIAL_BACKOFF_S
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(url, json=body, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as exc:
            if attempt == MAX_RETRIES:
                raise SystemExit(
                    f"[ERROR] Qdrant scroll failed after {MAX_RETRIES} retries: {exc}"
                ) from exc
            print(f"  Retry {attempt}/{MAX_RETRIES} after error: {exc}")
            time.sleep(backoff)
            backoff *= 2

    # Unreachable, but keeps mypy happy
    raise AssertionError("unreachable")  # pragma: no cover


def _flatten_point(
    point: dict[str, Any],
    *,
    include_vectors: bool = False,
) -> dict[str, Any]:
    """Convert a Qdrant point into a flat dict matching load_corpus() schema."""
    payload = point.get("payload", {})
    flat: dict[str, Any] = {key: payload.get(key, "") for key in PAYLOAD_KEYS}
    if include_vectors and "vector" in point:
        flat["vector"] = point["vector"]
    return flat


# ---------------------------------------------------------------------------
# Core export logic
# ---------------------------------------------------------------------------


def export_collection(
    qdrant_url: str,
    collection: str,
    *,
    include_vectors: bool = False,
) -> list[dict[str, Any]]:
    """Scroll through the entire collection and return flat chunk dicts."""
    chunks: list[dict[str, Any]] = []
    offset: int | str | None = None
    page = 0

    while True:
        data = _scroll_page(
            qdrant_url,
            collection,
            offset=offset,
            with_vectors=include_vectors,
        )
        result = data.get("result", {})
        points = result.get("points", [])

        for pt in points:
            chunks.append(_flatten_point(pt, include_vectors=include_vectors))

        page += 1
        print(f"  Exported {len(chunks)} chunks (page {page})...")

        offset = result.get("next_page_offset")
        if offset is None:
            break

    return chunks


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry-point for exporting Qdrant collection to JSON."""
    parser = argparse.ArgumentParser(
        description="Export Qdrant collection to flat JSON for offline evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m backend.scripts.export_qdrant_corpus\n"
            "  python -m backend.scripts.export_qdrant_corpus --collection indonesian_legal_docs\n"
            "  python -m backend.scripts.export_qdrant_corpus --include-embeddings\n"
            "  python -m backend.scripts.export_qdrant_corpus --text-only\n"
        ),
    )
    parser.add_argument(
        "--qdrant-url",
        default=DEFAULT_QDRANT_URL,
        help=f"Qdrant REST URL (default: {DEFAULT_QDRANT_URL})",
    )
    parser.add_argument(
        "--collection",
        default=DEFAULT_COLLECTION,
        help=f"Collection name (default: {DEFAULT_COLLECTION})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output JSON path (default: {DEFAULT_OUTPUT})",
    )

    # Mutually exclusive: --include-embeddings vs --text-only
    vec_group = parser.add_mutually_exclusive_group()
    vec_group.add_argument(
        "--include-embeddings",
        action="store_true",
        default=False,
        help="Include embedding vectors in the export",
    )
    vec_group.add_argument(
        "--text-only",
        action="store_true",
        default=True,
        help="Export text and metadata only, no vectors (default)",
    )

    args = parser.parse_args()

    # Resolve include_vectors flag
    include_vectors = args.include_embeddings

    # Ensure output directory exists
    os.makedirs(args.output.parent, exist_ok=True)

    print(f"Exporting collection '{args.collection}' from {args.qdrant_url}")
    print(f"  Vectors: {'yes' if include_vectors else 'no'}")
    print(f"  Output:  {args.output}")
    print()

    t0 = time.perf_counter()
    chunks = export_collection(
        args.qdrant_url,
        args.collection,
        include_vectors=include_vectors,
    )
    elapsed = time.perf_counter() - t0

    # Write JSON
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    size_mb = args.output.stat().st_size / (1024 * 1024)
    print(f"\nDone. {len(chunks)} chunks exported in {elapsed:.1f}s")
    print(f"  File: {args.output} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
