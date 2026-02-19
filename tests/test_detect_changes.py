"""
Tests for change detection of external legal documents repository.

Covers first-run detection, SHA comparison, git diff parsing, .md filtering,
state persistence, and state loading.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock

from backend.scripts.detect_changes import ChangeDetector, ChangeSet


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_subprocess_result(stdout: str = "", stderr: str = "", returncode: int = 0):
    """Build a fake ``subprocess.CompletedProcess``."""
    result = MagicMock()
    result.stdout = stdout
    result.stderr = stderr
    result.returncode = returncode
    return result


# ── First-run behaviour ─────────────────────────────────────────────────────


@mock.patch("backend.scripts.detect_changes.subprocess.run")
def test_first_run_all_files_added(mock_run, tmp_path: Path):
    """No state file exists → all .md files are reported as added."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    state_file = tmp_path / "state.json"

    # git rev-parse HEAD → current SHA
    # git ls-files *.md → file list
    mock_run.side_effect = [
        _make_subprocess_result(stdout="abc123\n"),
        _make_subprocess_result(stdout="docs/law1.md\ndocs/law2.md\n"),
    ]

    detector = ChangeDetector(repo_dir, state_file)
    cs = detector.detect()

    assert cs.added == ["docs/law1.md", "docs/law2.md"]
    assert cs.modified == []
    assert cs.deleted == []
    assert cs.current_sha == "abc123"
    assert cs.previous_sha == ""


# ── No changes (same SHA) ───────────────────────────────────────────────────


@mock.patch("backend.scripts.detect_changes.subprocess.run")
def test_no_changes_same_sha(mock_run, tmp_path: Path):
    """Same SHA in state file and HEAD → empty ChangeSet."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    state_file = tmp_path / "state.json"
    state_file.write_text(
        json.dumps({"last_sha": "abc123", "last_sync": "2026-02-20T10:00:00"}),
        encoding="utf-8",
    )

    mock_run.return_value = _make_subprocess_result(stdout="abc123\n")

    detector = ChangeDetector(repo_dir, state_file)
    cs = detector.detect()

    assert cs.added == []
    assert cs.modified == []
    assert cs.deleted == []
    assert cs.current_sha == "abc123"
    assert cs.previous_sha == "abc123"


# ── Diff parsing: added ─────────────────────────────────────────────────────


@mock.patch("backend.scripts.detect_changes.subprocess.run")
def test_git_diff_added_files(mock_run, tmp_path: Path):
    """Parse 'A\\tpath/file.md' lines correctly as added."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    state_file = tmp_path / "state.json"
    state_file.write_text(
        json.dumps({"last_sha": "aaa111"}), encoding="utf-8"
    )

    diff_output = "A\tdocs/new_regulation.md\nA\tdocs/another.md\n"
    mock_run.side_effect = [
        _make_subprocess_result(stdout="bbb222\n"),   # rev-parse
        _make_subprocess_result(stdout=diff_output),   # diff
    ]

    detector = ChangeDetector(repo_dir, state_file)
    cs = detector.detect()

    assert cs.added == ["docs/new_regulation.md", "docs/another.md"]
    assert cs.modified == []
    assert cs.deleted == []
    assert cs.current_sha == "bbb222"
    assert cs.previous_sha == "aaa111"


# ── Diff parsing: modified ───────────────────────────────────────────────────


@mock.patch("backend.scripts.detect_changes.subprocess.run")
def test_git_diff_modified_files(mock_run, tmp_path: Path):
    """Parse 'M\\tpath/file.md' lines correctly as modified."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    state_file = tmp_path / "state.json"
    state_file.write_text(
        json.dumps({"last_sha": "aaa111"}), encoding="utf-8"
    )

    diff_output = "M\tdocs/updated.md\n"
    mock_run.side_effect = [
        _make_subprocess_result(stdout="ccc333\n"),
        _make_subprocess_result(stdout=diff_output),
    ]

    detector = ChangeDetector(repo_dir, state_file)
    cs = detector.detect()

    assert cs.added == []
    assert cs.modified == ["docs/updated.md"]
    assert cs.deleted == []


# ── Diff parsing: deleted ────────────────────────────────────────────────────


@mock.patch("backend.scripts.detect_changes.subprocess.run")
def test_git_diff_deleted_files(mock_run, tmp_path: Path):
    """Parse 'D\\tpath/file.md' lines correctly as deleted."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    state_file = tmp_path / "state.json"
    state_file.write_text(
        json.dumps({"last_sha": "aaa111"}), encoding="utf-8"
    )

    diff_output = "D\tdocs/removed.md\n"
    mock_run.side_effect = [
        _make_subprocess_result(stdout="ddd444\n"),
        _make_subprocess_result(stdout=diff_output),
    ]

    detector = ChangeDetector(repo_dir, state_file)
    cs = detector.detect()

    assert cs.added == []
    assert cs.modified == []
    assert cs.deleted == ["docs/removed.md"]


# ── .md-only filtering ──────────────────────────────────────────────────────


@mock.patch("backend.scripts.detect_changes.subprocess.run")
def test_only_md_files_included(mock_run, tmp_path: Path):
    """Non-.md files in the diff output are filtered out."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    state_file = tmp_path / "state.json"
    state_file.write_text(
        json.dumps({"last_sha": "aaa111"}), encoding="utf-8"
    )

    diff_output = (
        "A\tdocs/new.md\n"
        "A\tscripts/run.py\n"
        "M\tREADME.txt\n"
        "M\tdocs/changed.md\n"
        "D\tconfig.yaml\n"
    )
    mock_run.side_effect = [
        _make_subprocess_result(stdout="eee555\n"),
        _make_subprocess_result(stdout=diff_output),
    ]

    detector = ChangeDetector(repo_dir, state_file)
    cs = detector.detect()

    assert cs.added == ["docs/new.md"]
    assert cs.modified == ["docs/changed.md"]
    assert cs.deleted == []


# ── State persistence ────────────────────────────────────────────────────────


def test_save_state_creates_json(tmp_path: Path):
    """save_state writes a valid JSON state file with expected keys."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    state_file = tmp_path / ".github" / "last-sync-state.json"

    detector = ChangeDetector(repo_dir, state_file)
    detector.save_state("abc123def", {"added": 5, "modified": 2, "deleted": 0})  # pragma: allowlist secret

    assert state_file.exists()
    data = json.loads(state_file.read_text(encoding="utf-8"))
    assert data["last_sha"] == "abc123def"  # pragma: allowlist secret
    assert "last_sync" in data
    assert data["stats"] == {"added": 5, "modified": 2, "deleted": 0}


# ── State loading ────────────────────────────────────────────────────────────


def test_load_previous_sha_from_state(tmp_path: Path):
    """Previous SHA is correctly loaded from a valid state file."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    state_file = tmp_path / "state.json"
    state_file.write_text(
        json.dumps({
            "last_sha": "prev_sha_999",
            "last_sync": "2026-02-20T10:00:00",
            "stats": {"added": 1, "modified": 0, "deleted": 0},
        }),
        encoding="utf-8",
    )

    detector = ChangeDetector(repo_dir, state_file)
    sha = detector._load_previous_sha()

    assert sha == "prev_sha_999"


# ── Mixed diff (A + M + D) ──────────────────────────────────────────────────


@mock.patch("backend.scripts.detect_changes.subprocess.run")
def test_mixed_diff_all_statuses(mock_run, tmp_path: Path):
    """Diff with A, M, and D lines produces correct ChangeSet."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    state_file = tmp_path / "state.json"
    state_file.write_text(
        json.dumps({"last_sha": "old_sha"}), encoding="utf-8"
    )

    diff_output = (
        "A\tnew_law.md\n"
        "M\texisting_law.md\n"
        "D\tobsolete_law.md\n"
    )
    mock_run.side_effect = [
        _make_subprocess_result(stdout="new_sha\n"),
        _make_subprocess_result(stdout=diff_output),
    ]

    detector = ChangeDetector(repo_dir, state_file)
    cs = detector.detect()

    assert cs.added == ["new_law.md"]
    assert cs.modified == ["existing_law.md"]
    assert cs.deleted == ["obsolete_law.md"]
    assert cs.current_sha == "new_sha"
    assert cs.previous_sha == "old_sha"


# ── Empty diff ───────────────────────────────────────────────────────────────


@mock.patch("backend.scripts.detect_changes.subprocess.run")
def test_empty_diff_output(mock_run, tmp_path: Path):
    """Empty diff output (different SHAs but no file changes) → empty lists."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    state_file = tmp_path / "state.json"
    state_file.write_text(
        json.dumps({"last_sha": "sha_old"}), encoding="utf-8"
    )

    mock_run.side_effect = [
        _make_subprocess_result(stdout="sha_new\n"),
        _make_subprocess_result(stdout=""),
    ]

    detector = ChangeDetector(repo_dir, state_file)
    cs = detector.detect()

    assert cs.added == []
    assert cs.modified == []
    assert cs.deleted == []
    assert cs.current_sha == "sha_new"
    assert cs.previous_sha == "sha_old"
