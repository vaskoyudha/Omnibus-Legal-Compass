"""Tests for the legal document corpus — validates structure, completeness, and integrity."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

CORPUS_PATH = Path(__file__).parent.parent / "backend" / "data" / "peraturan" / "regulations.json"
REQUIRED_FIELDS = {"jenis_dokumen", "nomor", "tahun", "judul", "tentang", "pasal", "text"}
VALID_JENIS = {"UU", "PP", "Perpres", "Permen", "Perda"}

# ── Minimum thresholds ───────────────────────────────────────────────────────

MIN_TOTAL_DOCUMENTS = 390
MIN_UNIQUE_REGULATIONS = 40
MIN_TEXT_LENGTH = 30


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def corpus() -> list[dict]:
    """Load the regulations corpus from JSON."""
    assert CORPUS_PATH.exists(), f"Corpus file not found: {CORPUS_PATH}"
    with open(CORPUS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, list), "Corpus must be a JSON array"
    return data


@pytest.fixture(scope="module")
def generated_corpus() -> list[dict]:
    """Generate corpus from scraper.py create_expanded_dataset()."""
    from scripts.scraper import create_expanded_dataset

    return create_expanded_dataset()


# ── Corpus file tests ────────────────────────────────────────────────────────


class TestCorpusFile:
    """Tests that validate the regulations.json file."""

    def test_corpus_file_exists(self):
        """Corpus JSON file must exist."""
        assert CORPUS_PATH.exists()

    def test_corpus_is_valid_json(self):
        """Corpus must be valid JSON."""
        with open(CORPUS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, list)

    def test_total_document_count(self, corpus: list[dict]):
        """Corpus must contain at least MIN_TOTAL_DOCUMENTS articles."""
        assert len(corpus) >= MIN_TOTAL_DOCUMENTS, (
            f"Expected >= {MIN_TOTAL_DOCUMENTS} documents, got {len(corpus)}"
        )

    def test_unique_regulation_count(self, corpus: list[dict]):
        """Corpus must cover at least MIN_UNIQUE_REGULATIONS distinct regulations."""
        regs = {
            (d["jenis_dokumen"], d["nomor"], str(d["tahun"]))
            for d in corpus
        }
        assert len(regs) >= MIN_UNIQUE_REGULATIONS, (
            f"Expected >= {MIN_UNIQUE_REGULATIONS} regulations, got {len(regs)}"
        )


# ── Document structure tests ─────────────────────────────────────────────────


class TestDocumentStructure:
    """Tests that validate individual document fields."""

    def test_all_required_fields_present(self, corpus: list[dict]):
        """Every document must have all required fields."""
        for i, doc in enumerate(corpus):
            missing = REQUIRED_FIELDS - set(doc.keys())
            assert not missing, (
                f"Document {i} missing fields: {missing}. "
                f"Doc: {doc.get('jenis_dokumen')} {doc.get('nomor')}/{doc.get('tahun')} Pasal {doc.get('pasal')}"
            )

    def test_jenis_dokumen_valid(self, corpus: list[dict]):
        """Every jenis_dokumen must be a known type."""
        for i, doc in enumerate(corpus):
            assert doc["jenis_dokumen"] in VALID_JENIS, (
                f"Document {i} has invalid jenis_dokumen: '{doc['jenis_dokumen']}'. "
                f"Valid types: {VALID_JENIS}"
            )

    def test_text_not_empty(self, corpus: list[dict]):
        """Every article must have non-empty text."""
        for i, doc in enumerate(corpus):
            text = doc.get("text", "")
            assert isinstance(text, str) and len(text.strip()) >= MIN_TEXT_LENGTH, (
                f"Document {i} has text shorter than {MIN_TEXT_LENGTH} chars. "
                f"Doc: {doc.get('jenis_dokumen')} {doc.get('nomor')}/{doc.get('tahun')} Pasal {doc.get('pasal')}"
            )

    def test_tahun_is_integer(self, corpus: list[dict]):
        """Every tahun must be an integer."""
        for i, doc in enumerate(corpus):
            assert isinstance(doc["tahun"], int), (
                f"Document {i} tahun is not int: {type(doc['tahun'])} = {doc['tahun']}"
            )

    def test_pasal_is_string(self, corpus: list[dict]):
        """Every pasal must be a string."""
        for i, doc in enumerate(corpus):
            assert isinstance(doc["pasal"], str), (
                f"Document {i} pasal is not string: {type(doc['pasal'])} = {doc['pasal']}"
            )

    def test_nomor_is_string(self, corpus: list[dict]):
        """Every nomor must be a string."""
        for i, doc in enumerate(corpus):
            assert isinstance(doc["nomor"], str), (
                f"Document {i} nomor is not string: {type(doc['nomor'])} = {doc['nomor']}"
            )


# ── Content integrity tests ──────────────────────────────────────────────────


class TestContentIntegrity:
    """Tests that validate content quality and uniqueness."""

    def test_no_exact_text_duplicates_within_regulation(self, corpus: list[dict]):
        """No two documents within the SAME regulation should have the exact same text.

        Cross-regulation duplicates are allowed because Indonesia's omnibus law
        (UU 11/2020 Cipta Kerja) intentionally restates articles from other laws.
        """
        reg_texts: dict[tuple, dict[str, int]] = {}
        duplicates = []
        for i, doc in enumerate(corpus):
            reg_key = (doc["jenis_dokumen"], doc["nomor"], str(doc["tahun"]))
            seen = reg_texts.setdefault(reg_key, {})
            text = doc["text"]
            if text in seen:
                duplicates.append((reg_key, seen[text], i, text[:80]))
            else:
                seen[text] = i
        assert not duplicates, (
            f"Found {len(duplicates)} duplicate text(s) within same regulation: "
            + "; ".join(
                f"{reg} docs [{a}] and [{b}]: '{preview}...'"
                for reg, a, b, preview in duplicates[:3]
            )
        )

    def test_no_duplicate_articles_within_regulation(self, corpus: list[dict]):
        """Within a single regulation, no two entries should share pasal+ayat."""
        reg_articles: dict[tuple, list[tuple]] = {}
        for doc in corpus:
            reg_key = (doc["jenis_dokumen"], doc["nomor"], str(doc["tahun"]))
            art_key = (doc["pasal"], doc.get("ayat"))
            reg_articles.setdefault(reg_key, []).append(art_key)

        for reg_key, articles in reg_articles.items():
            seen: set[tuple] = set()
            for art in articles:
                assert art not in seen, (
                    f"Duplicate article {art} in regulation {reg_key}"
                )
                seen.add(art)


# ── Scraper consistency tests ─────────────────────────────────────────────────


class TestScraperConsistency:
    """Tests that validate scraper output matches the JSON file."""

    def test_generated_matches_file(self, corpus: list[dict], generated_corpus: list[dict]):
        """create_expanded_dataset() output must match regulations.json."""
        assert len(generated_corpus) == len(corpus), (
            f"Scraper produces {len(generated_corpus)} docs but JSON has {len(corpus)}"
        )

    def test_generated_document_count(self, generated_corpus: list[dict]):
        """Scraper must produce at least MIN_TOTAL_DOCUMENTS articles."""
        assert len(generated_corpus) >= MIN_TOTAL_DOCUMENTS


# ── Domain coverage tests ────────────────────────────────────────────────────


class TestDomainCoverage:
    """Tests that the corpus covers key legal domains."""

    EXPECTED_DOMAINS = [
        ("UU", "11", "2020"),   # Cipta Kerja
        ("UU", "27", "2022"),   # PDP
        ("UU", "40", "2007"),   # Perseroan Terbatas
        ("UU", "13", "2003"),   # Ketenagakerjaan
        ("UU", "31", "1999"),   # Anti-Korupsi
        ("UU", "5", "1999"),    # Anti-Monopoli
        ("UU", "10", "1998"),   # Perbankan
        ("UU", "8", "1995"),    # Pasar Modal
        ("UU", "28", "2014"),   # Hak Cipta
        ("UU", "13", "2016"),   # Paten
        ("UU", "20", "2016"),   # Merek
        ("UU", "37", "2004"),   # Kepailitan
        # Batch 1
        ("UU", "42", "1999"),   # Jaminan Fidusia
        ("UU", "4", "1996"),    # Hak Tanggungan
        ("UU", "30", "1999"),   # Arbitrase
        ("UU", "2", "2004"),    # PPHI
        ("UU", "6", "2011"),    # Keimigrasian
        # Batch 2
        ("UU", "16", "2001"),   # Yayasan
        ("UU", "25", "1992"),   # Koperasi
        ("UU", "21", "2011"),   # OJK
        ("UU", "40", "2014"),   # Perasuransian
        ("UU", "7", "2014"),    # Perdagangan
        ("UU", "3", "2014"),    # Perindustrian
        # Batch 3
        ("UU", "2", "2017"),    # Jasa Konstruksi
        ("UU", "31", "2000"),   # Desain Industri
        ("UU", "30", "2000"),   # Rahasia Dagang
        ("UU", "17", "2006"),   # Kepabeanan
        ("UU", "39", "2007"),   # Cukai
    ]

    def test_all_key_regulations_present(self, corpus: list[dict]):
        """Corpus must include all key regulations."""
        present = {
            (d["jenis_dokumen"], d["nomor"], str(d["tahun"]))
            for d in corpus
        }
        for reg in self.EXPECTED_DOMAINS:
            assert reg in present, (
                f"Missing regulation: {reg[0]} {reg[1]}/{reg[2]}"
            )
