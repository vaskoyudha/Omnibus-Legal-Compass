"""
Multi-format markdown parser for Indonesian legal documents.

Detects format patterns (A/B/C/D/E/F) and extracts structured
metadata + content from the indonesian-legal-docs repository.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Format pattern enum
# ---------------------------------------------------------------------------


class FormatPattern(str, Enum):
    """Classification of markdown document formats in the legal corpus."""

    STRUCTURED = "A"        # MENIMBANG/MENGINGAT/BAB/Pasal
    YAML_FRONTMATTER = "B"  # --- yaml ---
    OCR_CONVERTED = "C"     # PDF OCR text
    CATALOG = "D"           # Metadata-only lists
    BINARY = "E"            # Binary disguised as .md
    README = "F"            # README/navigation (skip)


# ---------------------------------------------------------------------------
# Parsed regulation dataclass
# ---------------------------------------------------------------------------


@dataclass
class ParsedRegulation:
    """Structured output from parsing a single markdown regulation file."""

    filepath: str
    format_pattern: FormatPattern
    regulation_id: str         # Canonical: "UU-27-2022"
    jenis_dokumen: str         # UU, PP, Perpres, Permen, PMK, etc.
    nomor: str
    tahun: str
    judul: str
    ministry: Optional[str] = None
    effective_date: Optional[str] = None
    legal_basis: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    content: str = ""
    chapters: list[str] = field(default_factory=list)
    articles: list[int] = field(default_factory=list)
    has_full_text: bool = True
    quality_flag: Optional[str] = None
    content_hash: str = ""
    yaml_metadata: dict[str, Any] = field(default_factory=dict)
    source: str = "markdown_repo"


# ---------------------------------------------------------------------------
# Binary detection helpers
# ---------------------------------------------------------------------------

TEXTCHARS = bytearray(
    {7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7F}
)


def is_binary_string(data: bytes) -> bool:
    """Return True if *data* contains non-text bytes."""
    return bool(data.translate(None, TEXTCHARS))


def is_binary_file(filepath: Path, chunk_size: int = 1024) -> bool:
    """Return True if the first *chunk_size* bytes of *filepath* look binary."""
    try:
        with open(filepath, "rb") as f:
            return is_binary_string(f.read(chunk_size))
    except Exception:
        return True


# ---------------------------------------------------------------------------
# Content hashing — BLAKE2b 256-bit
# ---------------------------------------------------------------------------


def compute_content_hash(text: str) -> str:
    """Return a BLAKE2b hex digest (256-bit) of whitespace-normalised *text*."""
    normalized = " ".join(text.split())
    return hashlib.blake2b(normalized.encode("utf-8"), digest_size=32).hexdigest()


# ---------------------------------------------------------------------------
# Filename regex patterns
# ---------------------------------------------------------------------------

# Ministry name → display label mapping
_MINISTRY_MAP: dict[str, str] = {
    "esdm": "Kementerian ESDM",
    "kemhan": "Kementerian Pertahanan",
    "kemdikbud": "Kementerian Pendidikan dan Kebudayaan",
    "kemenhub": "Kementerian Perhubungan",
    "kemenkeu": "Kementerian Keuangan",
}

# Jenis abbreviation → canonical label for hierarchy patterns
_HIERARCHY_JENIS: dict[str, str] = {
    "uu": "UU",
    "pp": "PP",
    "perppu": "Perppu",
    "perpres": "Perpres",
}

# Each tuple: (compiled regex, optional jenis_map)
# Groups are documented inline.
FILENAME_PATTERNS: list[tuple[re.Pattern[str], dict[str, str] | None]] = [
    # Pattern 1: Hierarchy docs — (uu|pp|perppu|perpres)-{nomor}-{tahun}.md
    (
        re.compile(r"(uu|pp|perppu|perpres)-(\d+)-(\d{4})\.md"),
        _HIERARCHY_JENIS,
    ),
    # Pattern 2: Ministry permen — permen-{ministry}-{nomor}-{tahun}.md
    (
        re.compile(r"permen-(esdm|kemhan|kemdikbud|kemenhub|kemenkeu)-(\d+)-(\d{4})\.md"),
        None,
    ),
    # Pattern 3: Kemenhub specific — permenhub-{nomor}-{tahun}.md
    (
        re.compile(r"permenhub-(\d+)-(\d{4})\.md"),
        None,
    ),
    # Pattern 4: PMK — pmk-{nomor}-{tahun}.md
    (
        re.compile(r"pmk-(\d+)-(\d{4})\.md"),
        None,
    ),
    # Pattern 5: Kemkomdigi — perkomdigi-{nomor}-{tahun}[-slug].md
    (
        re.compile(r"perkomdigi-(\d+)-(\d{4})(?:-[\w-]+)?\.md"),
        None,
    ),
]

# Catalog-heuristic keywords matched against the filename stem
_CATALOG_KEYWORDS = frozenset(
    ["database", "catalog", "comprehensive-list", "regulations", "by-year"]
)


# ---------------------------------------------------------------------------
# MarkdownParser
# ---------------------------------------------------------------------------


class MarkdownParser:
    """Multi-format router: detect pattern -> parse with appropriate strategy."""

    # ------------------------------------------------------------------
    # Format detection
    # ------------------------------------------------------------------

    def detect_format(self, filepath: Path) -> FormatPattern:
        """Detect the format pattern for a markdown file."""

        # 1. Binary check (first 1024 bytes)
        if is_binary_file(filepath):
            return FormatPattern.BINARY

        # 2. README filename check
        if filepath.name.lower() == "readme.md":
            return FormatPattern.README

        content = filepath.read_text(encoding="utf-8", errors="replace")

        # 3. Starts with --- → YAML_FRONTMATTER
        if content.strip().startswith("---"):
            return FormatPattern.YAML_FRONTMATTER

        # 4. OCR conversion header in the first 500 chars
        head = content[:500]
        if "**Source File:**" in head or "**Converted:**" in head:
            return FormatPattern.OCR_CONVERTED

        # 5. Catalog keywords in filename stem
        stem_lower = filepath.stem.lower()
        if any(kw in stem_lower for kw in _CATALOG_KEYWORDS):
            return FormatPattern.CATALOG

        # 6. Default: structured legal text
        return FormatPattern.STRUCTURED

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def parse(self, filepath: Path) -> ParsedRegulation:
        """Parse any markdown file into structured regulation data."""
        pattern = self.detect_format(filepath)

        if pattern == FormatPattern.BINARY:
            return self._create_binary_stub(filepath)
        if pattern == FormatPattern.README:
            return self._create_readme_stub(filepath)
        if pattern == FormatPattern.YAML_FRONTMATTER:
            return self._parse_pattern_b(filepath)
        if pattern == FormatPattern.OCR_CONVERTED:
            return self._parse_pattern_c(filepath)
        if pattern == FormatPattern.CATALOG:
            return self._parse_pattern_d(filepath)
        return self._parse_pattern_a(filepath)

    # ------------------------------------------------------------------
    # Filename metadata extraction
    # ------------------------------------------------------------------

    @staticmethod
    def extract_filename_metadata(filepath: Path) -> dict[str, str]:
        """Extract jenis_dokumen, nomor, tahun (and ministry) from filename.

        Returns a dict with keys: jenis_dokumen, nomor, tahun, and
        optionally ministry.  Returns an empty dict on no match.
        """
        name = filepath.name.lower()

        for regex, jenis_map in FILENAME_PATTERNS:
            m = regex.match(name)
            if not m:
                continue

            groups = m.groups()

            # Pattern 1: hierarchy — groups = (jenis_abbr, nomor, tahun)
            if jenis_map is not None:
                return {
                    "jenis_dokumen": jenis_map[groups[0]],
                    "nomor": groups[1],
                    "tahun": groups[2],
                }

            # Pattern 2: ministry permen — groups = (ministry, nomor, tahun)
            if "permen-" in name and len(groups) == 3:
                ministry_key = groups[0]
                return {
                    "jenis_dokumen": "Permen",
                    "nomor": groups[1],
                    "tahun": groups[2],
                    "ministry": _MINISTRY_MAP.get(ministry_key, ministry_key),
                }

            # Pattern 3: permenhub — groups = (nomor, tahun)
            if name.startswith("permenhub"):
                return {
                    "jenis_dokumen": "Permen",
                    "nomor": groups[0],
                    "tahun": groups[1],
                    "ministry": "Kementerian Perhubungan",
                }

            # Pattern 4: pmk — groups = (nomor, tahun)
            if name.startswith("pmk"):
                return {
                    "jenis_dokumen": "PMK",
                    "nomor": groups[0],
                    "tahun": groups[1],
                    "ministry": "Kementerian Keuangan",
                }

            # Pattern 5: perkomdigi — groups = (nomor, tahun)
            if name.startswith("perkomdigi"):
                return {
                    "jenis_dokumen": "Permen",
                    "nomor": groups[0],
                    "tahun": groups[1],
                    "ministry": "Kementerian Komunikasi dan Digital",
                }

        return {}

    # ------------------------------------------------------------------
    # Canonical regulation ID builder
    # ------------------------------------------------------------------

    @staticmethod
    def build_regulation_id(jenis: str, nomor: str, tahun: str) -> str:
        """Build a canonical regulation ID like ``UU-27-2022``."""
        return f"{jenis}-{nomor}-{tahun}"

    # ------------------------------------------------------------------
    # Pattern A: Structured legal text
    # ------------------------------------------------------------------

    def _parse_pattern_a(self, filepath: Path) -> ParsedRegulation:
        """Parse structured Indonesian legal format (MENIMBANG/MENGINGAT/BAB/Pasal)."""
        content = filepath.read_text(encoding="utf-8", errors="replace")
        meta = self.extract_filename_metadata(filepath)

        jenis = meta.get("jenis_dokumen", "Unknown")
        nomor = meta.get("nomor", "")
        tahun = meta.get("tahun", "")
        ministry = meta.get("ministry")

        # Title from first # heading
        judul = ""
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if title_match:
            judul = title_match.group(1).strip()

        # Inline metadata: - **Nomor:** ...
        nomor_match = re.search(r"-\s*\*\*Nomor:\*\*\s*(.+)", content)
        if nomor_match:
            nomor_text = nomor_match.group(1).strip()
            # Try to extract number and year from "UU No. 27 Tahun 2022"
            num_year = re.search(r"(?:No\.?\s*)?(\d+)\s+Tahun\s+(\d{4})", nomor_text)
            if num_year:
                nomor = nomor or num_year.group(1)
                tahun = tahun or num_year.group(2)

        # Tentang
        tentang_match = re.search(r"-\s*\*\*Tentang:\*\*\s*(.+)", content)
        if tentang_match:
            judul = judul or tentang_match.group(1).strip()

        # Effective date
        effective_date: str | None = None
        date_match = re.search(r"-\s*\*\*Diundangkan:\*\*\s*(.+)", content)
        if date_match:
            effective_date = date_match.group(1).strip()

        # Chapters from ## BAB headings
        chapters: list[str] = re.findall(
            r"^##\s+BAB\s+[IVXLCDM]+\s*[-—]\s*(.+)$", content, re.MULTILINE
        )

        # Articles from ### Pasal headings
        articles: list[int] = []
        for m in re.finditer(r"^###\s+Pasal\s+(\d+)", content, re.MULTILINE):
            articles.append(int(m.group(1)))

        # Legal basis from MENGINGAT section
        legal_basis: list[str] = []
        mengingat_match = re.search(
            r"##\s*MENGINGAT[:\s]*\n(.*?)(?=\n##\s|\Z)",
            content,
            re.DOTALL | re.IGNORECASE,
        )
        if mengingat_match:
            basis_text = mengingat_match.group(1)
            # Extract individual UU/PP references
            for ref in re.finditer(
                r"(?:Undang-Undang|UU|Pasal)\s+(?:Nomor\s+)?\d+",
                basis_text,
            ):
                legal_basis.append(ref.group(0).strip())

        regulation_id = self.build_regulation_id(jenis, nomor, tahun)
        content_hash = compute_content_hash(content)

        return ParsedRegulation(
            filepath=str(filepath),
            format_pattern=FormatPattern.STRUCTURED,
            regulation_id=regulation_id,
            jenis_dokumen=jenis,
            nomor=nomor,
            tahun=tahun,
            judul=judul,
            ministry=ministry,
            effective_date=effective_date,
            legal_basis=legal_basis,
            chapters=chapters,
            articles=articles,
            content=content,
            content_hash=content_hash,
        )

    # ------------------------------------------------------------------
    # Pattern B: YAML frontmatter (non-standard: YAML inside code fence)
    # ------------------------------------------------------------------

    def _parse_pattern_b(self, filepath: Path) -> ParsedRegulation:
        """Parse YAML frontmatter + structured text.

        The actual ESDM/Kemkomdigi files wrap YAML inside a markdown code
        fence within ``---`` delimiters::

            ---
            **Metadata:**
            ```yaml
            regulation_id: "PERMEN-ESDM-19-2010"
            ...
            ```
            ---

        We must extract the YAML from the code fence, not rely on
        ``python-frontmatter`` which cannot handle this format.
        """
        raw = filepath.read_text(encoding="utf-8", errors="replace")
        meta = self.extract_filename_metadata(filepath)

        # Split on the first pair of --- delimiters
        yaml_metadata: dict[str, Any] = {}
        body = raw

        stripped = raw.strip()
        if stripped.startswith("---"):
            # Find the closing ---
            end_idx = stripped.find("---", 3)
            if end_idx != -1:
                frontmatter_block = stripped[3:end_idx]
                body = stripped[end_idx + 3:].strip()

                # Extract YAML from code fence markers
                fence_match = re.search(
                    r"```(?:yaml|yml)\s*\n(.*?)```",
                    frontmatter_block,
                    re.DOTALL,
                )
                if fence_match:
                    yaml_text = fence_match.group(1)
                else:
                    # Fallback: treat the entire frontmatter block as YAML
                    # (after stripping non-YAML lines like **Metadata:**)
                    lines = frontmatter_block.strip().splitlines()
                    yaml_lines = [
                        ln for ln in lines
                        if not ln.strip().startswith("**") and ln.strip()
                    ]
                    yaml_text = "\n".join(yaml_lines)

                try:
                    parsed = yaml.safe_load(yaml_text)
                    if isinstance(parsed, dict):
                        yaml_metadata = parsed
                except yaml.YAMLError:
                    logger.warning("Failed to parse YAML in %s", filepath)

        # Build fields from YAML metadata + filename fallback
        jenis = meta.get("jenis_dokumen", "Permen")
        nomor = str(yaml_metadata.get("number", meta.get("nomor", "")))
        tahun = str(yaml_metadata.get("year", meta.get("tahun", "")))
        judul = yaml_metadata.get("title", "")
        ministry = yaml_metadata.get("ministry", meta.get("ministry"))
        effective_date = yaml_metadata.get("effective_date")
        if effective_date is not None:
            effective_date = str(effective_date)

        legal_basis = yaml_metadata.get("legal_basis", [])
        if not isinstance(legal_basis, list):
            legal_basis = [str(legal_basis)]

        keywords = yaml_metadata.get("keywords", [])
        if not isinstance(keywords, list):
            keywords = [str(keywords)]

        regulation_id_raw = yaml_metadata.get("regulation_id", "")
        if regulation_id_raw:
            regulation_id = str(regulation_id_raw)
        else:
            regulation_id = self.build_regulation_id(jenis, nomor, tahun)

        content_hash = compute_content_hash(body) if body else ""

        return ParsedRegulation(
            filepath=str(filepath),
            format_pattern=FormatPattern.YAML_FRONTMATTER,
            regulation_id=regulation_id,
            jenis_dokumen=jenis,
            nomor=nomor,
            tahun=tahun,
            judul=judul,
            ministry=ministry,
            effective_date=effective_date,
            legal_basis=legal_basis,
            keywords=keywords,
            content=body,
            content_hash=content_hash,
            yaml_metadata=yaml_metadata,
        )

    # ------------------------------------------------------------------
    # Pattern C: OCR-converted text
    # ------------------------------------------------------------------

    def _parse_pattern_c(self, filepath: Path) -> ParsedRegulation:
        """Parse OCR-converted text with basic cleanup."""
        content = filepath.read_text(encoding="utf-8", errors="replace")
        meta = self.extract_filename_metadata(filepath)

        jenis = meta.get("jenis_dokumen", "Unknown")
        nomor = meta.get("nomor", "")
        tahun = meta.get("tahun", "")
        ministry = meta.get("ministry")

        # Title from first # heading
        judul = ""
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if title_match:
            judul = title_match.group(1).strip()

        # Basic OCR cleanup: collapse multiple blank lines, fix stray whitespace
        cleaned = re.sub(r"\n{3,}", "\n\n", content)
        cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)

        regulation_id = self.build_regulation_id(jenis, nomor, tahun)
        content_hash = compute_content_hash(cleaned)

        return ParsedRegulation(
            filepath=str(filepath),
            format_pattern=FormatPattern.OCR_CONVERTED,
            regulation_id=regulation_id,
            jenis_dokumen=jenis,
            nomor=nomor,
            tahun=tahun,
            judul=judul,
            ministry=ministry,
            content=cleaned,
            content_hash=content_hash,
            quality_flag="ocr",
        )

    # ------------------------------------------------------------------
    # Pattern D: Catalog / index files
    # ------------------------------------------------------------------

    def _parse_pattern_d(self, filepath: Path) -> ParsedRegulation:
        """Extract metadata from catalog/index files (no full text)."""
        content = filepath.read_text(encoding="utf-8", errors="replace")
        meta = self.extract_filename_metadata(filepath)

        jenis = meta.get("jenis_dokumen", "Unknown")
        nomor = meta.get("nomor", "")
        tahun = meta.get("tahun", "")

        # Title from first # heading
        judul = ""
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if title_match:
            judul = title_match.group(1).strip()

        # Extract regulation references from bullet lists
        # e.g. "- PMK 2/2023 - Komite Pengawas Perpajakan"
        legal_basis: list[str] = []
        ref_pattern = re.compile(
            r"[-*]\s+((?:PMK|UU|PP|Perpres|Permen)\s+\d+/?\d*)"
        )
        for m in ref_pattern.finditer(content):
            legal_basis.append(m.group(1).strip())

        regulation_id = self.build_regulation_id(jenis, nomor, tahun) if nomor else filepath.stem

        return ParsedRegulation(
            filepath=str(filepath),
            format_pattern=FormatPattern.CATALOG,
            regulation_id=regulation_id,
            jenis_dokumen=jenis,
            nomor=nomor,
            tahun=tahun,
            judul=judul,
            has_full_text=False,
            legal_basis=legal_basis,
            content="",
            content_hash="",
        )

    # ------------------------------------------------------------------
    # Stubs for binary and README files
    # ------------------------------------------------------------------

    def _create_binary_stub(self, filepath: Path) -> ParsedRegulation:
        """Return a minimal stub for a binary file disguised as .md."""
        meta = self.extract_filename_metadata(filepath)
        return ParsedRegulation(
            filepath=str(filepath),
            format_pattern=FormatPattern.BINARY,
            regulation_id=filepath.stem,
            jenis_dokumen=meta.get("jenis_dokumen", "Unknown"),
            nomor=meta.get("nomor", ""),
            tahun=meta.get("tahun", ""),
            judul="",
            has_full_text=False,
            quality_flag="binary",
        )

    def _create_readme_stub(self, filepath: Path) -> ParsedRegulation:
        """Return a minimal stub for a README/navigation file."""
        return ParsedRegulation(
            filepath=str(filepath),
            format_pattern=FormatPattern.README,
            regulation_id="README",
            jenis_dokumen="README",
            nomor="",
            tahun="",
            judul="README",
            has_full_text=False,
        )
