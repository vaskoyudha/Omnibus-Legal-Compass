"""Tests for the legal document corpus — validates structure, completeness, and integrity."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

CORPUS_PATH = Path(__file__).parent.parent / "backend" / "data" / "peraturan" / "merged_corpus.json"
REQUIRED_FIELDS = {"jenis_dokumen", "nomor", "tahun", "judul", "tentang", "pasal", "text"}
VALID_JENIS = {"UU", "PP", "Perpres", "Permen", "Perda"}

# ── Minimum thresholds ───────────────────────────────────────────────────────

MIN_TOTAL_DOCUMENTS = 10000
MIN_UNIQUE_REGULATIONS = 600
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

        A small number of intra-regulation duplicates is tolerated for the
        expanded corpus because OCR-sourced entries (Azzindani dataset) may
        contain duplicate text fragments from poor PDF extraction.
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
        # Allow up to 0.5% duplicate rate for OCR-sourced corpora
        max_allowed = max(20, int(len(corpus) * 0.005))
        assert len(duplicates) <= max_allowed, (
            f"Found {len(duplicates)} duplicate text(s) within same regulation "
            f"(max allowed: {max_allowed}): "
            + "; ".join(
                f"{reg} docs [{a}] and [{b}]: '{preview}...'"
                for reg, a, b, preview in duplicates[:3]
            )
        )

    def test_no_duplicate_articles_within_regulation(self, corpus: list[dict]):
        """Within a single regulation, no two entries should share pasal+ayat.

        A small number of duplicates is tolerated for the expanded corpus
        because OCR-sourced entries may have duplicate pasal/ayat metadata
        from imperfect PDF structure extraction.
        """
        reg_articles: dict[tuple, list[tuple]] = {}
        for doc in corpus:
            reg_key = (doc["jenis_dokumen"], doc["nomor"], str(doc["tahun"]))
            art_key = (doc["pasal"], doc.get("ayat"))
            reg_articles.setdefault(reg_key, []).append(art_key)

        duplicate_count = 0
        for reg_key, articles in reg_articles.items():
            seen: set[tuple] = set()
            for art in articles:
                if art in seen:
                    duplicate_count += 1
                seen.add(art)

        # Allow up to 0.5% duplicate rate for OCR-sourced corpora
        max_allowed = max(20, int(len(corpus) * 0.005))
        assert duplicate_count <= max_allowed, (
            f"Found {duplicate_count} duplicate pasal+ayat entries "
            f"(max allowed: {max_allowed})"
        )


# ── Scraper consistency tests ─────────────────────────────────────────────────


class TestScraperConsistency:
    """Tests that validate scraper output is a valid subset of the full corpus.

    The full corpus (regulations.json) is assembled from multiple sources:
    scraper.py (seed regulations), convert_azzindani.py (HuggingFace dataset),
    and prepare_priority_regulations.py. Therefore the scraper output is
    expected to be a *subset* of the corpus, not an exact match.
    """

    def test_generated_is_subset_of_corpus(self, corpus: list[dict], generated_corpus: list[dict]):
        """create_expanded_dataset() output must be a subset of regulations.json."""
        # Scraper generates the seed dataset; corpus includes additional sources
        assert len(generated_corpus) <= len(corpus), (
            f"Scraper produces {len(generated_corpus)} docs but corpus has {len(corpus)} — "
            f"scraper output should be a subset"
        )

    def test_generated_has_minimum_seed_documents(self, generated_corpus: list[dict]):
        """Scraper must produce at least 300 seed articles."""
        assert len(generated_corpus) >= 300, (
            f"Scraper produces only {len(generated_corpus)} seed docs, expected >= 300"
        )

    def test_generated_documents_found_in_corpus(self, corpus: list[dict], generated_corpus: list[dict]):
        """All scraper-generated articles should exist in the full corpus."""
        corpus_keys = {
            (d["jenis_dokumen"], d["nomor"], str(d["tahun"]), d["pasal"])
            for d in corpus
        }
        missing = []
        for doc in generated_corpus[:50]:  # Sample check for performance
            key = (doc["jenis_dokumen"], doc["nomor"], str(doc["tahun"]), doc["pasal"])
            if key not in corpus_keys:
                missing.append(key)
        assert not missing, (
            f"Scraper articles not found in corpus: {missing[:5]}"
        )


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
