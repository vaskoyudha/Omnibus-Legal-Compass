"""
Format converter for external regulation data sources.

Provides Pydantic schema adapters to transform external data sources
(HuggingFace Azzindani, OTF Peraturan) into the internal canonical
schema used by the ingestion pipeline.

Each adapter has a ``convert()`` method that accepts a single source
record (dict or string) and returns one or more ``RegulationChunk``
instances ready for downstream ingestion.

Usage::

    from backend.scripts.format_converter import (
        AzzindaniAdapter,
        OTFPeraturanAdapter,
        ManualAdapter,
    )

    adapter = AzzindaniAdapter()
    chunk = adapter.convert({
        "Regulation Name": "UU No. 11 Tahun 2020",
        "Regulation Number": "11",
        "Year": "2020",
        "About": "Cipta Kerja",
        "Chapter": "I",
        "Article": "1",
        "Content": "Dalam Undang-Undang ini yang dimaksud dengan ...",
    })
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Internal canonical schema
# ---------------------------------------------------------------------------

class RegulationChunk(BaseModel):
    """Canonical internal representation of a single regulation chunk.

    All external data sources are normalised into this schema before
    being passed to the ingestion pipeline.

    Attributes:
        jenis_dokumen: Document type code (``"UU"``, ``"PP"``, etc.).
        nomor: Regulation number as a string.
        tahun: Year of enactment as a string.
        judul: Short title / subject of the regulation.
        isi: Body text of the chunk (minimum 50 characters).
        bab: Chapter identifier, if applicable.
        pasal: Article number, if applicable.
        ayat: Sub-article (ayat) number, if applicable.
        penjelasan: ``True`` when this chunk is an explanatory section.
        effective_date: ISO-8601 date string when the regulation takes effect.
        source: Provenance tag indicating the upstream data source.

    Example::

        RegulationChunk(
            jenis_dokumen="UU",
            nomor="11",
            tahun="2020",
            judul="Cipta Kerja",
            isi="Dalam Undang-Undang ini yang dimaksud dengan ...",
            bab="I",
            pasal="1",
            source="huggingface_azzindani",
        )
    """

    jenis_dokumen: str  # "UU", "PP", "Perpres", "Permen", "Perda"
    nomor: str
    tahun: str
    judul: str
    isi: str  # Content text — validated: >= 50 chars
    bab: str | None = None
    pasal: str | None = None
    ayat: str | None = None
    penjelasan: bool = False
    effective_date: str | None = None  # ISO date string
    source: Literal[
        "huggingface_azzindani",
        "otf_peraturan",
        "manual",
    ]

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("isi")
    @classmethod
    def validate_content_length(cls, v: str) -> str:
        """Reject chunks whose body text is shorter than 50 characters.

        Short fragments typically arise from parsing artefacts or
        empty placeholder rows and carry no useful legal content.

        Raises:
            ValueError: When ``len(v) < 50``.
        """
        if len(v) < 50:
            raise ValueError(
                f"Content too short ({len(v)} chars, minimum 50)"
            )
        return v

    @field_validator("isi")
    @classmethod
    def detect_mojibake(cls, v: str) -> str:
        """Flag content that contains common mojibake byte sequences.

        Mojibake (garbled encoding) typically appears when UTF-8 text is
        misinterpreted as Latin-1 or Windows-1252.  The most frequent
        artefacts are the Unicode replacement character (``\\ufffd`` /
        ``\\u00ef\\u00bf\\u00bd``) and the ``\\u00c3`` prefix family.

        Raises:
            ValueError: When a mojibake pattern is detected.
        """
        # U+FFFD replacement character or raw bytes that encode it
        if "\ufffd" in v:
            raise ValueError(
                "Potential encoding issue detected (U+FFFD replacement character)"
            )
        # Common Latin-1-as-UTF-8 artefact family: Ã followed by another
        # Latin character (e.g. Ã©, Ã¯, Ã¼, Ã¶, Ã ).
        if re.search(r"\u00c3[\u0080-\u00bf]", v):
            raise ValueError(
                "Potential encoding issue detected (mojibake Ã-prefix pattern)"
            )
        return v

    @field_validator("tahun", mode="before")
    @classmethod
    def coerce_tahun_to_str(cls, v: Any) -> str:
        """Ensure ``tahun`` is stored as a string regardless of source type.

        The existing ``regulations.json`` stores ``tahun`` as an integer;
        external sources may provide it as a string.  This validator
        normalises both to ``str``.
        """
        return str(v)

    # ------------------------------------------------------------------
    # Conversion methods
    # ------------------------------------------------------------------

    def to_ingest_format(self) -> dict[str, Any]:
        """Convert to the format expected by ingest.py.

        The ingest.py script expects:
        - Field name ``text`` (not ``isi``)
        - Field ``tentang`` (uses ``judul`` as fallback if not present)
        - ``tahun`` as int (not string)

        Returns:
            Dictionary with keys compatible with create_document_chunks().
        """
        return {
            "text": self.isi,
            "jenis_dokumen": self.jenis_dokumen,
            "nomor": self.nomor,
            "tahun": int(self.tahun),
            "judul": self.judul,
            "tentang": self.judul,  # Use judul as tentang (same in most cases)
            "bab": self.bab,
            "pasal": self.pasal,
            "ayat": self.ayat,
        }


# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

_JENIS_PATTERN = re.compile(
    r"^(UU|PP|Perpres|Permen|Perda)\b", re.IGNORECASE
)

# Full Indonesian text patterns (for Azzindani dataset format)
_JENIS_FULL_TEXT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"UNDANG[- ]?UNDANG", re.IGNORECASE), "UU"),
    (re.compile(r"PERATURAN\s+PEMERINTAH", re.IGNORECASE), "PP"),
    (re.compile(r"PERATURAN\s+PRESIDEN", re.IGNORECASE), "Perpres"),
    (re.compile(r"PERATURAN\s+MENTERI", re.IGNORECASE), "Permen"),
    (re.compile(r"PERATURAN\s+DAERAH", re.IGNORECASE), "Perda"),
]

_TYPE_FOLDER_MAP: dict[str, str] = {
    "uu": "UU",
    "pp": "PP",
    "perpres": "Perpres",
    "permen": "Permen",
    "perda": "Perda",
}


def _parse_jenis_dokumen(regulation_name: str) -> str:
    """Extract the document-type prefix from a regulation name string.

    Args:
        regulation_name: Free-text regulation name, e.g.
            ``"UU No. 11 Tahun 2020"`` or 
            ``"PERATURAN PEMERINTAH REPUBLIK INDONESIA"``.

    Returns:
        Canonical document-type code (``"UU"``, ``"PP"``, etc.).

    Raises:
        ValueError: When no known prefix is found.

    Examples::

        >>> _parse_jenis_dokumen("UU No. 11 Tahun 2020")
        'UU'
        >>> _parse_jenis_dokumen("Perpres No. 5 Tahun 2021")
        'Perpres'
        >>> _parse_jenis_dokumen("PERATURAN PEMERINTAH REPUBLIK INDONESIA")
        'PP'
        >>> _parse_jenis_dokumen("UNDANG-UNDANG REPUBLIK INDONESIA")
        'UU'
    """
    regulation_name = regulation_name.strip()
    
    # Try short form first (UU, PP, Perpres, etc.)
    match = _JENIS_PATTERN.match(regulation_name)
    if match:
        raw = match.group(1)
        return _TYPE_FOLDER_MAP.get(raw.lower(), raw)
    
    # Try full Indonesian text patterns
    for pattern, doc_type in _JENIS_FULL_TEXT_PATTERNS:
        if pattern.search(regulation_name):
            return doc_type
    
    # No match found
    raise ValueError(
        f"Cannot determine jenis_dokumen from: {regulation_name!r}"
    )


# ---------------------------------------------------------------------------
# Adapter base
# ---------------------------------------------------------------------------

class BaseAdapter:
    """Abstract base for source-specific adapters.

    Subclasses must implement :meth:`convert`.
    """

    def convert(self, raw: Any) -> RegulationChunk:
        """Transform a single source record into a ``RegulationChunk``.

        Args:
            raw: Source-specific record (dict, string, etc.).

        Returns:
            A validated :class:`RegulationChunk`.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# AzzindaniAdapter
# ---------------------------------------------------------------------------

class AzzindaniAdapter(BaseAdapter):
    """Adapter for the HuggingFace *Azzindani* dataset.

    Source schema::

        {
            "Regulation Name": "UU No. 11 Tahun 2020",
            "Regulation Number": "11",
            "Year": "2020",
            "About": "Cipta Kerja",
            "Chapter": "I",
            "Article": "1",
            "Content": "Dalam Undang-Undang ini yang dimaksud dengan ..."
        }

    Example::

        adapter = AzzindaniAdapter()
        chunk = adapter.convert(row_dict)
    """

    def convert(self, raw: dict[str, Any]) -> RegulationChunk:
        """Convert a single Azzindani dataset row.

        Args:
            raw: Dictionary with Azzindani column names.

        Returns:
            A validated :class:`RegulationChunk`.

        Raises:
            ValueError: On missing required fields or validation failure.
        """
        regulation_name: str = raw.get("Regulation Name", "")
        jenis = _parse_jenis_dokumen(regulation_name)

        return RegulationChunk(
            jenis_dokumen=jenis,
            nomor=str(raw.get("Regulation Number", "")),
            tahun=str(raw.get("Year", "")),
            judul=raw.get("About", ""),
            isi=raw.get("Content", ""),
            bab=raw.get("Chapter") or None,
            pasal=str(raw["Article"]) if raw.get("Article") else None,
            source="huggingface_azzindani",
        )


# ---------------------------------------------------------------------------
# OTFPeraturanAdapter
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_FM_FIELD_RE = re.compile(r"^(\w+)\s*:\s*(.+)$", re.MULTILINE)


class OTFPeraturanAdapter(BaseAdapter):
    """Adapter for Open-Technology-Foundation *peraturan.go.id* markdown files.

    Each source file is a single markdown document with YAML-style
    frontmatter followed by regulation body text::

        ---
        type: UU
        number: 11
        year: 2020
        title: Cipta Kerja
        ---

        # Content starts here
        Dalam Undang-Undang ini yang dimaksud dengan ...

    The adapter can also accept a pre-parsed dictionary with keys
    ``type``, ``number``, ``year``, ``title``, and ``content``.

    Example::

        adapter = OTFPeraturanAdapter()
        chunk = adapter.convert(markdown_string)
    """

    @staticmethod
    def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
        """Split a markdown file into frontmatter dict and body text.

        Args:
            text: Raw markdown file contents.

        Returns:
            A 2-tuple ``(metadata_dict, body_text)``.

        Raises:
            ValueError: If no valid frontmatter block is found.
        """
        fm_match = _FRONTMATTER_RE.match(text)
        if not fm_match:
            raise ValueError("No YAML frontmatter found in markdown input")
        fm_block = fm_match.group(1)
        body = text[fm_match.end():].strip()

        meta: dict[str, str] = {}
        for m in _FM_FIELD_RE.finditer(fm_block):
            meta[m.group(1).lower()] = m.group(2).strip()

        return meta, body

    def convert(self, raw: str | dict[str, Any]) -> RegulationChunk:
        """Convert an OTF Peraturan markdown file or pre-parsed dict.

        Args:
            raw: Either a raw markdown string (with frontmatter) or a
                dict with ``type``, ``number``, ``year``, ``title``,
                ``content`` keys.

        Returns:
            A validated :class:`RegulationChunk`.

        Raises:
            ValueError: On missing metadata or validation failure.
        """
        if isinstance(raw, str):
            meta, body = self._parse_frontmatter(raw)
        else:
            meta = {k.lower(): str(v) for k, v in raw.items()}
            body = meta.pop("content", "")

        jenis_raw = meta.get("type", "")
        jenis = _TYPE_FOLDER_MAP.get(jenis_raw.lower(), jenis_raw)

        return RegulationChunk(
            jenis_dokumen=jenis,
            nomor=str(meta.get("number", "")),
            tahun=str(meta.get("year", "")),
            judul=meta.get("title", ""),
            isi=body,
            source="otf_peraturan",
        )


# ---------------------------------------------------------------------------
# ManualAdapter
# ---------------------------------------------------------------------------

class ManualAdapter(BaseAdapter):
    """Pass-through adapter for existing ``regulations.json`` entries.

    Validates that the record conforms to the canonical schema and
    applies minor normalisations (e.g. ``text`` -> ``isi``, adding
    ``source``).

    Source schema (``data/peraturan/regulations.json``)::

        {
            "jenis_dokumen": "UU",
            "nomor": "11",
            "tahun": 2020,
            "judul": "Cipta Kerja",
            "tentang": "Cipta Kerja (Omnibus Law)",
            "bab": "I",
            "pasal": "1",
            "text": "Dalam Undang-Undang ini ..."
        }

    Example::

        adapter = ManualAdapter()
        chunk = adapter.convert(json_entry)
    """

    def convert(self, raw: dict[str, Any]) -> RegulationChunk:
        """Convert an existing ``regulations.json`` entry.

        Key transformations:

        * ``text`` is mapped to ``isi`` (if ``isi`` is not already present).
        * ``tentang`` is dropped (redundant with ``judul``).
        * ``source`` defaults to ``"manual"`` when absent.
        * ``tahun`` is coerced to string.

        Args:
            raw: Dictionary from ``regulations.json``.

        Returns:
            A validated :class:`RegulationChunk`.
        """
        # Prefer 'isi' if present; fall back to 'text'
        isi = raw.get("isi") or raw.get("text", "")

        return RegulationChunk(
            jenis_dokumen=raw.get("jenis_dokumen", ""),
            nomor=str(raw.get("nomor", "")),
            tahun=raw.get("tahun", 0),  # coerced to str by validator
            judul=raw.get("judul", ""),
            isi=isi,
            bab=raw.get("bab") or None,
            pasal=str(raw["pasal"]) if raw.get("pasal") else None,
            ayat=str(raw["ayat"]) if raw.get("ayat") else None,
            source=raw.get("source", "manual"),
        )


# ---------------------------------------------------------------------------
# __main__ — self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from pydantic import ValidationError

    errors: list[str] = []

    def _assert(condition: bool, label: str) -> None:
        if not condition:
            errors.append(label)
            print(f"  FAIL: {label}")
        else:
            print(f"  OK:   {label}")

    # ---- AzzindaniAdapter ------------------------------------------------
    print("\n=== AzzindaniAdapter ===")
    az = AzzindaniAdapter()

    sample_az = {
        "Regulation Name": "UU No. 11 Tahun 2020",
        "Regulation Number": "11",
        "Year": "2020",
        "About": "Cipta Kerja",
        "Chapter": "I",
        "Article": "1",
        "Content": (
            "Dalam Undang-Undang ini yang dimaksud dengan: "
            "1. Cipta Kerja adalah upaya penciptaan kerja."
        ),
    }
    chunk = az.convert(sample_az)
    _assert(chunk.jenis_dokumen == "UU", "jenis_dokumen == 'UU'")
    _assert(chunk.nomor == "11", "nomor == '11'")
    _assert(chunk.tahun == "2020", "tahun == '2020'")
    _assert(chunk.judul == "Cipta Kerja", "judul")
    _assert(chunk.bab == "I", "bab == 'I'")
    _assert(chunk.pasal == "1", "pasal == '1'")
    _assert(chunk.source == "huggingface_azzindani", "source")
    _assert(len(chunk.isi) >= 50, "isi length >= 50")

    # Perpres prefix parsing
    sample_az2 = {**sample_az, "Regulation Name": "Perpres No. 5 Tahun 2021"}
    chunk2 = az.convert(sample_az2)
    _assert(chunk2.jenis_dokumen == "Perpres", "Perpres prefix parsing")

    # PP prefix parsing
    sample_az3 = {**sample_az, "Regulation Name": "PP No. 24 Tahun 2018"}
    chunk3 = az.convert(sample_az3)
    _assert(chunk3.jenis_dokumen == "PP", "PP prefix parsing")

    # ---- OTFPeraturanAdapter ---------------------------------------------
    print("\n=== OTFPeraturanAdapter ===")
    otf = OTFPeraturanAdapter()

    sample_md = """\
---
type: UU
number: 11
year: 2020
title: Cipta Kerja
---

Dalam Undang-Undang ini yang dimaksud dengan: 1. Cipta Kerja adalah upaya penciptaan kerja melalui usaha kemudahan."""

    chunk_otf = otf.convert(sample_md)
    _assert(chunk_otf.jenis_dokumen == "UU", "jenis_dokumen == 'UU'")
    _assert(chunk_otf.nomor == "11", "nomor == '11'")
    _assert(chunk_otf.tahun == "2020", "tahun == '2020'")
    _assert(chunk_otf.judul == "Cipta Kerja", "judul")
    _assert(chunk_otf.source == "otf_peraturan", "source")
    _assert(len(chunk_otf.isi) >= 50, "isi length >= 50")

    # Dict-based input
    chunk_otf2 = otf.convert({
        "type": "PP",
        "number": "24",
        "year": "2018",
        "title": "Perizinan Berusaha",
        "content": (
            "Perizinan Berusaha adalah legalitas yang diberikan kepada "
            "Pelaku Usaha untuk memulai dan menjalankan usaha."
        ),
    })
    _assert(chunk_otf2.jenis_dokumen == "PP", "dict input: PP")
    _assert(chunk_otf2.source == "otf_peraturan", "dict input: source")

    # ---- ManualAdapter ---------------------------------------------------
    print("\n=== ManualAdapter ===")
    manual = ManualAdapter()

    sample_manual = {
        "jenis_dokumen": "UU",
        "nomor": "11",
        "tahun": 2020,
        "judul": "Cipta Kerja",
        "tentang": "Cipta Kerja (Omnibus Law)",
        "bab": "I",
        "pasal": "1",
        "text": (
            "Dalam Undang-Undang ini yang dimaksud dengan: "
            "1. Cipta Kerja adalah upaya penciptaan kerja."
        ),
    }
    chunk_m = manual.convert(sample_manual)
    _assert(chunk_m.jenis_dokumen == "UU", "jenis_dokumen")
    _assert(chunk_m.tahun == "2020", "tahun coerced to str")
    _assert(chunk_m.source == "manual", "source defaults to 'manual'")
    _assert(chunk_m.isi == sample_manual["text"], "text -> isi mapping")
    _assert(chunk_m.bab == "I", "bab preserved")
    _assert(chunk_m.pasal == "1", "pasal preserved")

    # ---- Validation: short content ---------------------------------------
    print("\n=== Validation: short content ===")
    try:
        RegulationChunk(
            jenis_dokumen="UU",
            nomor="1",
            tahun="2020",
            judul="Test",
            isi="Too short",
            source="manual",
        )
        _assert(False, "should reject isi < 50 chars")
    except ValidationError:
        _assert(True, "rejects isi < 50 chars")

    # ---- Validation: mojibake --------------------------------------------
    print("\n=== Validation: mojibake ===")
    try:
        RegulationChunk(
            jenis_dokumen="UU",
            nomor="1",
            tahun="2020",
            judul="Test",
            isi="Dalam Undang-Undang ini \ufffd yang dimaksud dengan hal-hal penting berikut ini",
            source="manual",
        )
        _assert(False, "should reject U+FFFD mojibake")
    except ValidationError:
        _assert(True, "rejects U+FFFD mojibake")

    try:
        RegulationChunk(
            jenis_dokumen="UU",
            nomor="1",
            tahun="2020",
            judul="Test",
            isi="Dalam Undang-Undang ini Ã© yang dimaksud dengan hal-hal penting berikut ini",
            source="manual",
        )
        _assert(False, "should reject Ã-prefix mojibake")
    except ValidationError:
        _assert(True, "rejects Ã-prefix mojibake")

    # ---- Validation: bad regulation name ---------------------------------
    print("\n=== Validation: bad regulation name ===")
    try:
        _parse_jenis_dokumen("Unknown Document Type 123")
        _assert(False, "should reject unknown jenis_dokumen prefix")
    except ValueError:
        _assert(True, "rejects unknown jenis_dokumen prefix")

    # ---- Summary ---------------------------------------------------------
    print()
    if errors:
        print(f"FAILED ({len(errors)} failures):")
        for e in errors:
            print(f"  - {e}")
        raise SystemExit(1)
    else:
        print("All adapter tests passed (OK)")
