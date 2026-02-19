"""
Cross-reference extraction for Indonesian legal documents.

Identifies legal citation patterns in regulation text and normalizes them
to canonical form (e.g. "UU-27-2022") for knowledge graph edges.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class LegalReference:
    """A normalized legal citation extracted from Indonesian regulation text."""

    raw_text: str
    jenis: str  # UU, PP, Perpres, Permen, etc.
    nomor: str
    tahun: str
    relation: str | None  # dimaksud/diubah/dicabut/None
    canonical: str  # "UU-27-2022"


# ── Regex Patterns ───────────────────────────────────────────────────────────

PATTERN_STANDARD = re.compile(
    r"(?P<jenis>Undang-Undang|Peraturan Pemerintah|Peraturan Presiden"
    r"|Peraturan Menteri|Keputusan Presiden)"
    r"\s+Nomor\s+(?P<nomor>\d+(?:/[A-Z]+)?)"
    r"\s+Tahun\s+(?P<tahun>\d{4})",
    re.IGNORECASE,
)

PATTERN_ABBREVIATED = re.compile(
    r"(?P<jenis>UU|PP|Perpres|Permen|Keppres|PMK|Perppu)"
    r"(?:\s+No\.?|\s+Nomor)?\s*"
    r"(?P<nomor>\d+)"
    r"(?:/|(?:\s+Tahun\s+))"
    r"(?P<tahun>\d{4})",
    re.IGNORECASE,
)

PATTERN_CROSS_REF = re.compile(
    r"sebagaimana\s+(?P<relation>dimaksud dalam|telah diubah dengan"
    r"|telah dicabut dengan|tercantum dalam)"
    r"\s+(?P<citation>(?:Undang-Undang|UU|PP|Perpres).*?(?:Tahun\s+\d{4}|\d{4}))",
    re.IGNORECASE,
)

PATTERN_AMENDMENTS = re.compile(
    r"telah\s+(?P<count>\w+\s+kali\s+)?"
    r"(?P<action>diubah|dicabut|diganti)"
    r"(?:\s+terakhir)?"
    r"\s+dengan\s+"
    r"(?P<citation>(?:PP|UU|Perpres|Permen).*?(?:Tahun\s+\d{4}|\d{4}))",
    re.IGNORECASE,
)


# ── Normalization Map ────────────────────────────────────────────────────────

JENIS_MAP: dict[str, str] = {
    "undang-undang": "UU",
    "peraturan pemerintah": "PP",
    "peraturan presiden": "Perpres",
    "peraturan menteri": "Permen",
    "keputusan presiden": "Keppres",
}

# Known abbreviations for pass-through validation
_KNOWN_ABBREVIATIONS = {"uu", "pp", "perpres", "permen", "keppres", "pmk", "perppu"}

# Canonical title-case forms for abbreviations
_ABBREV_CANONICAL: dict[str, str] = {
    "uu": "UU",
    "pp": "PP",
    "perpres": "Perpres",
    "permen": "Permen",
    "keppres": "Keppres",
    "pmk": "PMK",
    "perppu": "Perppu",
}


def normalize_jenis(jenis: str) -> str:
    """Normalize regulation type to canonical abbreviated form.

    Handles:
    - Full Indonesian names: "Undang-Undang" → "UU"
    - Already abbreviated: "UU" → "UU", "pp" → "PP"
    - Mixed case / extra whitespace: "  peraturan   pemerintah  " → "PP"
    """
    cleaned = " ".join(jenis.strip().split()).lower()

    # Check full-text map first
    if cleaned in JENIS_MAP:
        return JENIS_MAP[cleaned]

    # Already an abbreviation — return canonical title-case
    if cleaned in _ABBREV_CANONICAL:
        return _ABBREV_CANONICAL[cleaned]

    # Fallback: return title-cased input (preserves unknown types)
    return jenis.strip().title()


def _extract_from_citation(citation_text: str) -> tuple[str, str, str] | None:
    """Extract (jenis, nomor, tahun) from a citation substring.

    Used for PATTERN_CROSS_REF and PATTERN_AMENDMENTS where the citation
    is captured as a single group that needs sub-parsing.
    """
    # Try standard pattern first
    m = PATTERN_STANDARD.search(citation_text)
    if m:
        return m.group("jenis"), m.group("nomor"), m.group("tahun")

    # Try abbreviated pattern
    m = PATTERN_ABBREVIATED.search(citation_text)
    if m:
        return m.group("jenis"), m.group("nomor"), m.group("tahun")

    return None


def extract_legal_references(text: str) -> list[LegalReference]:
    """Extract all legal cross-references from Indonesian legal text.

    Runs all 4 regex patterns against the text, normalizes each match,
    deduplicates by canonical form, and returns sorted results.
    """
    if not text or not text.strip():
        return []

    seen: dict[str, LegalReference] = {}

    # ── Pattern 1: Standard full-form citations ──────────────────────────
    for m in PATTERN_STANDARD.finditer(text):
        jenis = normalize_jenis(m.group("jenis"))
        nomor = m.group("nomor")
        tahun = m.group("tahun")
        canonical = f"{jenis}-{nomor}-{tahun}"
        if canonical not in seen:
            seen[canonical] = LegalReference(
                raw_text=m.group(0),
                jenis=jenis,
                nomor=nomor,
                tahun=tahun,
                relation=None,
                canonical=canonical,
            )

    # ── Pattern 2: Abbreviated citations ─────────────────────────────────
    for m in PATTERN_ABBREVIATED.finditer(text):
        jenis = normalize_jenis(m.group("jenis"))
        nomor = m.group("nomor")
        tahun = m.group("tahun")
        canonical = f"{jenis}-{nomor}-{tahun}"
        if canonical not in seen:
            seen[canonical] = LegalReference(
                raw_text=m.group(0),
                jenis=jenis,
                nomor=nomor,
                tahun=tahun,
                relation=None,
                canonical=canonical,
            )

    # ── Pattern 3: Cross-reference citations ─────────────────────────────
    for m in PATTERN_CROSS_REF.finditer(text):
        relation = m.group("relation").strip()
        citation = m.group("citation")
        parsed = _extract_from_citation(citation)
        if parsed:
            jenis_raw, nomor, tahun = parsed
            jenis = normalize_jenis(jenis_raw)
            canonical = f"{jenis}-{nomor}-{tahun}"
            if canonical not in seen:
                seen[canonical] = LegalReference(
                    raw_text=m.group(0),
                    jenis=jenis,
                    nomor=nomor,
                    tahun=tahun,
                    relation=relation,
                    canonical=canonical,
                )
            elif seen[canonical].relation is None:
                # Upgrade: earlier pattern matched without relation context
                seen[canonical] = LegalReference(
                    raw_text=m.group(0),
                    jenis=jenis,
                    nomor=nomor,
                    tahun=tahun,
                    relation=relation,
                    canonical=canonical,
                )

    # ── Pattern 4: Amendment citations ───────────────────────────────────
    for m in PATTERN_AMENDMENTS.finditer(text):
        action = m.group("action").strip()
        citation = m.group("citation")
        parsed = _extract_from_citation(citation)
        if parsed:
            jenis_raw, nomor, tahun = parsed
            jenis = normalize_jenis(jenis_raw)
            canonical = f"{jenis}-{nomor}-{tahun}"
            if canonical not in seen:
                seen[canonical] = LegalReference(
                    raw_text=m.group(0),
                    jenis=jenis,
                    nomor=nomor,
                    tahun=tahun,
                    relation=action,
                    canonical=canonical,
                )
            elif seen[canonical].relation is None:
                # Upgrade: earlier pattern matched without relation context
                seen[canonical] = LegalReference(
                    raw_text=m.group(0),
                    jenis=jenis,
                    nomor=nomor,
                    tahun=tahun,
                    relation=action,
                    canonical=canonical,
                )

    return sorted(seen.values(), key=lambda ref: ref.canonical)
