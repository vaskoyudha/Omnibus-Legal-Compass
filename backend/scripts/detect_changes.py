"""
Change detection for external Indonesian legal documents repository.

Compares the current state of the cloned legal-docs repo against the last
sync checkpoint to identify new, modified, and deleted markdown files
using ``git diff --name-status``.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Data Structures ──────────────────────────────────────────────────────────


@dataclass
class ChangeSet:
    """Result of comparing the external repo against the last sync point."""

    added: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    current_sha: str = ""
    previous_sha: str = ""


# ── Change Detector ──────────────────────────────────────────────────────────


class ChangeDetector:
    """Detect new/modified/deleted markdown files in an external git repo.

    Reads a JSON state file to determine the last-synced commit, runs
    ``git diff --name-status`` between that commit and HEAD, and returns
    a :class:`ChangeSet` listing only ``.md`` file changes.
    """

    def __init__(self, repo_dir: Path, state_file: Path) -> None:
        self.repo_dir: Path = repo_dir
        self.state_file: Path = state_file

    # ── Public API ───────────────────────────────────────────────────────

    def detect(self) -> ChangeSet:
        """Compare current repo state against last sync.

        * First run (no state file): every ``.md`` file is reported as added.
        * Same SHA: returns an empty :class:`ChangeSet`.
        * Otherwise: parses ``git diff --name-status`` output.
        """
        current_sha = self._get_current_sha()
        previous_sha = self._load_previous_sha()

        # First run — no previous state
        if previous_sha is None:
            logger.info("No previous sync state found — treating all .md files as added")
            md_files = self._list_markdown_files()
            return ChangeSet(
                added=md_files,
                modified=[],
                deleted=[],
                current_sha=current_sha,
                previous_sha="",
            )

        # No changes since last sync
        if current_sha == previous_sha:
            logger.info("Repository unchanged (SHA: %s)", current_sha[:8])
            return ChangeSet(
                added=[],
                modified=[],
                deleted=[],
                current_sha=current_sha,
                previous_sha=previous_sha,
            )

        # Diff between previous and current
        logger.info(
            "Detecting changes %s..%s", previous_sha[:8], current_sha[:8]
        )
        result = subprocess.run(
            ["git", "diff", "--name-status", previous_sha, current_sha],
            capture_output=True,
            text=True,
            cwd=str(self.repo_dir),
        )
        if result.returncode != 0:
            logger.warning("git diff failed: %s", result.stderr.strip())
            return ChangeSet(
                current_sha=current_sha, previous_sha=previous_sha
            )

        return self._parse_diff(result.stdout, current_sha, previous_sha)

    def save_state(self, sha: str, stats: dict[str, int]) -> None:
        """Persist sync state so the next run knows where to resume.

        Parameters
        ----------
        sha:
            The commit SHA that was just synced.
        stats:
            Summary counters (e.g. ``{"added": 5, "modified": 2, "deleted": 0}``).
        """
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "last_sha": sha,
            "last_sync": datetime.now(timezone.utc).isoformat(),
            "stats": stats,
        }
        self.state_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        logger.info("Sync state saved (SHA: %s)", sha[:8])

    # ── Internal Helpers ─────────────────────────────────────────────────

    def _get_current_sha(self) -> str:
        """Return HEAD commit SHA of the external repo."""
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(self.repo_dir),
        )
        if result.returncode != 0:
            msg = f"git rev-parse HEAD failed: {result.stderr.strip()}"
            raise RuntimeError(msg)
        return result.stdout.strip()

    def _load_previous_sha(self) -> str | None:
        """Load the last-synced SHA from the JSON state file.

        Returns ``None`` when the state file does not exist (first run).
        """
        if not self.state_file.exists():
            return None
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            return data.get("last_sha")
        except (json.JSONDecodeError, KeyError):
            logger.warning("Corrupt state file — treating as first run")
            return None

    def _list_markdown_files(self) -> list[str]:
        """List all ``.md`` files tracked by git in the repo."""
        result = subprocess.run(
            ["git", "ls-files", "*.md"],
            capture_output=True,
            text=True,
            cwd=str(self.repo_dir),
        )
        if result.returncode != 0:
            logger.warning("git ls-files failed: %s", result.stderr.strip())
            return []
        return [
            line
            for line in result.stdout.strip().splitlines()
            if line.endswith(".md")
        ]

    def _parse_diff(
        self, diff_output: str, current_sha: str, previous_sha: str
    ) -> ChangeSet:
        """Parse ``git diff --name-status`` output into a :class:`ChangeSet`.

        Each line has the format ``<status>\\t<path>`` where status is one of
        A (added), M (modified), or D (deleted).  Only ``.md`` files are kept.
        """
        added: list[str] = []
        modified: list[str] = []
        deleted: list[str] = []

        for line in diff_output.strip().splitlines():
            if not line.strip():
                continue
            parts = line.split("\t", maxsplit=1)
            if len(parts) != 2:
                logger.warning("Unexpected diff line: %r", line)
                continue
            status, filepath = parts[0].strip(), parts[1].strip()
            if not filepath.endswith(".md"):
                continue
            if status == "A":
                added.append(filepath)
            elif status == "M":
                modified.append(filepath)
            elif status == "D":
                deleted.append(filepath)
            else:
                logger.warning("Unknown diff status %r for %s", status, filepath)

        return ChangeSet(
            added=added,
            modified=modified,
            deleted=deleted,
            current_sha=current_sha,
            previous_sha=previous_sha,
        )
