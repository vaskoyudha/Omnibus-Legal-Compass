"""
Amendment and revocation detection for Indonesian legal regulations.

Identifies amendment, revocation, replacement, and supplementation language
in regulation text and determines relationships between regulations.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum

from backend.cross_reference import normalize_jenis

logger = logging.getLogger(__name__)


# ── Amendment Types ──────────────────────────────────────────────────────────


class AmendmentType(str, Enum):
    """Types of amendment relationships between regulations."""

    AMENDS = "amends"
    REVOKES = "revokes"
    REPLACES = "replaces"
    SUPPLEMENTS = "supplements"


# ── Data Model ───────────────────────────────────────────────────────────────


@dataclass
class AmendmentRelation:
    """A detected amendment/revocation relationship between two regulations."""

    source_regulation: str  # the amending regulation, e.g. "UU-19-2016"
    target_regulation: str  # the amended regulation, e.g. "UU-11-2008"
    amendment_type: AmendmentType
    raw_text: str
    confidence: float  # 0.0–1.0


# ── Target Regex Fragment ────────────────────────────────────────────────────

_TARGET_PATTERN = (
    r"(?P<target>"
    r"(?:Undang-Undang|Peraturan Pemerintah|Peraturan Presiden"
    r"|Peraturan Menteri|UU|PP|Perpres|Permen)"
    r"(?:\s+Nomor|\s+No\.?)?\s+"
    r"(?:\d+)"
    r"(?:\s+Tahun\s+\d{4}|/\d{4})"
    r")"
)


# ── Amendment Detector ───────────────────────────────────────────────────────


class AmendmentDetector:
    """Detects amendment/revocation/replacement language in Indonesian legal text.

    Uses compiled regex patterns to identify amendment relationships
    and normalizes target regulation identifiers to canonical form.
    """

    AMENDMENT_PATTERNS: list[tuple[AmendmentType, re.Pattern[str]]] = [
        (
            AmendmentType.AMENDS,
            re.compile(
                r"(?:mengubah|perubahan\s+atas)\s+" + _TARGET_PATTERN,
                re.IGNORECASE,
            ),
        ),
        (
            AmendmentType.REVOKES,
            re.compile(
                r"(?:mencabut|pencabutan)\s+" + _TARGET_PATTERN,
                re.IGNORECASE,
            ),
        ),
        (
            AmendmentType.REPLACES,
            re.compile(
                r"(?:mengganti|penggantian)\s+" + _TARGET_PATTERN,
                re.IGNORECASE,
            ),
        ),
        (
            AmendmentType.SUPPLEMENTS,
            re.compile(
                r"(?:melengkapi|penambahan\s+atas)\s+" + _TARGET_PATTERN,
                re.IGNORECASE,
            ),
        ),
    ]

    # ── Title patterns ───────────────────────────────────────────────────

    _TITLE_PATTERN: re.Pattern[str] = re.compile(
        r"(?:perubahan|pencabutan|penggantian)\s+(?:atas\s+)?" + _TARGET_PATTERN,
        re.IGNORECASE,
    )

    _TITLE_TYPE_MAP: dict[str, AmendmentType] = {
        "perubahan": AmendmentType.AMENDS,
        "pencabutan": AmendmentType.REVOKES,
        "penggantian": AmendmentType.REPLACES,
    }

    # ── Internal helpers ─────────────────────────────────────────────────

    @staticmethod
    def _parse_target(target_text: str) -> str | None:
        """Parse a target regulation string into canonical form (e.g. 'UU-11-2008').

        Handles both full-form ('Undang-Undang Nomor 11 Tahun 2008')
        and abbreviated ('UU No. 11/2008') citations.
        """
        # Full-form pattern
        m = re.search(
            r"(?P<jenis>Undang-Undang|Peraturan Pemerintah|Peraturan Presiden"
            r"|Peraturan Menteri)"
            r"\s+(?:Nomor|No\.?)\s*(?P<nomor>\d+)"
            r"\s+Tahun\s+(?P<tahun>\d{4})",
            target_text,
            re.IGNORECASE,
        )
        if m:
            jenis = normalize_jenis(m.group("jenis"))
            return f"{jenis}-{m.group('nomor')}-{m.group('tahun')}"

        # Abbreviated pattern
        m = re.search(
            r"(?P<jenis>UU|PP|Perpres|Permen)"
            r"(?:\s+(?:Nomor|No\.?))?\s*(?P<nomor>\d+)"
            r"(?:\s+Tahun\s+(?P<tahun>\d{4})|/(?P<tahun2>\d{4}))",
            target_text,
            re.IGNORECASE,
        )
        if m:
            jenis = normalize_jenis(m.group("jenis"))
            tahun = m.group("tahun") or m.group("tahun2")
            return f"{jenis}-{m.group('nomor')}-{tahun}"

        return None

    # ── Public API ───────────────────────────────────────────────────────

    def detect_amendments(
        self, text: str, source_regulation_id: str
    ) -> list[AmendmentRelation]:
        """Detect amendment/revocation relationships in regulation body text.

        Scans the full text for amendment patterns and returns all detected
        relationships with confidence 1.0 for exact body-text matches.

        Args:
            text: Body text of the regulation.
            source_regulation_id: Canonical ID of the source regulation.

        Returns:
            List of detected amendment relations (empty if none found).
        """
        if not text or not text.strip():
            return []

        results: list[AmendmentRelation] = []

        for amendment_type, pattern in self.AMENDMENT_PATTERNS:
            for m in pattern.finditer(text):
                target_text = m.group("target")
                canonical = self._parse_target(target_text)
                if canonical is None:
                    logger.warning(
                        "Could not parse target regulation from: %r", target_text
                    )
                    continue
                results.append(
                    AmendmentRelation(
                        source_regulation=source_regulation_id,
                        target_regulation=canonical,
                        amendment_type=amendment_type,
                        raw_text=m.group(0),
                        confidence=1.0,
                    )
                )

        return results

    def detect_from_title(
        self, title: str, regulation_id: str
    ) -> list[AmendmentRelation]:
        """Detect amendment relationships from a regulation's title.

        Titles like "Perubahan atas UU Nomor 11 Tahun 2008" indicate
        that the regulation amends UU-11-2008.  Title-based detections
        receive confidence 0.8.

        Args:
            title: Title of the regulation.
            regulation_id: Canonical ID of the regulation.

        Returns:
            List of detected amendment relations (empty if none found).
        """
        if not title or not title.strip():
            return []

        results: list[AmendmentRelation] = []

        for m in self._TITLE_PATTERN.finditer(title):
            # Determine amendment type from the keyword preceding "atas"
            keyword = m.group(0).split()[0].lower()
            amendment_type = self._TITLE_TYPE_MAP.get(keyword)
            if amendment_type is None:
                continue

            target_text = m.group("target")
            canonical = self._parse_target(target_text)
            if canonical is None:
                logger.warning(
                    "Could not parse target regulation from title: %r", target_text
                )
                continue

            results.append(
                AmendmentRelation(
                    source_regulation=regulation_id,
                    target_regulation=canonical,
                    amendment_type=amendment_type,
                    raw_text=m.group(0),
                    confidence=0.8,
                )
            )

        return results
