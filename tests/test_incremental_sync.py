"""
Tests for incremental sync pipeline.

Covers no-change detection, added/modified/deleted file processing,
mixed operations, state persistence, Qdrant point deletion, and
SyncResult serialization.
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock

from qdrant_client.models import Filter, FieldCondition, MatchValue, FilterSelector

from backend.scripts.detect_changes import ChangeSet
from backend.scripts.incremental_sync import IncrementalSyncPipeline, SyncResult


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_mock_chunk(filepath: str = "docs/law.md", text: str = "chunk text"):
    """Build a fake ChunkData-like object with a filepath attribute."""
    chunk = MagicMock()
    chunk.filepath = filepath
    chunk.text = text
    return chunk


def _build_pipeline(tmp_path: Path) -> IncrementalSyncPipeline:
    """Construct an IncrementalSyncPipeline with all external deps mocked."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    state_file = tmp_path / "state.json"

    with mock.patch("backend.scripts.incremental_sync.MarkdownIngestionPipeline"), \
         mock.patch("backend.scripts.incremental_sync.ChangeDetector"), \
         mock.patch("backend.scripts.incremental_sync.QdrantClient"):
        pipeline = IncrementalSyncPipeline(
            qdrant_url="http://localhost:6333",
            collection_name="test_collection",
            repo_dir=repo_dir,
            state_file=state_file,
        )
    return pipeline


# ── No changes ───────────────────────────────────────────────────────────────


def test_sync_no_changes(tmp_path: Path):
    """Empty ChangeSet (no adds, mods, deletes) → status 'no_changes'."""
    pipeline = _build_pipeline(tmp_path)
    pipeline.detector.detect.return_value = ChangeSet(
        added=[], modified=[], deleted=[],
        current_sha="abc123", previous_sha="abc123",
    )

    result = pipeline.sync()

    assert result.status == "no_changes"
    assert result.added == 0
    assert result.modified == 0
    assert result.deleted == 0
    assert result.chunks_created == 0
    assert result.current_sha == "abc123"


# ── Added files ──────────────────────────────────────────────────────────────


def test_sync_added_files(tmp_path: Path):
    """Two added files → process_single_file called twice, chunks embedded."""
    pipeline = _build_pipeline(tmp_path)

    chunk_a = _make_mock_chunk("docs/law_a.md")
    chunk_b = _make_mock_chunk("docs/law_b.md")
    pipeline.pipeline.process_single_file.side_effect = [
        [chunk_a],
        [chunk_b],
    ]

    pipeline.detector.detect.return_value = ChangeSet(
        added=["docs/law_a.md", "docs/law_b.md"],
        modified=[], deleted=[],
        current_sha="sha_new", previous_sha="sha_old",
    )

    result = pipeline.sync()

    assert result.status == "synced"
    assert result.added == 2
    assert result.chunks_created == 2
    assert pipeline.pipeline.process_single_file.call_count == 2
    pipeline.pipeline._embed_and_upsert.assert_called_once()
    # Verify the chunks passed to _embed_and_upsert
    embed_call_args = pipeline.pipeline._embed_and_upsert.call_args
    assert len(embed_call_args[0][0]) == 2


# ── Modified files ───────────────────────────────────────────────────────────


def test_sync_modified_files(tmp_path: Path):
    """One modified file → delete called THEN process_single_file called."""
    pipeline = _build_pipeline(tmp_path)

    chunk_mod = _make_mock_chunk("docs/updated.md", "updated content")
    pipeline.pipeline.process_single_file.return_value = [chunk_mod]

    pipeline.detector.detect.return_value = ChangeSet(
        added=[], modified=["docs/updated.md"], deleted=[],
        current_sha="sha_new", previous_sha="sha_old",
    )

    result = pipeline.sync()

    assert result.status == "synced"
    assert result.modified == 1
    assert result.chunks_created == 1
    # Verify delete was called before process
    pipeline.qdrant_client.delete.assert_called_once()
    pipeline.pipeline.process_single_file.assert_called_once()


# ── Deleted files ────────────────────────────────────────────────────────────


def test_sync_deleted_files(tmp_path: Path):
    """One deleted file → delete called, SyncResult.deleted == 1."""
    pipeline = _build_pipeline(tmp_path)

    pipeline.detector.detect.return_value = ChangeSet(
        added=[], modified=[], deleted=["docs/removed.md"],
        current_sha="sha_new", previous_sha="sha_old",
    )

    result = pipeline.sync()

    assert result.status == "synced"
    assert result.deleted == 1
    assert result.added == 0
    assert result.modified == 0
    assert result.chunks_created == 0
    pipeline.qdrant_client.delete.assert_called_once()
    # No process_single_file calls for deletions
    pipeline.pipeline.process_single_file.assert_not_called()
    # No embed_and_upsert since no chunks
    pipeline.pipeline._embed_and_upsert.assert_not_called()


# ── Mixed changes ────────────────────────────────────────────────────────────


def test_sync_mixed_changes(tmp_path: Path):
    """1 added + 1 modified + 1 deleted → all operations executed."""
    pipeline = _build_pipeline(tmp_path)

    chunk_add = _make_mock_chunk("docs/new.md")
    chunk_mod = _make_mock_chunk("docs/changed.md")
    pipeline.pipeline.process_single_file.side_effect = [
        [chunk_add],   # added file
        [chunk_mod],   # modified file
    ]

    pipeline.detector.detect.return_value = ChangeSet(
        added=["docs/new.md"],
        modified=["docs/changed.md"],
        deleted=["docs/old.md"],
        current_sha="sha_new", previous_sha="sha_old",
    )

    result = pipeline.sync()

    assert result.status == "synced"
    assert result.added == 1
    assert result.modified == 1
    assert result.deleted == 1
    assert result.chunks_created == 2
    # delete called for modified + deleted = 2 times
    assert pipeline.qdrant_client.delete.call_count == 2
    # process_single_file called for added + modified = 2 times
    assert pipeline.pipeline.process_single_file.call_count == 2
    pipeline.pipeline._embed_and_upsert.assert_called_once()


# ── State persistence ────────────────────────────────────────────────────────


def test_sync_saves_state(tmp_path: Path):
    """After sync, detector.save_state() is called with correct SHA and stats."""
    pipeline = _build_pipeline(tmp_path)

    chunk = _make_mock_chunk("docs/new.md")
    pipeline.pipeline.process_single_file.return_value = [chunk]

    pipeline.detector.detect.return_value = ChangeSet(
        added=["docs/new.md"], modified=[], deleted=[],
        current_sha="sha_after", previous_sha="sha_before",
    )

    pipeline.sync()

    pipeline.detector.save_state.assert_called_once_with(
        "sha_after",
        {"added": 1, "modified": 0, "deleted": 0},
    )


# ── Point deletion filter ───────────────────────────────────────────────────


def test_delete_points_for_file(tmp_path: Path):
    """Verify QdrantClient.delete() is called with correct FilterSelector."""
    pipeline = _build_pipeline(tmp_path)

    pipeline._delete_points_for_file("docs/target.md")

    pipeline.qdrant_client.delete.assert_called_once()
    call_kwargs = pipeline.qdrant_client.delete.call_args
    assert call_kwargs[1]["collection_name"] == "test_collection"

    selector = call_kwargs[1]["points_selector"]
    # Verify the FilterSelector structure
    assert isinstance(selector, FilterSelector)
    filter_obj = selector.filter
    assert len(filter_obj.must) == 1
    condition = filter_obj.must[0]
    assert isinstance(condition, FieldCondition)
    assert condition.key == "filepath"
    assert condition.match.value == "docs/target.md"


# ── SyncResult.to_dict ──────────────────────────────────────────────────────


def test_sync_result_to_dict():
    """SyncResult.to_dict() returns all fields as a plain dict."""
    result = SyncResult(
        status="synced",
        added=3,
        modified=2,
        deleted=1,
        chunks_created=10,
        chunks_deleted=5,
        current_sha="abc123",
        errors=["some error"],
    )

    d = result.to_dict()

    assert d == {
        "status": "synced",
        "added": 3,
        "modified": 2,
        "deleted": 1,
        "chunks_created": 10,
        "chunks_deleted": 5,
        "current_sha": "abc123",
        "errors": ["some error"],
    }
    # Must be JSON-serializable
    import json
    json.dumps(d)  # should not raise


# ── SyncResult.summary ──────────────────────────────────────────────────────


def test_sync_result_summary():
    """summary() returns a formatted human-readable string."""
    result = SyncResult(
        status="synced",
        added=5,
        modified=3,
        deleted=1,
        chunks_created=20,
        chunks_deleted=8,
    )

    s = result.summary()

    assert "synced" in s
    assert "+5" in s
    assert "~3" in s
    assert "-1" in s
    assert "20 chunks created" in s
    assert "8 chunks deleted" in s
