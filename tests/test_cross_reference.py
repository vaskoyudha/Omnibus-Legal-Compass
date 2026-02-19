"""
Tests for cross-reference extraction from Indonesian legal documents.

Covers all 4 regex patterns, normalization, deduplication, and edge cases.
"""

from __future__ import annotations

from backend.cross_reference import (
    LegalReference,
    extract_legal_references,
    normalize_jenis,
)


# ── Pattern 1: Standard full-form citations ──────────────────────────────────


def test_standard_pattern_undang_undang():
    """Standard: 'Undang-Undang Nomor 27 Tahun 2022' → UU-27-2022."""
    text = "Undang-Undang Nomor 27 Tahun 2022 tentang Pelindungan Data Pribadi"
    refs = extract_legal_references(text)
    assert len(refs) == 1
    assert refs[0].canonical == "UU-27-2022"
    assert refs[0].jenis == "UU"
    assert refs[0].nomor == "27"
    assert refs[0].tahun == "2022"
    assert refs[0].relation is None


def test_standard_pattern_peraturan_pemerintah():
    """Standard: 'Peraturan Pemerintah Nomor 35 Tahun 2004' → PP-35-2004."""
    text = "Peraturan Pemerintah Nomor 35 Tahun 2004 tentang Kegiatan Usaha Hulu"
    refs = extract_legal_references(text)
    assert len(refs) == 1
    assert refs[0].canonical == "PP-35-2004"
    assert refs[0].jenis == "PP"


def test_standard_pattern_keputusan_presiden():
    """Standard: 'Keputusan Presiden Nomor 84 Tahun 2009'."""
    text = "Keputusan Presiden Nomor 84 Tahun 2009"
    refs = extract_legal_references(text)
    assert len(refs) == 1
    assert refs[0].canonical == "Keppres-84-2009"
    assert refs[0].jenis == "Keppres"


# ── Pattern 2: Abbreviated citations ─────────────────────────────────────────


def test_abbreviated_pattern_uu_slash():
    """Abbreviated: 'UU No. 27/2022' → UU-27-2022."""
    text = "berdasarkan UU No. 27/2022"
    refs = extract_legal_references(text)
    assert len(refs) == 1
    assert refs[0].canonical == "UU-27-2022"
    assert refs[0].jenis == "UU"
    assert refs[0].nomor == "27"


def test_abbreviated_pattern_pp_tahun():
    """Abbreviated: 'PP Nomor 55 Tahun 2009' → PP-55-2009."""
    text = "PP Nomor 55 Tahun 2009"
    refs = extract_legal_references(text)
    assert len(refs) == 1
    assert refs[0].canonical == "PP-55-2009"


def test_abbreviated_pattern_perppu():
    """Abbreviated: 'Perppu No 2/2022' → Perppu-2-2022."""
    text = "sesuai Perppu No 2/2022"
    refs = extract_legal_references(text)
    assert len(refs) == 1
    assert refs[0].canonical == "Perppu-2-2022"
    assert refs[0].jenis == "Perppu"


# ── Pattern 3: Cross-reference citations ─────────────────────────────────────


def test_cross_ref_dimaksud_dalam():
    """Cross-ref: 'sebagaimana dimaksud dalam UU No 11 Tahun 2008'."""
    text = "sebagaimana dimaksud dalam UU No 11 Tahun 2008 tentang ITE"
    refs = extract_legal_references(text)
    assert len(refs) == 1
    assert refs[0].canonical == "UU-11-2008"
    assert refs[0].relation == "dimaksud dalam"


def test_cross_ref_telah_diubah():
    """Cross-ref: 'sebagaimana telah diubah dengan Undang-Undang Nomor 19 Tahun 2016'."""
    text = (
        "sebagaimana telah diubah dengan Undang-Undang Nomor 19 Tahun 2016 "
        "tentang Perubahan atas UU ITE"
    )
    refs = extract_legal_references(text)
    canonicals = [r.canonical for r in refs]
    assert "UU-19-2016" in canonicals
    uu_ref = next(r for r in refs if r.canonical == "UU-19-2016")
    assert uu_ref.relation in ("telah diubah dengan", None)


def test_cross_ref_telah_dicabut():
    """Cross-ref: 'sebagaimana telah dicabut dengan PP Nomor 10 Tahun 2021'."""
    text = "sebagaimana telah dicabut dengan PP Nomor 10 Tahun 2021"
    refs = extract_legal_references(text)
    assert len(refs) == 1
    assert refs[0].canonical == "PP-10-2021"
    assert refs[0].relation == "telah dicabut dengan"


# ── Pattern 4: Amendment citations ───────────────────────────────────────────


def test_amendment_pattern_diubah():
    """Amendment: 'telah dua kali diubah terakhir dengan PP Nomor 55 Tahun 2009'."""
    text = "telah dua kali diubah terakhir dengan PP Nomor 55 Tahun 2009"
    refs = extract_legal_references(text)
    assert len(refs) == 1
    assert refs[0].canonical == "PP-55-2009"
    assert refs[0].relation == "diubah"


def test_amendment_pattern_dicabut():
    """Amendment: 'telah dicabut dengan UU Nomor 6 Tahun 2023'."""
    text = "telah dicabut dengan UU Nomor 6 Tahun 2023"
    refs = extract_legal_references(text)
    assert len(refs) == 1
    assert refs[0].canonical == "UU-6-2023"
    assert refs[0].relation == "dicabut"


# ── normalize_jenis ──────────────────────────────────────────────────────────


def test_normalize_jenis_full_name():
    """Full name → abbreviation."""
    assert normalize_jenis("Undang-Undang") == "UU"
    assert normalize_jenis("Peraturan Pemerintah") == "PP"
    assert normalize_jenis("Peraturan Presiden") == "Perpres"
    assert normalize_jenis("Peraturan Menteri") == "Permen"
    assert normalize_jenis("Keputusan Presiden") == "Keppres"


def test_normalize_jenis_abbreviation_passthrough():
    """Already abbreviated → canonical form."""
    assert normalize_jenis("UU") == "UU"
    assert normalize_jenis("PP") == "PP"
    assert normalize_jenis("Perpres") == "Perpres"
    assert normalize_jenis("PMK") == "PMK"
    assert normalize_jenis("Perppu") == "Perppu"


def test_normalize_jenis_mixed_case():
    """Mixed case → canonical form."""
    assert normalize_jenis("undang-undang") == "UU"
    assert normalize_jenis("PERATURAN PEMERINTAH") == "PP"
    assert normalize_jenis("pp") == "PP"
    assert normalize_jenis("uu") == "UU"
    assert normalize_jenis("perpres") == "Perpres"


def test_normalize_jenis_extra_whitespace():
    """Extra whitespace is cleaned before lookup."""
    assert normalize_jenis("  Undang-Undang  ") == "UU"
    assert normalize_jenis("  peraturan   pemerintah  ") == "PP"
    assert normalize_jenis("  UU  ") == "UU"


# ── Multiple references ──────────────────────────────────────────────────────


def test_multiple_refs_in_same_text():
    """Multiple distinct legal references extracted from one text block."""
    text = (
        "Undang-Undang Nomor 22 Tahun 2001 tentang Minyak dan Gas Bumi "
        "serta Peraturan Pemerintah Nomor 35 Tahun 2004 tentang Kegiatan Usaha"
    )
    refs = extract_legal_references(text)
    canonicals = sorted(r.canonical for r in refs)
    assert "PP-35-2004" in canonicals
    assert "UU-22-2001" in canonicals


def test_real_permen_mengingat_section():
    """Text from permen-esdm-19-2010 MENGINGAT section with multiple refs."""
    text = (
        "UNDANG-UNDANG NOMOR 22 TAHUN 2001 TENTANG MINYAK DAN GAS "
        "Peraturan Pemerintah Nomor 35 Tahun 2004 tentang Kegiatan "
        "Usaha Hulu Minyak dan Gas Bumi sebagaimana telah dua kali "
        "diubah terakhir dengan Peraturan Pemerintah Nomor 55 Tahun 2009"
    )
    refs = extract_legal_references(text)
    canonicals = [r.canonical for r in refs]
    assert "UU-22-2001" in canonicals
    assert "PP-35-2004" in canonicals
    assert "PP-55-2009" in canonicals


# ── Deduplication ────────────────────────────────────────────────────────────


def test_deduplication_same_ref_different_forms():
    """Same regulation cited in both standard and abbreviated form → one entry."""
    text = (
        "Undang-Undang Nomor 27 Tahun 2022 tentang PDP. "
        "Berdasarkan UU No. 27/2022 tersebut."
    )
    refs = extract_legal_references(text)
    canonicals = [r.canonical for r in refs]
    assert canonicals.count("UU-27-2022") == 1


# ── Edge cases ───────────────────────────────────────────────────────────────


def test_empty_text_returns_empty():
    """Empty string returns no references."""
    assert extract_legal_references("") == []


def test_whitespace_only_returns_empty():
    """Whitespace-only string returns no references."""
    assert extract_legal_references("   \n\t  ") == []


def test_no_legal_refs_returns_empty():
    """Text without legal citations returns empty list."""
    text = "Ini adalah teks biasa tanpa referensi hukum apapun."
    assert extract_legal_references(text) == []


def test_results_sorted_by_canonical():
    """Returned references are sorted by canonical form."""
    text = (
        "PP Nomor 55 Tahun 2009 dan Undang-Undang Nomor 22 Tahun 2001 "
        "serta Peraturan Presiden Nomor 9 Tahun 2020"
    )
    refs = extract_legal_references(text)
    canonicals = [r.canonical for r in refs]
    assert canonicals == sorted(canonicals)


def test_legal_reference_dataclass_fields():
    """LegalReference has all expected fields."""
    ref = LegalReference(
        raw_text="UU No. 27/2022",
        jenis="UU",
        nomor="27",
        tahun="2022",
        relation=None,
        canonical="UU-27-2022",
    )
    assert ref.raw_text == "UU No. 27/2022"
    assert ref.jenis == "UU"
    assert ref.nomor == "27"
    assert ref.tahun == "2022"
    assert ref.relation is None
    assert ref.canonical == "UU-27-2022"
