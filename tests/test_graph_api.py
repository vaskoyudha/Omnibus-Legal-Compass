"""
Tests for Knowledge Graph API endpoints.

Covers:
- GET /api/v1/graph/laws — list all regulations with filters
- GET /api/v1/graph/law/{id} — single law with hierarchy
- GET /api/v1/graph/law/{id}/hierarchy — implementing regulations + amendments
- GET /api/v1/graph/article/{id}/references — cross-references
- GET /api/v1/graph/search?q=... — full-text search
- GET /api/v1/graph/stats — graph statistics
- KG unavailable (503) scenarios
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from knowledge_graph.graph import LegalKnowledgeGraph
from knowledge_graph.schema import (
    Article,
    Chapter,
    GovernmentRegulation,
    Law,
    PresidentialRegulation,
)


# ---------------------------------------------------------------------------
# Fixture: build a small knowledge graph for testing
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_kg() -> LegalKnowledgeGraph:
    """Build a small knowledge graph with known data for API testing."""
    kg = LegalKnowledgeGraph()

    # Add a Law
    law = Law(
        id="uu_11_2020",
        number=11,
        year=2020,
        title="UU No. 11 Tahun 2020",
        about="Cipta Kerja",
        status="active",
    )
    kg.add_regulation(law)

    # Add a Chapter under the law
    chapter = Chapter(
        id="uu_11_2020_bab_1",
        title="Bab I Ketentuan Umum",
        number="I",
        parent_regulation_id="uu_11_2020",
    )
    kg.add_chapter(chapter)

    # Add an Article under the chapter
    article = Article(
        id="uu_11_2020_pasal_1",
        number="1",
        parent_regulation_id="uu_11_2020",
        parent_chapter_id="uu_11_2020_bab_1",
        full_text="Dalam Undang-Undang ini yang dimaksud dengan...",
    )
    kg.add_article(article)

    # Add another Law (amended)
    law2 = Law(
        id="uu_40_2007",
        number=40,
        year=2007,
        title="UU No. 40 Tahun 2007",
        about="Perseroan Terbatas",
        status="amended",
    )
    kg.add_regulation(law2)

    # Add a Government Regulation (implements uu_11_2020)
    pp = GovernmentRegulation(
        id="pp_24_2018",
        number=24,
        year=2018,
        title="PP No. 24 Tahun 2018",
        about="Pelayanan Perizinan Berusaha Terintegrasi Secara Elektronik",
        status="active",
    )
    kg.add_regulation(pp)

    # Add a Presidential Regulation
    perpres = PresidentialRegulation(
        id="perpres_49_2021",
        number=49,
        year=2021,
        title="Perpres No. 49 Tahun 2021",
        about="Perubahan Atas Perpres tentang OSS",
        status="active",
    )
    kg.add_regulation(perpres)

    return kg


@pytest.fixture
def kg_patch(sample_kg):
    """Patch main.knowledge_graph with the sample graph."""
    with patch("main.knowledge_graph", sample_kg):
        yield sample_kg


# ===========================================================================
# GET /graph/laws
# ===========================================================================


class TestListLaws:
    def test_list_all_laws(self, test_client, kg_patch):
        """Should return all regulations."""
        response = test_client.get("/api/v1/graph/laws")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # We have 4 regulations (2 laws + 1 PP + 1 Perpres)
        assert len(data) == 4

    def test_filter_by_status(self, test_client, kg_patch):
        """Filter by status=active should exclude amended."""
        response = test_client.get("/api/v1/graph/laws?status=active")
        assert response.status_code == 200
        data = response.json()
        # Only uu_11_2020 has status=active (PP/Perpres don't have status field)
        assert all(d.get("status") == "active" for d in data if "status" in d)
        assert len(data) >= 1

    def test_filter_by_year(self, test_client, kg_patch):
        """Filter by year=2020."""
        response = test_client.get("/api/v1/graph/laws?year=2020")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["year"] == 2020

    def test_filter_by_node_type(self, test_client, kg_patch):
        """Filter by node_type=law should only return UU."""
        response = test_client.get("/api/v1/graph/laws?node_type=law")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(d["node_type"] == "law" for d in data)

    def test_filter_by_node_type_pp(self, test_client, kg_patch):
        """Filter by node_type=government_regulation."""
        response = test_client.get("/api/v1/graph/laws?node_type=government_regulation")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["node_type"] == "government_regulation"

    def test_kg_not_loaded_returns_503(self, test_client):
        """Should return 503 when knowledge graph is None."""
        with patch("main.knowledge_graph", None):
            response = test_client.get("/api/v1/graph/laws")
        assert response.status_code == 503

    def test_legacy_prefix_works(self, test_client, kg_patch):
        """GET /api/graph/laws should also work."""
        response = test_client.get("/api/graph/laws")
        assert response.status_code == 200


# ===========================================================================
# GET /graph/law/{id}
# ===========================================================================


class TestGetLaw:
    def test_get_law_with_hierarchy(self, test_client, kg_patch):
        """Should return law with children (chapters, articles)."""
        response = test_client.get("/api/v1/graph/law/uu_11_2020")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "uu_11_2020"
        assert data["about"] == "Cipta Kerja"
        assert "children" in data
        assert len(data["children"]) == 1  # 1 chapter
        chapter = data["children"][0]
        assert chapter["title"] == "Bab I Ketentuan Umum"
        assert len(chapter["children"]) == 1  # 1 article
        assert chapter["children"][0]["number"] == "1"

    def test_get_law_not_found(self, test_client, kg_patch):
        """Should return 404 for nonexistent law."""
        response = test_client.get("/api/v1/graph/law/uu_999_2099")
        assert response.status_code == 404

    def test_kg_unavailable_503(self, test_client):
        with patch("main.knowledge_graph", None):
            response = test_client.get("/api/v1/graph/law/uu_11_2020")
        assert response.status_code == 503


# ===========================================================================
# GET /graph/law/{id}/hierarchy
# ===========================================================================


class TestGetLawHierarchy:
    def test_hierarchy_returns_structure(self, test_client, kg_patch):
        """Should return regulation + implementing_regulations + amendments."""
        response = test_client.get("/api/v1/graph/law/uu_11_2020/hierarchy")
        assert response.status_code == 200
        data = response.json()
        assert "regulation" in data
        assert data["regulation"]["id"] == "uu_11_2020"
        assert "implementing_regulations" in data
        assert "amendments" in data
        assert isinstance(data["implementing_regulations"], list)
        assert isinstance(data["amendments"], list)

    def test_hierarchy_not_found(self, test_client, kg_patch):
        response = test_client.get("/api/v1/graph/law/uu_999_2099/hierarchy")
        assert response.status_code == 404

    def test_hierarchy_kg_unavailable(self, test_client):
        with patch("main.knowledge_graph", None):
            response = test_client.get("/api/v1/graph/law/uu_11_2020/hierarchy")
        assert response.status_code == 503


# ===========================================================================
# GET /graph/article/{id}/references
# ===========================================================================


class TestArticleReferences:
    def test_get_references(self, test_client, kg_patch):
        """Should return article data + references list."""
        response = test_client.get("/api/v1/graph/article/uu_11_2020_pasal_1/references")
        assert response.status_code == 200
        data = response.json()
        assert "article" in data
        assert data["article"]["number"] == "1"
        assert "references" in data
        assert isinstance(data["references"], list)

    def test_article_not_found(self, test_client, kg_patch):
        response = test_client.get("/api/v1/graph/article/nonexistent/references")
        assert response.status_code == 404

    def test_article_kg_unavailable(self, test_client):
        with patch("main.knowledge_graph", None):
            response = test_client.get("/api/v1/graph/article/foo/references")
        assert response.status_code == 503


# ===========================================================================
# GET /graph/search
# ===========================================================================


class TestGraphSearch:
    def test_search_finds_results(self, test_client, kg_patch):
        """Searching for 'Cipta Kerja' should find uu_11_2020."""
        response = test_client.get("/api/v1/graph/search?q=Cipta%20Kerja")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(d.get("about") == "Cipta Kerja" for d in data)

    def test_search_case_insensitive(self, test_client, kg_patch):
        """Search should be case-insensitive."""
        response = test_client.get("/api/v1/graph/search?q=cipta%20kerja")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_search_no_results(self, test_client, kg_patch):
        """Should return empty list for unmatched query."""
        response = test_client.get("/api/v1/graph/search?q=zzzzz_not_found")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_search_with_node_type_filter(self, test_client, kg_patch):
        """Filter search by node_type."""
        response = test_client.get("/api/v1/graph/search?q=Perseroan&node_type=law")
        assert response.status_code == 200
        data = response.json()
        assert all(d.get("node_type") == "law" for d in data)

    def test_search_missing_query_returns_422(self, test_client, kg_patch):
        """Missing 'q' parameter should return 422."""
        response = test_client.get("/api/v1/graph/search")
        assert response.status_code == 422

    def test_search_kg_unavailable(self, test_client):
        with patch("main.knowledge_graph", None):
            response = test_client.get("/api/v1/graph/search?q=test")
        assert response.status_code == 503


# ===========================================================================
# GET /graph/stats
# ===========================================================================


class TestGraphStats:
    def test_stats_returns_counts(self, test_client, kg_patch):
        """Should return node/edge counts."""
        response = test_client.get("/api/v1/graph/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_nodes" in data
        assert "total_edges" in data
        assert "nodes_by_type" in data
        assert "edges_by_type" in data
        # We have 6 nodes total (2 laws + 1 PP + 1 Perpres + 1 chapter + 1 article)
        assert data["total_nodes"] == 6

    def test_stats_legacy_prefix(self, test_client, kg_patch):
        """GET /api/graph/stats should also work."""
        response = test_client.get("/api/graph/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_nodes" in data

    def test_stats_kg_unavailable(self, test_client):
        with patch("main.knowledge_graph", None):
            response = test_client.get("/api/v1/graph/stats")
        assert response.status_code == 503
