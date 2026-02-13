"""Tests for the dashboard coverage computation and metrics aggregation."""

from __future__ import annotations

import pytest
from unittest.mock import patch

from knowledge_graph.graph import LegalKnowledgeGraph
from knowledge_graph.schema import (
    Article,
    Chapter,
    EdgeType,
    GovernmentRegulation,
    Law,
    PresidentialRegulation,
)
from dashboard.coverage import (
    CoverageComputer,
    DomainCoverage,
    LawCoverage,
    classify_domain,
)
from dashboard.metrics import DashboardStats, MetricsAggregator


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def empty_graph() -> LegalKnowledgeGraph:
    """Empty knowledge graph."""
    return LegalKnowledgeGraph()


@pytest.fixture
def sample_graph() -> LegalKnowledgeGraph:
    """Knowledge graph with multiple regulations, chapters, and articles."""
    kg = LegalKnowledgeGraph()

    # Law 1: Cipta Kerja (Ketenagakerjaan domain — has "kerja" in about)
    law1 = Law(
        id="uu_11_2020",
        number=11,
        year=2020,
        title="Cipta Kerja",
        about="Penciptaan Lapangan Kerja",
        status="active",
    )
    kg.add_regulation(law1)

    ch1 = Chapter(
        id="uu_11_2020_bab_I",
        number="I",
        title="Ketentuan Umum",
        parent_regulation_id="uu_11_2020",
    )
    kg.add_chapter(ch1)

    art1 = Article(
        id="uu_11_2020_pasal_1",
        number="1",
        full_text="Pasal 1 isi",
        parent_chapter_id="uu_11_2020_bab_I",
        parent_regulation_id="uu_11_2020",
    )
    kg.add_article(art1)

    art2 = Article(
        id="uu_11_2020_pasal_5",
        number="5",
        full_text="Pasal 5 isi",
        parent_chapter_id="uu_11_2020_bab_I",
        parent_regulation_id="uu_11_2020",
    )
    kg.add_article(art2)

    # Law 2: Perlindungan Data
    law2 = Law(
        id="uu_27_2022",
        number=27,
        year=2022,
        title="Pelindungan Data Pribadi",
        about="Perlindungan Data Pribadi",
        status="active",
    )
    kg.add_regulation(law2)

    art3 = Article(
        id="uu_27_2022_pasal_2",
        number="2",
        full_text="Pasal 2 isi",
        parent_chapter_id=None,
        parent_regulation_id="uu_27_2022",
    )
    kg.add_article(art3)

    # PP: Perizinan Berusaha
    pp = GovernmentRegulation(
        id="pp_24_2018",
        number=24,
        year=2018,
        title="Perizinan Berusaha",
        about="Pelayanan Perizinan Berusaha Terintegrasi Secara Elektronik",
    )
    kg.add_regulation(pp)

    art4 = Article(
        id="pp_24_2018_pasal_1",
        number="1",
        full_text="Pasal 1 PP",
        parent_chapter_id=None,
        parent_regulation_id="pp_24_2018",
    )
    kg.add_article(art4)

    art5 = Article(
        id="pp_24_2018_pasal_3",
        number="3",
        full_text="Pasal 3 PP",
        parent_chapter_id=None,
        parent_regulation_id="pp_24_2018",
    )
    kg.add_article(art5)

    # Perpres: NIB
    perpres = PresidentialRegulation(
        id="perpres_49_2021",
        number=49,
        year=2021,
        title="NIB",
        about="Percepatan Pelaksanaan Berusaha",
    )
    kg.add_regulation(perpres)

    art6 = Article(
        id="perpres_49_2021_pasal_3",
        number="3",
        full_text="Pasal 3 Perpres",
        parent_chapter_id=None,
        parent_regulation_id="perpres_49_2021",
    )
    kg.add_article(art6)

    return kg


# ── classify_domain tests ──────────────────────────────────────────────────


class TestClassifyDomain:
    """Tests for the domain classification function."""

    def test_ketenagakerjaan_domain(self) -> None:
        assert classify_domain("Penciptaan Lapangan Kerja") == "Ketenagakerjaan"

    def test_perizinan_domain(self) -> None:
        assert classify_domain("Pelayanan Perizinan Berusaha Terintegrasi") == "Perizinan Usaha"

    def test_perlindungan_data_domain(self) -> None:
        assert classify_domain("Perlindungan Data Pribadi") == "Perlindungan Data"

    def test_badan_usaha_domain(self) -> None:
        assert classify_domain("Perseroan Terbatas") == "Badan Usaha"

    def test_investasi_domain(self) -> None:
        assert classify_domain("Penanaman Modal Asing") == "Investasi"

    def test_lingkungan_domain(self) -> None:
        assert classify_domain("Dampak Lingkungan Hidup") == "Lingkungan"

    def test_perpajakan_domain(self) -> None:
        assert classify_domain("Pajak Penghasilan") == "Perpajakan"

    def test_default_domain(self) -> None:
        assert classify_domain("Sesuatu Tidak Dikenal") == "Lainnya"

    def test_case_insensitive(self) -> None:
        assert classify_domain("PERLINDUNGAN DATA PRIBADI") == "Perlindungan Data"

    def test_percepatan_berusaha(self) -> None:
        assert classify_domain("Percepatan Pelaksanaan Berusaha") == "Perizinan Usaha"


# ── CoverageComputer tests ──────────────────────────────────────────────────


class TestCoverageComputer:
    """Tests for the CoverageComputer class."""

    def test_empty_graph(self, empty_graph: LegalKnowledgeGraph) -> None:
        comp = CoverageComputer(empty_graph)
        result = comp.compute_all_coverage()
        assert result == []

    def test_nonexistent_regulation(self, sample_graph: LegalKnowledgeGraph) -> None:
        comp = CoverageComputer(sample_graph)
        result = comp.compute_law_coverage("nonexistent_id")
        assert result is None

    def test_zero_indexed(self, sample_graph: LegalKnowledgeGraph) -> None:
        """No articles indexed → 0% coverage."""
        comp = CoverageComputer(sample_graph, indexed_article_ids=set())
        cov = comp.compute_law_coverage("uu_11_2020")
        assert cov is not None
        assert cov.total_articles == 2
        assert cov.indexed_articles == 0
        assert cov.coverage_percent == 0.0
        assert len(cov.missing_articles) == 2

    def test_partial_coverage(self, sample_graph: LegalKnowledgeGraph) -> None:
        """1 of 2 articles indexed → 50%."""
        comp = CoverageComputer(
            sample_graph,
            indexed_article_ids={"uu_11_2020_pasal_1"},
        )
        cov = comp.compute_law_coverage("uu_11_2020")
        assert cov is not None
        assert cov.total_articles == 2
        assert cov.indexed_articles == 1
        assert cov.coverage_percent == 50.0
        assert "uu_11_2020_pasal_5" in cov.missing_articles

    def test_full_coverage(self, sample_graph: LegalKnowledgeGraph) -> None:
        """All articles indexed → 100%."""
        comp = CoverageComputer(
            sample_graph,
            indexed_article_ids={"uu_11_2020_pasal_1", "uu_11_2020_pasal_5"},
        )
        cov = comp.compute_law_coverage("uu_11_2020")
        assert cov is not None
        assert cov.total_articles == 2
        assert cov.indexed_articles == 2
        assert cov.coverage_percent == 100.0
        assert cov.missing_articles == []

    def test_law_coverage_metadata(self, sample_graph: LegalKnowledgeGraph) -> None:
        comp = CoverageComputer(sample_graph)
        cov = comp.compute_law_coverage("uu_11_2020")
        assert cov is not None
        assert cov.regulation_id == "uu_11_2020"
        assert cov.regulation_type == "law"
        assert cov.title == "Cipta Kerja"
        assert cov.domain == "Ketenagakerjaan"
        assert cov.total_chapters == 1  # bab_I

    def test_government_regulation_coverage(self, sample_graph: LegalKnowledgeGraph) -> None:
        comp = CoverageComputer(
            sample_graph,
            indexed_article_ids={"pp_24_2018_pasal_1"},
        )
        cov = comp.compute_law_coverage("pp_24_2018")
        assert cov is not None
        assert cov.regulation_type == "government_regulation"
        assert cov.total_articles == 2
        assert cov.indexed_articles == 1
        assert cov.coverage_percent == 50.0

    def test_regulation_with_no_articles(self, empty_graph: LegalKnowledgeGraph) -> None:
        """Regulation with 0 articles → 0% coverage."""
        kg = empty_graph
        law = Law(
            id="uu_1_2000",
            number=1,
            year=2000,
            title="Empty Law",
            about="Pajak",
            status="active",
        )
        kg.add_regulation(law)
        comp = CoverageComputer(kg)
        cov = comp.compute_law_coverage("uu_1_2000")
        assert cov is not None
        assert cov.total_articles == 0
        assert cov.coverage_percent == 0.0

    def test_compute_all_coverage(self, sample_graph: LegalKnowledgeGraph) -> None:
        comp = CoverageComputer(sample_graph)
        results = comp.compute_all_coverage()
        # 4 regulations: uu_11_2020, uu_27_2022, pp_24_2018, perpres_49_2021
        assert len(results) == 4
        ids = {r.regulation_id for r in results}
        assert ids == {"uu_11_2020", "uu_27_2022", "pp_24_2018", "perpres_49_2021"}

    def test_compute_domain_coverage(self, sample_graph: LegalKnowledgeGraph) -> None:
        all_articles = {
            "uu_11_2020_pasal_1", "uu_11_2020_pasal_5",
            "uu_27_2022_pasal_2",
        }
        comp = CoverageComputer(sample_graph, indexed_article_ids=all_articles)
        domains = comp.compute_domain_coverage()
        assert len(domains) > 0

        # Check domain names
        domain_names = {d.domain for d in domains}
        assert "Ketenagakerjaan" in domain_names
        assert "Perlindungan Data" in domain_names
        assert "Perizinan Usaha" in domain_names

    def test_domain_coverage_aggregation(self, sample_graph: LegalKnowledgeGraph) -> None:
        """Perizinan Usaha domain has pp_24_2018 (2 arts) + perpres_49_2021 (1 art)."""
        comp = CoverageComputer(
            sample_graph,
            indexed_article_ids={"pp_24_2018_pasal_1", "perpres_49_2021_pasal_3"},
        )
        domains = comp.compute_domain_coverage()
        perizinan = next((d for d in domains if d.domain == "Perizinan Usaha"), None)
        assert perizinan is not None
        assert perizinan.regulation_count == 2
        assert perizinan.total_articles == 3  # 2 from PP + 1 from Perpres
        assert perizinan.indexed_articles == 2
        assert perizinan.coverage_percent == pytest.approx(66.7, abs=0.1)

    def test_domain_coverage_sorted(self, sample_graph: LegalKnowledgeGraph) -> None:
        comp = CoverageComputer(sample_graph)
        domains = comp.compute_domain_coverage()
        names = [d.domain for d in domains]
        assert names == sorted(names)

    def test_none_indexed_defaults_empty(self, sample_graph: LegalKnowledgeGraph) -> None:
        comp = CoverageComputer(sample_graph, indexed_article_ids=None)
        cov = comp.compute_law_coverage("uu_11_2020")
        assert cov is not None
        assert cov.indexed_articles == 0


# ── DomainCoverage model tests ─────────────────────────────────────────────


class TestDomainCoverageModel:
    """Tests for the DomainCoverage Pydantic model."""

    def test_create_domain_coverage(self) -> None:
        dc = DomainCoverage(
            domain="Test",
            total_articles=10,
            indexed_articles=5,
            coverage_percent=50.0,
            regulation_count=2,
        )
        assert dc.domain == "Test"
        assert dc.total_articles == 10

    def test_domain_coverage_serialization(self) -> None:
        dc = DomainCoverage(
            domain="Test",
            total_articles=0,
            indexed_articles=0,
            coverage_percent=0,
            regulation_count=0,
        )
        data = dc.model_dump()
        assert "domain" in data
        assert "laws" in data
        assert data["laws"] == []


# ── LawCoverage model tests ────────────────────────────────────────────────


class TestLawCoverageModel:
    """Tests for the LawCoverage Pydantic model."""

    def test_create_law_coverage(self) -> None:
        lc = LawCoverage(
            regulation_id="uu_1_2000",
            regulation_type="law",
            title="Test",
            about="About test",
            domain="Test",
            total_articles=5,
            indexed_articles=3,
            coverage_percent=60.0,
        )
        assert lc.coverage_percent == 60.0

    def test_missing_articles_default(self) -> None:
        lc = LawCoverage(
            regulation_id="uu_1_2000",
            regulation_type="law",
            title="Test",
            about="About",
            domain="Test",
            total_articles=0,
            indexed_articles=0,
            coverage_percent=0,
        )
        assert lc.missing_articles == []


# ── MetricsAggregator tests ────────────────────────────────────────────────


class TestMetricsAggregator:
    """Tests for the MetricsAggregator class."""

    def test_empty_graph_stats(self, empty_graph: LegalKnowledgeGraph) -> None:
        comp = CoverageComputer(empty_graph)
        agg = MetricsAggregator(empty_graph, comp)
        stats = agg.compute_stats()
        assert stats.overall_coverage_percent == 0.0
        assert stats.total_regulations == 0
        assert stats.total_articles == 0
        assert stats.indexed_articles == 0
        assert stats.domain_count == 0
        assert stats.most_covered_domain is None
        assert stats.least_covered_domain is None
        assert stats.last_updated != ""

    def test_stats_with_data(self, sample_graph: LegalKnowledgeGraph) -> None:
        indexed = {"uu_11_2020_pasal_1", "uu_27_2022_pasal_2"}
        comp = CoverageComputer(sample_graph, indexed_article_ids=indexed)
        agg = MetricsAggregator(sample_graph, comp)
        stats = agg.compute_stats()

        assert stats.total_regulations == 4
        assert stats.total_articles == 6  # 6 article nodes
        assert stats.indexed_articles == 2
        assert stats.overall_coverage_percent > 0
        assert stats.domain_count >= 3

    def test_most_least_covered(self, sample_graph: LegalKnowledgeGraph) -> None:
        """Index all Ketenagakerjaan, none of Perizinan → check most/least."""
        indexed = {"uu_11_2020_pasal_1", "uu_11_2020_pasal_5"}
        comp = CoverageComputer(sample_graph, indexed_article_ids=indexed)
        agg = MetricsAggregator(sample_graph, comp)
        stats = agg.compute_stats()

        assert stats.most_covered_domain == "Ketenagakerjaan"
        # Least covered is one of the 0% domains
        assert stats.least_covered_domain in {"Perlindungan Data", "Perizinan Usaha"}

    def test_stats_has_last_updated(self, sample_graph: LegalKnowledgeGraph) -> None:
        comp = CoverageComputer(sample_graph)
        agg = MetricsAggregator(sample_graph, comp)
        stats = agg.compute_stats()
        # ISO format has 'T' separator
        assert "T" in stats.last_updated

    def test_full_coverage_stats(self, sample_graph: LegalKnowledgeGraph) -> None:
        all_ids = {
            "uu_11_2020_pasal_1", "uu_11_2020_pasal_5",
            "uu_27_2022_pasal_2",
            "pp_24_2018_pasal_1", "pp_24_2018_pasal_3",
            "perpres_49_2021_pasal_3",
        }
        comp = CoverageComputer(sample_graph, indexed_article_ids=all_ids)
        agg = MetricsAggregator(sample_graph, comp)
        stats = agg.compute_stats()
        assert stats.overall_coverage_percent == 100.0
        assert stats.indexed_articles == 6

    def test_stats_serialization(self, sample_graph: LegalKnowledgeGraph) -> None:
        comp = CoverageComputer(sample_graph)
        agg = MetricsAggregator(sample_graph, comp)
        stats = agg.compute_stats()
        data = stats.model_dump()
        assert "overall_coverage_percent" in data
        assert "total_regulations" in data
        assert "most_covered_domain" in data
        assert "last_updated" in data


# ── API endpoint tests (integration via FastAPI TestClient) ─────────────────

from fastapi.testclient import TestClient


@pytest.fixture
def mock_graph(sample_graph: LegalKnowledgeGraph):
    """Patch the global knowledge_graph in main.py."""
    with patch("main.knowledge_graph", sample_graph):
        yield sample_graph


@pytest.fixture
def client(mock_graph):
    """FastAPI test client with mocked graph."""
    from main import app
    return TestClient(app, raise_server_exceptions=False)


class TestDashboardAPI:
    """Tests for the dashboard API endpoints."""

    def test_coverage_endpoint(self, client: TestClient) -> None:
        resp = client.get("/api/v1/dashboard/coverage")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Each item should have required fields
        item = data[0]
        assert "regulation_id" in item
        assert "total_articles" in item
        assert "indexed_articles" in item
        assert "coverage_percent" in item
        assert "domain" in item

    def test_stats_endpoint(self, client: TestClient) -> None:
        resp = client.get("/api/v1/dashboard/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_coverage_percent" in data
        assert "total_regulations" in data
        assert "total_articles" in data
        assert "last_updated" in data
        assert 0 <= data["overall_coverage_percent"] <= 100

    def test_domain_coverage_endpoint(self, client: TestClient) -> None:
        resp = client.get("/api/v1/dashboard/coverage/Ketenagakerjaan")
        assert resp.status_code == 200
        data = resp.json()
        assert data["domain"] == "Ketenagakerjaan"
        assert "total_articles" in data
        assert "laws" in data

    def test_domain_coverage_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/v1/dashboard/coverage/NonExistentDomain")
        assert resp.status_code == 404

    def test_coverage_returns_all_regulations(self, client: TestClient) -> None:
        resp = client.get("/api/v1/dashboard/coverage")
        data = resp.json()
        ids = {item["regulation_id"] for item in data}
        assert "uu_11_2020" in ids
        assert "pp_24_2018" in ids

    def test_stats_domain_count(self, client: TestClient) -> None:
        resp = client.get("/api/v1/dashboard/stats")
        data = resp.json()
        assert data["domain_count"] >= 1
