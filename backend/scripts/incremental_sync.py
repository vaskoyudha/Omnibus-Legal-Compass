"""
Incremental sync pipeline for Indonesian legal documents.

Wraps :class:`MarkdownIngestionPipeline` and :class:`ChangeDetector` to process
only changed files since last sync.  Supports add, modify, and delete operations
with Qdrant point management.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, FilterSelector

from backend.scripts.ingest_markdown import MarkdownIngestionPipeline
from backend.scripts.detect_changes import ChangeDetector, ChangeSet

logger = logging.getLogger(__name__)


# ── Data Structures ──────────────────────────────────────────────────────────


@dataclass
class SyncResult:
    """Outcome of an incremental sync run."""

    status: str = "no_changes"
    added: int = 0
    modified: int = 0
    deleted: int = 0
    chunks_created: int = 0
    chunks_deleted: int = 0
    current_sha: str = ""
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary of all fields."""
        return {
            "status": self.status,
            "added": self.added,
            "modified": self.modified,
            "deleted": self.deleted,
            "chunks_created": self.chunks_created,
            "chunks_deleted": self.chunks_deleted,
            "current_sha": self.current_sha,
            "errors": self.errors,
        }

    def summary(self) -> str:
        """Return a human-readable summary string."""
        return (
            f"Sync {self.status}: "
            f"+{self.added} added, ~{self.modified} modified, "
            f"-{self.deleted} deleted | "
            f"{self.chunks_created} chunks created, "
            f"{self.chunks_deleted} chunks deleted"
        )


# ── Incremental Sync Pipeline ───────────────────────────────────────────────


class IncrementalSyncPipeline:
    """Process only changed files since the last sync.

    Orchestrates :class:`ChangeDetector` for delta detection and
    :class:`MarkdownIngestionPipeline` for parsing/chunking, then manages
    Qdrant point deletions for modified and removed files.
    """

    def __init__(
        self,
        qdrant_url: str,
        collection_name: str,
        repo_dir: Path,
        state_file: Path,
        jina_api_key: str | None = None,
    ) -> None:
        self.collection_name = collection_name
        self.repo_dir = repo_dir

        self.pipeline = MarkdownIngestionPipeline(
            qdrant_url=qdrant_url,
            collection_name=collection_name,
            jina_api_key=jina_api_key,
            repo_dir=repo_dir,
        )
        self.detector = ChangeDetector(repo_dir, state_file)
        self.qdrant_client = QdrantClient(url=qdrant_url)

    # ── Public API ───────────────────────────────────────────────────────

    def sync(self) -> SyncResult:
        """Run an incremental sync cycle.

        1. Detect changes via :class:`ChangeDetector`.
        2. If no changes → return early with ``status="no_changes"``.
        3. Process added files (parse → chunk).
        4. Process modified files (delete old points → parse → chunk).
        5. Process deleted files (delete points).
        6. Embed and upsert all collected chunks.
        7. Save state with the new SHA.
        8. Return :class:`SyncResult`.
        """
        changeset: ChangeSet = self.detector.detect()
        result = SyncResult(current_sha=changeset.current_sha)

        # No changes → early return
        if (
            not changeset.added
            and not changeset.modified
            and not changeset.deleted
        ):
            result.status = "no_changes"
            logger.info("No changes detected — skipping sync")
            return result

        all_chunks: list = []

        # ── Added files ──────────────────────────────────────────────
        for filepath in changeset.added:
            try:
                chunks = self.pipeline.process_single_file(
                    self.repo_dir / filepath
                )
                all_chunks.extend(chunks)
                result.added += 1
            except Exception as exc:
                result.errors.append(f"add:{filepath}: {exc}")
                logger.exception("Error processing added file %s", filepath)

        # ── Modified files ───────────────────────────────────────────
        for filepath in changeset.modified:
            try:
                deleted_count = self._delete_points_for_file(filepath)
                result.chunks_deleted += deleted_count
                chunks = self.pipeline.process_single_file(
                    self.repo_dir / filepath
                )
                all_chunks.extend(chunks)
                result.modified += 1
            except Exception as exc:
                result.errors.append(f"modify:{filepath}: {exc}")
                logger.exception("Error processing modified file %s", filepath)

        # ── Deleted files ────────────────────────────────────────────
        for filepath in changeset.deleted:
            try:
                deleted_count = self._delete_points_for_file(filepath)
                result.chunks_deleted += deleted_count
                result.deleted += 1
            except Exception as exc:
                result.errors.append(f"delete:{filepath}: {exc}")
                logger.exception("Error deleting points for %s", filepath)

        # ── Embed and upsert ─────────────────────────────────────────
        if all_chunks:
            self.pipeline._embed_and_upsert(all_chunks, batch_size=100)
            result.chunks_created = len(all_chunks)

        # ── Save state ───────────────────────────────────────────────
        self.detector.save_state(
            changeset.current_sha,
            {
                "added": result.added,
                "modified": result.modified,
                "deleted": result.deleted,
            },
        )

        result.status = "synced" if not result.errors else "error"
        logger.info(result.summary())
        return result

    # ── Internal Helpers ─────────────────────────────────────────────────

    def _delete_points_for_file(self, filepath: str) -> int:
        """Delete all Qdrant points whose ``filepath`` field matches.

        Returns a count placeholder (Qdrant delete is fire-and-forget).
        """
        self.qdrant_client.delete(
            collection_name=self.collection_name,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[
                        FieldCondition(
                            key="filepath",
                            match=MatchValue(value=filepath),
                        )
                    ]
                )
            ),
        )
        logger.info("Deleted points for filepath=%s", filepath)
        return 0  # Qdrant delete doesn't return count


# ── CLI Entry Point ──────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point for incremental sync pipeline."""
    parser = argparse.ArgumentParser(
        description="Incrementally sync changed legal documents into Qdrant"
    )
    parser.add_argument(
        "--repo-dir",
        required=True,
        help="Path to the cloned legal-docs git repository",
    )
    parser.add_argument(
        "--state-file",
        required=True,
        help="Path to the JSON sync state file",
    )
    parser.add_argument(
        "--qdrant-url",
        default=os.getenv("QDRANT_URL", "http://localhost:6333"),
        help="Qdrant server URL (default: QDRANT_URL env or localhost:6333)",
    )
    parser.add_argument(
        "--collection-name",
        default="indonesian_legal_docs",
        help="Qdrant collection name (default: indonesian_legal_docs)",
    )
    parser.add_argument(
        "--jina-api-key",
        default=os.getenv("JINA_API_KEY"),
        help="Jina API key (default: JINA_API_KEY env var)",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Write SyncResult JSON to this file path",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    pipeline = IncrementalSyncPipeline(
        qdrant_url=args.qdrant_url,
        collection_name=args.collection_name,
        repo_dir=Path(args.repo_dir),
        state_file=Path(args.state_file),
        jina_api_key=args.jina_api_key,
    )

    result = pipeline.sync()

    print(f"\n{'=' * 60}")
    print(result.summary())
    print(f"{'=' * 60}")

    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result.to_dict(), indent=2), encoding="utf-8"
        )
        print(f"Result written to {output_path}")


if __name__ == "__main__":
    main()
