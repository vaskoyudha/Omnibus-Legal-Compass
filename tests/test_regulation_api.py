"""
Tests for Regulation Library API endpoints.

Covers:
- GET /api/v1/regulations — paginated regulation list with filters
- GET /api/v1/regulations/{id} — single regulation detail with hierarchy
- GET /api/v1/regulations/{id}/timeline — amendment timeline
- GET /api/v1/regulations/{id}/articles/{aid}/references — cross-references
- KG unavailable (503) scenarios
- Pagination, sorting, and search
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from knowledge_graph.graph import LegalKnowledgeGraph
from knowledge_graph.schema import (
    Article,
    Chapter,
    EdgeType,
    GovernmentRegulation,
    Law,
    PresidentialRegulation,
)


# ---------------------------------------------------------------------------
# Fixture: build a small knowledge graph for testing
# ---------------------------------------------------------------------------


@pytest.fixture
def regulation_kg() -> LegalKnowledgeGraph:
    """Build a knowledge graph with known data for Regulation Library testing."""
    kg = LegalKnowledgeGraph()

    # Add Law 1: UU 11/2020 Cipta Kerja (active)
    law1 = Law(
        id="uu_11_2020",
        number=11,
        year=2020,
        title="UU No. 11 Tahun 2020",
        about="Cipta Kerja",
        status="active",
    )
    kg.add_regulation(law1)

    # Chapter under law1
    chapter1 = Chapter(
        id="uu_11_2020_bab_1",
        title="Bab I Ketentuan Umum",
        number="I",
        parent_regulation_id="uu_11_2020",
    )
    kg.add_chapter(chapter1)

    # Article under chapter1
    article1 = Article(
        id="uu_11_2020_pasal_1",
        number="1",
        parent_regulation_id="uu_11_2020",
        parent_chapter_id="uu_11_2020_bab_1",
        full_text="Dalam Undang-Undang ini yang dimaksud dengan...",
    )
    kg.add_article(article1)

    # Article 2 under chapter1
    article2 = Article(
        id="uu_11_2020_pasal_2",
        number="2",
        parent_regulation_id="uu_11_2020",
        parent_chapter_id="uu_11_2020_bab_1",
        full_text="Ruang lingkup Undang-Undang ini...",
    )
    kg.add_article(article2)

    # Add Law 2: UU 40/2007 (amended)
    law2 = Law(
        id="uu_40_2007",
        number=40,
        year=2007,
        title="UU No. 40 Tahun 2007",
        about="Perseroan Terbatas",
        status="amended",
    )
    kg.add_regulation(law2)

    # Add Government Regulation (implements uu_11_2020)
    pp = GovernmentRegulation(
        id="pp_24_2018",
        number=24,
        year=2018,
        title="PP No. 24 Tahun 2018",
        about="Pelayanan Perizinan Berusaha Terintegrasi Secara Elektronik",
        status="active",
    )
    kg.add_regulation(pp)
    kg.add_edge("pp_24_2018", "uu_11_2020", EdgeType.IMPLEMENTS)

    # Add Presidential Regulation
    perpres = PresidentialRegulation(
        id="perpres_49_2021",
        number=49,
        year=2021,
        title="Perpres No. 49 Tahun 2021",
        about="Perubahan Atas Perpres tentang OSS",
        status="active",
    )
    kg.add_regulation(perpres)

    # Add amendment: uu_11_2020 AMENDS uu_40_2007
    kg.add_edge("uu_11_2020", "uu_40_2007", EdgeType.AMENDS)

    # Add cross-reference: pasal_1 REFERENCES pasal_2
    kg.add_edge("uu_11_2020_pasal_1", "uu_11_2020_pasal_2", EdgeType.REFERENCES)

    # Ensure reverse edges (AMENDED_BY, IMPLEMENTED_BY, etc.)
    kg.ensure_reverse_edges()

    return kg


@pytest.fixture
def reg_kg_patch(regulation_kg):
    """Patch main.knowledge_graph with the regulation test graph."""
    with patch("main.knowledge_graph", regulation_kg):
        yield regulation_kg


@pytest.fixture
def reg_kg_patch_no_rag(regulation_kg):
    """Patch KG and ensure rag_chain is None (no Qdrant enrichment)."""
    with patch("main.knowledge_graph", regulation_kg), \
         patch("main.rag_chain", None):
        yield regulation_kg


# ===========================================================================
# GET /regulations — List
# ===========================================================================


class TestListRegulations:
    def test_list_regulations_default(self, test_client, reg_kg_patch):
        """GET /api/v1/regulations returns 200 with items/total/page fields."""
        response = test_client.get("/api/v1/regulations")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert isinstance(data["items"], list)
        assert data["total"] >= 1

    def test_list_regulations_filter_by_type(self, test_client, reg_kg_patch):
        """?node_type=law filters to only laws."""
        response = test_client.get("/api/v1/regulations?node_type=law")
        assert response.status_code == 200
        data = response.json()
        assert all(item["node_type"] == "law" for item in data["items"])
        assert data["total"] == 2  # uu_11_2020 and uu_40_2007

    def test_list_regulations_filter_by_year(self, test_client, reg_kg_patch):
        """?year=2020 filters by year."""
        response = test_client.get("/api/v1/regulations?year=2020")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["year"] == 2020

    def test_list_regulations_filter_by_status(self, test_client, reg_kg_patch):
        """?status=active filters by status."""
        response = test_client.get("/api/v1/regulations?status=active")
        assert response.status_code == 200
        data = response.json()
        assert all(item["status"] == "active" for item in data["items"])
        # Only Law nodes have a status field in the schema;
        # PP and Perpres don't define status, so only uu_11_2020 matches
        assert data["total"] >= 1

    def test_list_regulations_search(self, test_client, reg_kg_patch):
        """?search=cipta filters by title/about."""
        response = test_client.get("/api/v1/regulations?search=cipta")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any("Cipta" in item["about"] or "cipta" in item["about"].lower()
                    for item in data["items"])

    def test_list_regulations_pagination(self, test_client, reg_kg_patch):
        """?page=2&page_size=1 returns correct slice."""
        response = test_client.get("/api/v1/regulations?page=2&page_size=1")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 1
        assert len(data["items"]) == 1
        assert data["total_pages"] >= 2

    def test_list_regulations_sort_asc(self, test_client, reg_kg_patch):
        """?sort_order=asc reverses sort order."""
        response = test_client.get("/api/v1/regulations?sort_order=asc")
        assert response.status_code == 200
        data = response.json()
        years = [item["year"] for item in data["items"]]
        assert years == sorted(years)

    def test_list_regulations_structure(self, test_client, reg_kg_patch):
        """Response has items, total, page, page_size, total_pages."""
        response = test_client.get("/api/v1/regulations")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        # Check item structure
        if data["items"]:
            item = data["items"][0]
            assert "id" in item
            assert "node_type" in item
            assert "number" in item
            assert "year" in item
            assert "title" in item
            assert "about" in item

    def test_chunk_counts_not_crash(self, test_client, reg_kg_patch_no_rag):
        """Listing works even when rag_chain is None."""
        response = test_client.get("/api/v1/regulations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["items"], list)
        # All indexed_chunk_count should be 0 since rag_chain is None
        for item in data["items"]:
            assert item["indexed_chunk_count"] == 0

    def test_kg_not_loaded_returns_503(self, test_client):
        """Should return 503 when knowledge graph is None."""
        with patch("main.knowledge_graph", None):
            response = test_client.get("/api/v1/regulations")
        assert response.status_code == 503


# ===========================================================================
# GET /regulations/{id} — Detail
# ===========================================================================


class TestRegulationDetail:
    def test_get_regulation_detail(self, test_client, reg_kg_patch):
        """GET /api/v1/regulations/{id} returns 200 with chapters field."""
        response = test_client.get("/api/v1/regulations/uu_11_2020")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "uu_11_2020"
        assert "chapters" in data

    def test_get_regulation_detail_not_found(self, test_client, reg_kg_patch):
        """GET /api/v1/regulations/nonexistent returns 404."""
        response = test_client.get("/api/v1/regulations/nonexistent")
        assert response.status_code == 404

    def test_get_regulation_detail_has_chapters(self, test_client, reg_kg_patch):
        """Detail response contains chapters array."""
        response = test_client.get("/api/v1/regulations/uu_11_2020")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["chapters"], list)
        assert len(data["chapters"]) >= 1
        # Chapter should have articles
        chapter = data["chapters"][0]
        assert "articles" in chapter

    def test_get_regulation_detail_has_amendments(self, test_client, reg_kg_patch):
        """Detail response contains amendments array."""
        response = test_client.get("/api/v1/regulations/uu_11_2020")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["amendments"], list)
        # uu_11_2020 AMENDS uu_40_2007 → should have at least 1 amendment
        assert len(data["amendments"]) >= 1

    def test_regulation_detail_structure(self, test_client, reg_kg_patch):
        """Response has id, node_type, number, year, title, about."""
        response = test_client.get("/api/v1/regulations/uu_11_2020")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "uu_11_2020"
        assert data["node_type"] == "law"
        assert data["number"] == 11
        assert data["year"] == 2020
        assert "title" in data
        assert "about" in data
        assert "status" in data

    def test_regulation_detail_503(self, test_client):
        """503 when KG not loaded."""
        with patch("main.knowledge_graph", None):
            response = test_client.get("/api/v1/regulations/uu_11_2020")
        assert response.status_code == 503


# ===========================================================================
# GET /regulations/{id}/timeline — Amendment Timeline
# ===========================================================================


class TestAmendmentTimeline:
    def test_amendment_timeline(self, test_client, reg_kg_patch):
        """GET /api/v1/regulations/{id}/timeline returns entries."""
        response = test_client.get("/api/v1/regulations/uu_11_2020/timeline")
        assert response.status_code == 200
        data = response.json()
        assert "regulation_id" in data
        assert data["regulation_id"] == "uu_11_2020"
        assert "entries" in data
        assert isinstance(data["entries"], list)
        # uu_11_2020 has AMENDS edge to uu_40_2007, plus reverse AMENDED_BY
        assert len(data["entries"]) >= 1

    def test_amendment_timeline_not_found(self, test_client, reg_kg_patch):
        """404 for missing regulation ID."""
        response = test_client.get("/api/v1/regulations/nonexistent/timeline")
        assert response.status_code == 404

    def test_amendment_timeline_503(self, test_client):
        """503 when KG not loaded."""
        with patch("main.knowledge_graph", None):
            response = test_client.get("/api/v1/regulations/uu_11_2020/timeline")
        assert response.status_code == 503


# ===========================================================================
# GET /regulations/{id}/articles/{aid}/references — Cross-references
# ===========================================================================


class TestArticleCrossReferences:
    def test_article_cross_references(self, test_client, reg_kg_patch):
        """GET /api/v1/regulations/{id}/articles/{aid}/references returns data."""
        response = test_client.get(
            "/api/v1/regulations/uu_11_2020/articles/uu_11_2020_pasal_1/references"
        )
        assert response.status_code == 200
        data = response.json()
        assert "references_to" in data
        assert "referenced_by" in data
        assert isinstance(data["references_to"], list)
        assert isinstance(data["referenced_by"], list)
        # pasal_1 REFERENCES pasal_2 → should have outgoing ref
        assert len(data["references_to"]) >= 1

    def test_article_references_regulation_not_found(self, test_client, reg_kg_patch):
        """404 when regulation ID doesn't exist."""
        response = test_client.get(
            "/api/v1/regulations/nonexistent/articles/any_article/references"
        )
        assert response.status_code == 404

    def test_article_references_503(self, test_client):
        """503 when KG not loaded."""
        with patch("main.knowledge_graph", None):
            response = test_client.get(
                "/api/v1/regulations/uu_11_2020/articles/uu_11_2020_pasal_1/references"
            )
        assert response.status_code == 503
