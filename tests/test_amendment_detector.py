"""
Tests for amendment/revocation detection in Indonesian legal regulations.

Covers all amendment types (amends, revokes, replaces, supplements),
title-based detection, confidence scoring, and edge cases.
"""

from __future__ import annotations

from backend.amendment_detector import (
    AmendmentDetector,
    AmendmentRelation,
    AmendmentType,
)


# ── Pattern: mengubah / perubahan atas (AMENDS) ─────────────────────────────


def test_detect_mengubah_as_amends():
    """Body text 'mengubah UU Nomor 11 Tahun 2008' → AmendmentType.AMENDS."""
    detector = AmendmentDetector()
    text = "Pasal ini mengubah UU Nomor 11 Tahun 2008 tentang ITE"
    results = detector.detect_amendments(text, "UU-19-2016")
    assert len(results) == 1
    assert results[0].amendment_type == AmendmentType.AMENDS
    assert results[0].target_regulation == "UU-11-2008"
    assert results[0].source_regulation == "UU-19-2016"


def test_detect_perubahan_atas_as_amends():
    """Body text 'perubahan atas PP Nomor 35 Tahun 2004' → AMENDS."""
    detector = AmendmentDetector()
    text = "merupakan perubahan atas PP Nomor 35 Tahun 2004 tentang Kegiatan Usaha"
    results = detector.detect_amendments(text, "PP-55-2009")
    assert len(results) == 1
    assert results[0].amendment_type == AmendmentType.AMENDS
    assert results[0].target_regulation == "PP-35-2004"
    assert results[0].source_regulation == "PP-55-2009"


# ── Pattern: mencabut (REVOKES) ─────────────────────────────────────────────


def test_detect_mencabut_as_revokes():
    """Body text 'mencabut Perpres Nomor 9 Tahun 2020' → REVOKES."""
    detector = AmendmentDetector()
    text = "Ketentuan ini mencabut Perpres Nomor 9 Tahun 2020"
    results = detector.detect_amendments(text, "Perpres-10-2021")
    assert len(results) == 1
    assert results[0].amendment_type == AmendmentType.REVOKES
    assert results[0].target_regulation == "Perpres-9-2020"
    assert results[0].source_regulation == "Perpres-10-2021"


# ── Pattern: mengganti (REPLACES) ───────────────────────────────────────────


def test_detect_mengganti_as_replaces():
    """Body text 'mengganti Permen Nomor 5 Tahun 2018' → REPLACES."""
    detector = AmendmentDetector()
    text = "Peraturan ini mengganti Permen Nomor 5 Tahun 2018"
    results = detector.detect_amendments(text, "Permen-10-2022")
    assert len(results) == 1
    assert results[0].amendment_type == AmendmentType.REPLACES
    assert results[0].target_regulation == "Permen-5-2018"
    assert results[0].source_regulation == "Permen-10-2022"


# ── Title-based detection ────────────────────────────────────────────────────


def test_detect_from_title_perubahan():
    """Title 'Perubahan atas UU Nomor 11 Tahun 2008' → AMENDS with 0.8 confidence."""
    detector = AmendmentDetector()
    title = "Perubahan atas UU Nomor 11 Tahun 2008 tentang ITE"
    results = detector.detect_from_title(title, "UU-19-2016")
    assert len(results) == 1
    assert results[0].amendment_type == AmendmentType.AMENDS
    assert results[0].target_regulation == "UU-11-2008"
    assert results[0].confidence == 0.8


# ── Confidence scoring ───────────────────────────────────────────────────────


def test_confidence_score_body_text():
    """Body text matches get confidence 1.0."""
    detector = AmendmentDetector()
    text = "mengubah UU Nomor 11 Tahun 2008"
    results = detector.detect_amendments(text, "UU-19-2016")
    assert len(results) == 1
    assert results[0].confidence == 1.0


# ── Edge cases ───────────────────────────────────────────────────────────────


def test_no_amendments_returns_empty():
    """Text without amendment language returns empty list."""
    detector = AmendmentDetector()
    text = "Pasal 1 mengatur tentang ketentuan umum dalam peraturan ini."
    results = detector.detect_amendments(text, "UU-11-2020")
    assert results == []


def test_multiple_amendments_in_text():
    """Text with multiple amendment types returns multiple results."""
    detector = AmendmentDetector()
    text = (
        "Peraturan ini mengubah UU Nomor 11 Tahun 2008 tentang ITE "
        "dan mencabut PP Nomor 35 Tahun 2004 tentang Kegiatan Usaha Hulu."
    )
    results = detector.detect_amendments(text, "UU-19-2016")
    assert len(results) == 2
    types = {r.amendment_type for r in results}
    assert AmendmentType.AMENDS in types
    assert AmendmentType.REVOKES in types
    targets = {r.target_regulation for r in results}
    assert "UU-11-2008" in targets
    assert "PP-35-2004" in targets


# ── Additional coverage ─────────────────────────────────────────────────────


def test_empty_text_returns_empty():
    """Empty string returns no amendments."""
    detector = AmendmentDetector()
    assert detector.detect_amendments("", "UU-1-2020") == []
    assert detector.detect_from_title("", "UU-1-2020") == []


def test_amendment_relation_dataclass_fields():
    """AmendmentRelation has all expected fields."""
    rel = AmendmentRelation(
        source_regulation="UU-19-2016",
        target_regulation="UU-11-2008",
        amendment_type=AmendmentType.AMENDS,
        raw_text="mengubah UU Nomor 11 Tahun 2008",
        confidence=1.0,
    )
    assert rel.source_regulation == "UU-19-2016"
    assert rel.target_regulation == "UU-11-2008"
    assert rel.amendment_type == AmendmentType.AMENDS
    assert rel.raw_text == "mengubah UU Nomor 11 Tahun 2008"
    assert rel.confidence == 1.0


def test_amendment_type_enum_values():
    """AmendmentType enum has correct string values."""
    assert AmendmentType.AMENDS.value == "amends"
    assert AmendmentType.REVOKES.value == "revokes"
    assert AmendmentType.REPLACES.value == "replaces"
    assert AmendmentType.SUPPLEMENTS.value == "supplements"
