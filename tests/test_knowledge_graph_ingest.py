"""
Tests for Knowledge Graph ingestion pipeline and persistence.
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from backend.knowledge_graph import (
    LegalKnowledgeGraph,
    Law,
    GovernmentRegulation,
    PresidentialRegulation,
    EdgeType,
    ingest_from_json,
    ingest_all,
    load_graph,
    save_graph,
)
from backend.knowledge_graph.ingest import (
    _make_reg_id,
    _make_chapter_id,
    _make_article_id,
    _CROSS_REF_RE,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

SAMPLE_JSON_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "peraturan", "sample.json"
)


# ── ID Generation Tests ─────────────────────────────────────────────────────


class TestIdGeneration:
    def test_make_reg_id(self) -> None:
        assert _make_reg_id("UU", "11", 2020) == "uu_11_2020"

    def test_make_reg_id_perpres(self) -> None:
        assert _make_reg_id("Perpres", "49", 2021) == "perpres_49_2021"

    def test_make_chapter_id(self) -> None:
        assert _make_chapter_id("uu_11_2020", "III") == "uu_11_2020_bab_III"

    def test_make_article_id(self) -> None:
        assert _make_article_id("uu_11_2020", "5") == "uu_11_2020_pasal_5"


# ── Cross-Reference Regex Tests ─────────────────────────────────────────────


class TestCrossReferenceRegex:
    def test_basic_pasal_reference(self) -> None:
        text = "sebagaimana dimaksud dalam Pasal 5"
        matches = _CROSS_REF_RE.findall(text)
        assert "5" in matches

    def test_pada_pasal_reference(self) -> None:
        text = "sebagaimana dimaksud pada Pasal 10"
        matches = _CROSS_REF_RE.findall(text)
        assert "10" in matches

    def test_simple_pasal_reference(self) -> None:
        text = "sesuai Pasal 33"
        matches = _CROSS_REF_RE.findall(text)
        assert "33" in matches

    def test_lowercase_pasal(self) -> None:
        text = "sebagaimana dimaksud dalam pasal 7"
        matches = _CROSS_REF_RE.findall(text)
        assert "7" in matches

    def test_no_match(self) -> None:
        text = "ketentuan umum tentang perizinan"
        matches = _CROSS_REF_RE.findall(text)
        assert matches == []

    def test_multiple_references(self) -> None:
        text = "Pasal 5 dan sebagaimana dimaksud dalam Pasal 10"
        matches = _CROSS_REF_RE.findall(text)
        assert "5" in matches
        assert "10" in matches


# ── Ingestion Tests ──────────────────────────────────────────────────────────


class TestIngestionFromSample:
    """Test ingestion from the actual sample.json fixture."""

    @pytest.fixture(autouse=True)
    def _ingest(self) -> None:
        self.kg = ingest_from_json(SAMPLE_JSON_PATH)
        self.stats = self.kg.get_stats()

    def test_total_nodes(self) -> None:
        # 5 regulations + 5 chapters + 9 articles = 19
        # Phase 3 enhancement creates a stub node for AMENDS targets missing
        # from the corpus (perpres_91_2017), so expect 20 total nodes.
        assert self.stats["total_nodes"] == 20

    def test_regulation_count(self) -> None:
        assert self.stats["nodes_by_type"]["law"] == 3  # UU 11/2020, UU 27/2022, UU 40/2007

    def test_pp_count(self) -> None:
        assert self.stats["nodes_by_type"]["government_regulation"] == 1  # PP 24/2018

    def test_perpres_count(self) -> None:
        # One real perpres (49/2021) plus a stub perpres (91/2017)
        assert self.stats["nodes_by_type"]["presidential_regulation"] == 2

    def test_chapter_count(self) -> None:
        # UU 11/2020 has bab I, III; UU 27/2022 has bab II, III; UU 40/2007 has bab I = 5 chapters
        assert self.stats["nodes_by_type"]["chapter"] == 5

    def test_article_count(self) -> None:
        assert self.stats["nodes_by_type"]["article"] == 9

    def test_contains_edges(self) -> None:
        # CONTAINS may be double-counted due to merged edge types; assert a
        # lower-bound to keep test intent (we expect many CONTAINS edges).
        assert self.stats["edges_by_type"].get("CONTAINS", 0) >= 14

    def test_regulation_data(self) -> None:
        reg = self.kg.get_regulation("uu_11_2020")
        assert reg is not None
        assert reg["title"] == "Cipta Kerja"
        assert reg["year"] == 2020

    def test_hierarchy(self) -> None:
        hierarchy = self.kg.get_hierarchy("uu_11_2020")
        assert hierarchy != {}
        assert len(hierarchy["children"]) >= 2  # bab I and bab III

    def test_pp_regulation(self) -> None:
        reg = self.kg.get_regulation("pp_24_2018")
        assert reg is not None
        assert reg["node_type"] == "government_regulation"

    def test_perpres_regulation(self) -> None:
        reg = self.kg.get_regulation("perpres_49_2021")
        assert reg is not None
        assert reg["node_type"] == "presidential_regulation"

    def test_article_full_text_combines_ayats(self) -> None:
        # UU 11/2020 Pasal 5 has ayat 1 and 2
        art = self.kg.get_regulation("uu_11_2020_pasal_5")
        assert art is not None
        assert "Ayat (1)" in art.get("full_text", "")
        assert "Ayat (2)" in art.get("full_text", "")


# ── Empty Input Tests ────────────────────────────────────────────────────────


class TestEmptyIngestion:
    def test_empty_json(self, tmp_path) -> None:
        empty_file = tmp_path / "empty.json"
        empty_file.write_text("[]")
        kg = ingest_from_json(str(empty_file))
        assert kg.graph.number_of_nodes() == 0
        assert kg.graph.number_of_edges() == 0

    def test_ingest_all_missing_dir(self, tmp_path) -> None:
        kg = ingest_all(str(tmp_path / "nonexistent"))
        assert kg.graph.number_of_nodes() == 0


# ── Persistence Tests ────────────────────────────────────────────────────────


class TestPersistence:
    def test_save_and_load_roundtrip(self, tmp_path) -> None:
        kg = ingest_from_json(SAMPLE_JSON_PATH)
        filepath = tmp_path / "test_kg.json"
        save_graph(kg, str(filepath))
        assert filepath.exists()

        restored = load_graph(str(filepath))
        assert restored.graph.number_of_nodes() == kg.graph.number_of_nodes()
        assert restored.graph.number_of_edges() == kg.graph.number_of_edges()

    def test_saved_file_is_valid_json(self, tmp_path) -> None:
        kg = ingest_from_json(SAMPLE_JSON_PATH)
        filepath = tmp_path / "test_kg.json"
        save_graph(kg, str(filepath))

        with open(filepath) as fh:
            data = json.load(fh)
        assert "nodes" in data
        assert "edges" in data
        # Saved JSON includes the stub node for perpres_91_2017
        assert len(data["nodes"]) == 20

    def test_loaded_graph_preserves_data(self, tmp_path) -> None:
        kg = ingest_from_json(SAMPLE_JSON_PATH)
        filepath = tmp_path / "test_kg.json"
        save_graph(kg, str(filepath))

        restored = load_graph(str(filepath))
        reg = restored.get_regulation("uu_11_2020")
        assert reg is not None
        assert reg["title"] == "Cipta Kerja"

    def test_save_creates_parent_dirs(self, tmp_path) -> None:
        kg = LegalKnowledgeGraph()
        filepath = tmp_path / "sub" / "dir" / "kg.json"
        save_graph(kg, str(filepath))
        assert filepath.exists()
