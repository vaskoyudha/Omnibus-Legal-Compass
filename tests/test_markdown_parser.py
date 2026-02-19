"""
Tests for multi-format markdown parser for Indonesian legal documents.

Covers format detection (A/B/C/D/E/F), binary detection, filename metadata
extraction, content hashing, and parsing for all pattern strategies.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from backend.scripts.markdown_parser import (
    FormatPattern,
    MarkdownParser,
    ParsedRegulation,
    compute_content_hash,
    is_binary_file,
    is_binary_string,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _write_file(tmp_path: Path, name: str, content: str) -> Path:
    """Write UTF-8 text to a temp file and return its path."""
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def _write_binary_file(tmp_path: Path, name: str, data: bytes) -> Path:
    """Write raw bytes to a temp file and return its path."""
    p = tmp_path / name
    p.write_bytes(data)
    return p


# ── Sample content constants ─────────────────────────────────────────────────


SAMPLE_PATTERN_A = """\
# UU No. 27 Tahun 2022 - Pelindungan Data Pribadi

## Metadata
- **Nomor:** UU No. 27 Tahun 2022
- **Tentang:** Pelindungan Data Pribadi
- **Diundangkan:** 17 Oktober 2022

## MENIMBANG:
a. bahwa negara menjamin kemerdekaan tiap-tiap penduduk;

## MENGINGAT:
Pasal 20 tentang hak konstitusional
Undang-Undang Nomor 39 tentang Hak Asasi Manusia

## BAB I \u2014 KETENTUAN UMUM

### Pasal 1
Dalam Undang-Undang ini yang dimaksud dengan:
1. **Data** adalah kumpulan informasi.

### Pasal 2
Undang-Undang ini berlaku untuk setiap orang.

## BAB II \u2014 RUANG LINGKUP

### Pasal 3
Ruang lingkup undang-undang ini.
"""

SAMPLE_PATTERN_B = """\
---
**Metadata:**
```yaml
regulation_id: "PERMEN-ESDM-19-2010"
title: "Tata Cara Penetapan Harga Minyak"
ministry: "Kementerian ESDM"
year: 2010
number: 19
category: "energy_mining"
effective_date: "2010-06-15"
legal_basis:
  - "UU-22-2001"
  - "PP-35-2004"
keywords:
  - minyak
  - gas
```
---

# Peraturan Menteri Energi dan Sumber Daya Mineral

## MENIMBANG
bahwa dalam rangka mempercepat pelaksanaan...

### Pasal 1
Gas Bumi adalah hasil proses alami.
"""

SAMPLE_PATTERN_B_PLAIN_YAML = """\
---
regulation_id: "PERMEN-TEST-1-2020"
title: "Test Regulation"
year: 2020
number: 1
---

# Test Regulation Content
"""

SAMPLE_PATTERN_C = """\
**Source File:** pp-5-2021.pdf
**Converted:** 2024-01-15

# Peraturan Pemerintah Nomor 5 Tahun 2021

Perizinan Berusaha Berbasis Risiko dilaksanakan melalui sistem OSS.
"""

SAMPLE_PATTERN_D = """\
# PMK 2023 Regulations Database
## Comprehensive Research

- PMK 2/2023 - Komite Pengawas Perpajakan
- PMK 168/2023 - Pemotongan Pajak Penghasilan
- PMK 172/2023 - Transfer Pricing
- UU 7/2021 - Harmonisasi Peraturan Perpajakan
"""

SAMPLE_README = """\
# Indonesian Legal Docs

## Structure
- hierarchy/ - Legal hierarchy
- permen/ - Ministry regulations
"""


# ── Format detection: all 6 patterns ─────────────────────────────────────────


def test_detect_format_pattern_a_structured(tmp_path: Path):
    """Structured legal text (Pattern A) is the default detection result."""
    fp = _write_file(tmp_path, "uu-27-2022.md", SAMPLE_PATTERN_A)
    parser = MarkdownParser()
    assert parser.detect_format(fp) == FormatPattern.STRUCTURED


def test_detect_format_pattern_b_yaml_frontmatter(tmp_path: Path):
    """Files starting with '---' are classified as YAML_FRONTMATTER (Pattern B)."""
    fp = _write_file(tmp_path, "permen-esdm-19-2010.md", SAMPLE_PATTERN_B)
    parser = MarkdownParser()
    assert parser.detect_format(fp) == FormatPattern.YAML_FRONTMATTER


def test_detect_format_pattern_c_source_file_marker(tmp_path: Path):
    """Files with '**Source File:**' in first 500 chars are OCR_CONVERTED (Pattern C)."""
    fp = _write_file(tmp_path, "pp-5-2021.md", SAMPLE_PATTERN_C)
    parser = MarkdownParser()
    assert parser.detect_format(fp) == FormatPattern.OCR_CONVERTED


def test_detect_format_pattern_c_converted_marker(tmp_path: Path):
    """Files with '**Converted:**' in first 500 chars are OCR_CONVERTED (Pattern C)."""
    fp = _write_file(tmp_path, "test-doc.md", "**Converted:** 2024-01-01\n\nSome text")
    parser = MarkdownParser()
    assert parser.detect_format(fp) == FormatPattern.OCR_CONVERTED


def test_detect_format_pattern_d_catalog(tmp_path: Path):
    """Files with 'database' in filename stem are CATALOG (Pattern D)."""
    fp = _write_file(tmp_path, "pmk_2023_database.md", SAMPLE_PATTERN_D)
    parser = MarkdownParser()
    assert parser.detect_format(fp) == FormatPattern.CATALOG


def test_detect_format_pattern_d_all_catalog_keywords(tmp_path: Path):
    """All 5 catalog keywords trigger CATALOG detection."""
    parser = MarkdownParser()
    for keyword in ["database", "catalog", "comprehensive-list", "regulations", "by-year"]:
        fp = _write_file(tmp_path, f"test-{keyword}.md", "# Catalog\n- Item 1")
        assert parser.detect_format(fp) == FormatPattern.CATALOG, f"Failed for: {keyword}"


def test_detect_format_pattern_e_binary(tmp_path: Path):
    """Binary content disguised as .md is classified as BINARY (Pattern E)."""
    fp = _write_binary_file(tmp_path, "corrupted.md", b"\x00\x01\x02\x03\x04\x05binary")
    parser = MarkdownParser()
    assert parser.detect_format(fp) == FormatPattern.BINARY


def test_detect_format_pattern_f_readme(tmp_path: Path):
    """README.md is classified as README (Pattern F) regardless of content."""
    fp = _write_file(tmp_path, "README.md", SAMPLE_README)
    parser = MarkdownParser()
    assert parser.detect_format(fp) == FormatPattern.README


def test_detect_format_readme_case_insensitive(tmp_path: Path):
    """readme.md (lowercase) is also classified as README."""
    fp = _write_file(tmp_path, "readme.md", "# Nav")
    parser = MarkdownParser()
    assert parser.detect_format(fp) == FormatPattern.README


# ── Binary detection helpers ─────────────────────────────────────────────────


def test_is_binary_string_with_text():
    """Normal UTF-8 text bytes are not detected as binary."""
    assert is_binary_string(b"Undang-Undang Nomor 27 Tahun 2022") is False


def test_is_binary_string_with_binary():
    """Bytes containing null and control characters are detected as binary."""
    assert is_binary_string(b"\x00\x01\x02\x03\x04\x05\x06") is True


def test_is_binary_string_empty():
    """Empty bytes are not detected as binary."""
    assert is_binary_string(b"") is False


def test_is_binary_file_with_text_file(tmp_path: Path):
    """A text file on disk is not detected as binary."""
    fp = _write_file(tmp_path, "normal.md", "Normal text content")
    assert is_binary_file(fp) is False


def test_is_binary_file_with_binary_file(tmp_path: Path):
    """A binary file on disk is detected as binary."""
    fp = _write_binary_file(tmp_path, "binary.md", b"\x00\x01\x02\x03\x04\x05")
    assert is_binary_file(fp) is True


def test_is_binary_file_nonexistent_returns_true(tmp_path: Path):
    """Non-existent file path returns True (safe default)."""
    fp = tmp_path / "does_not_exist.md"
    assert is_binary_file(fp) is True


# ── Content hashing — BLAKE2b ────────────────────────────────────────────────


def test_compute_content_hash_consistency():
    """Same input always produces the same BLAKE2b hex digest."""
    text = "Pasal 1: Data Pribadi adalah setiap data tentang seseorang."
    h1 = compute_content_hash(text)
    h2 = compute_content_hash(text)
    assert h1 == h2
    assert len(h1) == 64  # 32-byte digest -> 64 hex chars


def test_compute_content_hash_normalizes_whitespace():
    """Whitespace variations produce the same hash after normalization."""
    h1 = compute_content_hash("Hello   world\n\nfoo")
    h2 = compute_content_hash("Hello world\nfoo")
    assert h1 == h2


def test_compute_content_hash_different_input():
    """Different input text produces different hashes."""
    h1 = compute_content_hash("Undang-Undang Nomor 27")
    h2 = compute_content_hash("Peraturan Pemerintah Nomor 5")
    assert h1 != h2


def test_compute_content_hash_is_blake2b_hex():
    """Hash is a 64-char lowercase hex string (256-bit BLAKE2b)."""
    h = compute_content_hash("test")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_compute_content_hash_matches_manual_blake2b():
    """Hash matches manual BLAKE2b computation with whitespace normalization."""
    text = "Pasal  1   Data Pribadi"
    normalized = " ".join(text.split())
    expected = hashlib.blake2b(normalized.encode("utf-8"), digest_size=32).hexdigest()
    assert compute_content_hash(text) == expected


# ── Pattern A parsing ────────────────────────────────────────────────────────


def test_parse_pattern_a_basic_fields(tmp_path: Path):
    """Pattern A extracts jenis, nomor, tahun, title, and effective date."""
    fp = _write_file(tmp_path, "uu-27-2022.md", SAMPLE_PATTERN_A)
    parser = MarkdownParser()
    result = parser.parse(fp)

    assert isinstance(result, ParsedRegulation)
    assert result.format_pattern == FormatPattern.STRUCTURED
    assert result.jenis_dokumen == "UU"
    assert result.nomor == "27"
    assert result.tahun == "2022"
    assert result.regulation_id == "UU-27-2022"
    assert "Pelindungan Data Pribadi" in result.judul
    assert result.effective_date == "17 Oktober 2022"
    assert result.has_full_text is True


def test_parse_pattern_a_chapters(tmp_path: Path):
    """Pattern A extracts chapter names from '## BAB' headings."""
    fp = _write_file(tmp_path, "uu-27-2022.md", SAMPLE_PATTERN_A)
    result = MarkdownParser().parse(fp)

    assert len(result.chapters) == 2
    assert "KETENTUAN UMUM" in result.chapters[0]
    assert "RUANG LINGKUP" in result.chapters[1]


def test_parse_pattern_a_articles(tmp_path: Path):
    """Pattern A extracts article numbers from '### Pasal' headings."""
    fp = _write_file(tmp_path, "uu-27-2022.md", SAMPLE_PATTERN_A)
    result = MarkdownParser().parse(fp)

    assert result.articles == [1, 2, 3]


def test_parse_pattern_a_legal_basis(tmp_path: Path):
    """Pattern A extracts legal basis from MENGINGAT section."""
    fp = _write_file(tmp_path, "uu-27-2022.md", SAMPLE_PATTERN_A)
    result = MarkdownParser().parse(fp)

    assert len(result.legal_basis) >= 1


def test_parse_pattern_a_content_hash(tmp_path: Path):
    """Pattern A includes a non-empty 64-char content hash."""
    fp = _write_file(tmp_path, "uu-27-2022.md", SAMPLE_PATTERN_A)
    result = MarkdownParser().parse(fp)

    assert result.content_hash != ""
    assert len(result.content_hash) == 64


# ── Pattern B parsing ────────────────────────────────────────────────────────


def test_parse_pattern_b_yaml_code_fence(tmp_path: Path):
    """Pattern B extracts YAML from non-standard code fence within '---' delimiters."""
    fp = _write_file(tmp_path, "permen-esdm-19-2010.md", SAMPLE_PATTERN_B)
    result = MarkdownParser().parse(fp)

    assert result.format_pattern == FormatPattern.YAML_FRONTMATTER
    assert result.regulation_id == "PERMEN-ESDM-19-2010"
    assert result.jenis_dokumen == "Permen"
    assert result.nomor == "19"
    assert result.tahun == "2010"
    assert result.judul == "Tata Cara Penetapan Harga Minyak"
    assert result.ministry == "Kementerian ESDM"
    assert result.effective_date == "2010-06-15"


def test_parse_pattern_b_legal_basis_and_keywords(tmp_path: Path):
    """Pattern B extracts legal_basis and keywords lists from YAML."""
    fp = _write_file(tmp_path, "permen-esdm-19-2010.md", SAMPLE_PATTERN_B)
    result = MarkdownParser().parse(fp)

    assert result.legal_basis == ["UU-22-2001", "PP-35-2004"]
    assert result.keywords == ["minyak", "gas"]


def test_parse_pattern_b_yaml_metadata_preserved(tmp_path: Path):
    """Pattern B preserves the raw yaml_metadata dict."""
    fp = _write_file(tmp_path, "permen-esdm-19-2010.md", SAMPLE_PATTERN_B)
    result = MarkdownParser().parse(fp)

    assert result.yaml_metadata["category"] == "energy_mining"
    assert result.yaml_metadata["number"] == 19
    assert result.yaml_metadata["regulation_id"] == "PERMEN-ESDM-19-2010"


def test_parse_pattern_b_body_excludes_frontmatter(tmp_path: Path):
    """Pattern B body content does not include YAML frontmatter."""
    fp = _write_file(tmp_path, "permen-esdm-19-2010.md", SAMPLE_PATTERN_B)
    result = MarkdownParser().parse(fp)

    assert "regulation_id:" not in result.content
    assert "Peraturan Menteri" in result.content
    assert result.content_hash != ""


def test_parse_pattern_b_plain_yaml_fallback(tmp_path: Path):
    """Pattern B handles plain YAML (no code fence) via fallback parsing."""
    fp = _write_file(tmp_path, "permen-test-1-2020.md", SAMPLE_PATTERN_B_PLAIN_YAML)
    result = MarkdownParser().parse(fp)

    assert result.format_pattern == FormatPattern.YAML_FRONTMATTER
    assert result.regulation_id == "PERMEN-TEST-1-2020"
    assert result.judul == "Test Regulation"


def test_parse_pattern_b_corrupt_yaml(tmp_path: Path):
    """Pattern B with unparsable YAML falls back to filename metadata."""
    corrupt = "---\n```yaml\n[invalid: yaml: {{{{\n```\n---\n\nBody text here."
    fp = _write_file(tmp_path, "permen-esdm-19-2010.md", corrupt)
    result = MarkdownParser().parse(fp)

    assert result.format_pattern == FormatPattern.YAML_FRONTMATTER
    assert result.jenis_dokumen == "Permen"
    assert result.nomor == "19"
    assert result.tahun == "2010"
    assert result.yaml_metadata == {}


# ── Pattern C parsing ────────────────────────────────────────────────────────


def test_parse_pattern_c_ocr_quality_flag(tmp_path: Path):
    """Pattern C sets quality_flag='ocr' and extracts title."""
    fp = _write_file(tmp_path, "pp-5-2021.md", SAMPLE_PATTERN_C)
    result = MarkdownParser().parse(fp)

    assert result.format_pattern == FormatPattern.OCR_CONVERTED
    assert result.quality_flag == "ocr"
    assert result.jenis_dokumen == "PP"
    assert result.nomor == "5"
    assert result.tahun == "2021"
    assert result.judul == "Peraturan Pemerintah Nomor 5 Tahun 2021"
    assert result.content_hash != ""


def test_parse_pattern_c_ocr_cleanup(tmp_path: Path):
    """Pattern C collapses excessive blank lines in content."""
    fp = _write_file(tmp_path, "pp-5-2021.md", SAMPLE_PATTERN_C)
    result = MarkdownParser().parse(fp)

    assert "\n\n\n" not in result.content


# ── Pattern D parsing ────────────────────────────────────────────────────────


def test_parse_pattern_d_no_full_text(tmp_path: Path):
    """Pattern D sets has_full_text=False with empty content and hash."""
    fp = _write_file(tmp_path, "pmk_2023_database.md", SAMPLE_PATTERN_D)
    result = MarkdownParser().parse(fp)

    assert result.format_pattern == FormatPattern.CATALOG
    assert result.has_full_text is False
    assert result.content == ""
    assert result.content_hash == ""


def test_parse_pattern_d_extracts_references(tmp_path: Path):
    """Pattern D extracts regulation references from bullet lists."""
    fp = _write_file(tmp_path, "pmk_2023_database.md", SAMPLE_PATTERN_D)
    result = MarkdownParser().parse(fp)

    assert len(result.legal_basis) >= 3
    ref_texts = " ".join(result.legal_basis)
    assert "PMK" in ref_texts
    assert "UU" in ref_texts


def test_parse_pattern_d_title(tmp_path: Path):
    """Pattern D extracts title from the first # heading."""
    fp = _write_file(tmp_path, "pmk_2023_database.md", SAMPLE_PATTERN_D)
    result = MarkdownParser().parse(fp)

    assert result.judul == "PMK 2023 Regulations Database"


# ── Pattern E: binary stub ───────────────────────────────────────────────────


def test_parse_pattern_e_binary_stub(tmp_path: Path):
    """Binary file produces a minimal stub with quality_flag='binary'."""
    fp = _write_binary_file(tmp_path, "corrupted.md", b"\x00\x01\x02\xff\xfe" * 50)
    result = MarkdownParser().parse(fp)

    assert result.format_pattern == FormatPattern.BINARY
    assert result.has_full_text is False
    assert result.quality_flag == "binary"
    assert result.judul == ""


# ── Pattern F: README stub ───────────────────────────────────────────────────


def test_parse_pattern_f_readme_stub(tmp_path: Path):
    """README file produces a stub with regulation_id='README'."""
    fp = _write_file(tmp_path, "README.md", SAMPLE_README)
    result = MarkdownParser().parse(fp)

    assert result.format_pattern == FormatPattern.README
    assert result.regulation_id == "README"
    assert result.jenis_dokumen == "README"
    assert result.has_full_text is False


# ── Filename metadata extraction: all 5 regex patterns ───────────────────────


def test_filename_metadata_pattern1_uu():
    """Pattern 1: 'uu-27-2022.md' -> jenis=UU, nomor=27, tahun=2022."""
    meta = MarkdownParser.extract_filename_metadata(Path("uu-27-2022.md"))
    assert meta == {"jenis_dokumen": "UU", "nomor": "27", "tahun": "2022"}


def test_filename_metadata_pattern1_pp():
    """Pattern 1: 'pp-5-2021.md' -> jenis=PP, nomor=5, tahun=2021."""
    meta = MarkdownParser.extract_filename_metadata(Path("pp-5-2021.md"))
    assert meta == {"jenis_dokumen": "PP", "nomor": "5", "tahun": "2021"}


def test_filename_metadata_pattern1_perpres():
    """Pattern 1: 'perpres-9-2020.md' -> jenis=Perpres."""
    meta = MarkdownParser.extract_filename_metadata(Path("perpres-9-2020.md"))
    assert meta == {"jenis_dokumen": "Perpres", "nomor": "9", "tahun": "2020"}


def test_filename_metadata_pattern1_perppu():
    """Pattern 1: 'perppu-2-2022.md' -> jenis=Perppu."""
    meta = MarkdownParser.extract_filename_metadata(Path("perppu-2-2022.md"))
    assert meta == {"jenis_dokumen": "Perppu", "nomor": "2", "tahun": "2022"}


def test_filename_metadata_pattern2_permen_esdm():
    """Pattern 2: 'permen-esdm-19-2010.md' -> Permen with Kementerian ESDM."""
    meta = MarkdownParser.extract_filename_metadata(Path("permen-esdm-19-2010.md"))
    assert meta["jenis_dokumen"] == "Permen"
    assert meta["nomor"] == "19"
    assert meta["tahun"] == "2010"
    assert meta["ministry"] == "Kementerian ESDM"


def test_filename_metadata_pattern3_permenhub():
    """Pattern 3: 'permenhub-10-2023.md' -> Permen with Kementerian Perhubungan."""
    meta = MarkdownParser.extract_filename_metadata(Path("permenhub-10-2023.md"))
    assert meta["jenis_dokumen"] == "Permen"
    assert meta["nomor"] == "10"
    assert meta["tahun"] == "2023"
    assert meta["ministry"] == "Kementerian Perhubungan"


def test_filename_metadata_pattern4_pmk():
    """Pattern 4: 'pmk-5-2024.md' -> PMK with Kementerian Keuangan."""
    meta = MarkdownParser.extract_filename_metadata(Path("pmk-5-2024.md"))
    assert meta["jenis_dokumen"] == "PMK"
    assert meta["nomor"] == "5"
    assert meta["tahun"] == "2024"
    assert meta["ministry"] == "Kementerian Keuangan"


def test_filename_metadata_pattern5_perkomdigi():
    """Pattern 5: 'perkomdigi-3-2025.md' -> Permen with Kementerian Komunikasi dan Digital."""
    meta = MarkdownParser.extract_filename_metadata(Path("perkomdigi-3-2025.md"))
    assert meta["jenis_dokumen"] == "Permen"
    assert meta["nomor"] == "3"
    assert meta["tahun"] == "2025"
    assert meta["ministry"] == "Kementerian Komunikasi dan Digital"


def test_filename_metadata_pattern5_perkomdigi_with_slug():
    """Pattern 5 with trailing slug: 'perkomdigi-3-2025-tata-kelola.md'."""
    meta = MarkdownParser.extract_filename_metadata(Path("perkomdigi-3-2025-tata-kelola.md"))
    assert meta["jenis_dokumen"] == "Permen"
    assert meta["nomor"] == "3"
    assert meta["tahun"] == "2025"


def test_filename_metadata_no_match():
    """Unrecognized filename returns empty dict."""
    meta = MarkdownParser.extract_filename_metadata(Path("random-document.md"))
    assert meta == {}


# ── Edge cases ───────────────────────────────────────────────────────────────


def test_parse_empty_file(tmp_path: Path):
    """Empty .md file parses as Pattern A with empty fields."""
    fp = _write_file(tmp_path, "uu-1-2000.md", "")
    result = MarkdownParser().parse(fp)

    assert result.format_pattern == FormatPattern.STRUCTURED
    assert result.judul == ""
    assert result.chapters == []
    assert result.articles == []


def test_parse_whitespace_only_file(tmp_path: Path):
    """Whitespace-only file parses as Pattern A (default)."""
    fp = _write_file(tmp_path, "uu-2-2001.md", "   \n\n\t  \n")
    result = MarkdownParser().parse(fp)

    assert result.format_pattern == FormatPattern.STRUCTURED


def test_build_regulation_id():
    """build_regulation_id produces canonical 'JENIS-NOMOR-TAHUN' format."""
    assert MarkdownParser.build_regulation_id("UU", "27", "2022") == "UU-27-2022"
    assert MarkdownParser.build_regulation_id("PP", "5", "2021") == "PP-5-2021"
    assert MarkdownParser.build_regulation_id("PMK", "168", "2023") == "PMK-168-2023"


def test_format_pattern_enum_values():
    """FormatPattern enum has the expected 6 members with correct string values."""
    assert FormatPattern.STRUCTURED.value == "A"
    assert FormatPattern.YAML_FRONTMATTER.value == "B"
    assert FormatPattern.OCR_CONVERTED.value == "C"
    assert FormatPattern.CATALOG.value == "D"
    assert FormatPattern.BINARY.value == "E"
    assert FormatPattern.README.value == "F"
    assert len(FormatPattern) == 6


def test_format_pattern_is_str():
    """FormatPattern members are also strings (str, Enum)."""
    assert isinstance(FormatPattern.STRUCTURED, str)
    assert FormatPattern.STRUCTURED == "A"


def test_parsed_regulation_default_fields():
    """ParsedRegulation dataclass has correct defaults for optional fields."""
    reg = ParsedRegulation(
        filepath="test.md",
        format_pattern=FormatPattern.STRUCTURED,
        regulation_id="UU-1-2000",
        jenis_dokumen="UU",
        nomor="1",
        tahun="2000",
        judul="Test",
    )
    assert reg.ministry is None
    assert reg.effective_date is None
    assert reg.legal_basis == []
    assert reg.keywords == []
    assert reg.content == ""
    assert reg.chapters == []
    assert reg.articles == []
    assert reg.has_full_text is True
    assert reg.quality_flag is None
    assert reg.content_hash == ""
    assert reg.yaml_metadata == {}
    assert reg.source == "markdown_repo"
