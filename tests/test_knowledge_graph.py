"""
Comprehensive tests for the Knowledge Graph schema and graph operations.

Covers:
- Pydantic model creation and validation
- Graph add/get operations
- Hierarchy traversal
- Cross-reference tracking
- Amendment chains
- Implementing regulations
- Serialization round-trip
- Text search
- Statistics
"""

from __future__ import annotations

import pytest

from knowledge_graph import (
    Article,
    Chapter,
    EdgeType,
    GovernmentRegulation,
    Law,
    LegalKnowledgeGraph,
    MinisterialRegulation,
    PresidentialRegulation,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def uu_cipta_kerja() -> Law:
    return Law(
        id="uu_11_2020",
        number=11,
        year=2020,
        title="Cipta Kerja",
        about="Penciptaan Lapangan Kerja",
        status="active",
    )


@pytest.fixture
def uu_pdp() -> Law:
    return Law(
        id="uu_27_2022",
        number=27,
        year=2022,
        title="Pelindungan Data Pribadi",
        about="Perlindungan Data Pribadi",
    )


@pytest.fixture
def uu_pt() -> Law:
    return Law(
        id="uu_40_2007",
        number=40,
        year=2007,
        title="Perseroan Terbatas",
        about="Perseroan Terbatas",
    )


@pytest.fixture
def pp_perizinan() -> GovernmentRegulation:
    return GovernmentRegulation(
        id="pp_24_2018",
        number=24,
        year=2018,
        title="Perizinan Berusaha Terintegrasi",
        about="Pelayanan Perizinan Berusaha Terintegrasi Secara Elektronik",
        parent_law_id="uu_11_2020",
    )


@pytest.fixture
def perpres_nib() -> PresidentialRegulation:
    return PresidentialRegulation(
        id="perpres_49_2021",
        number=49,
        year=2021,
        title="NIB",
        about="Percepatan Pelaksanaan Berusaha",
        parent_law_id="uu_11_2020",
    )


@pytest.fixture
def permen_example() -> MinisterialRegulation:
    return MinisterialRegulation(
        id="permen_5_2021",
        number=5,
        year=2021,
        title="Pedoman Perizinan",
        about="Pedoman Pelaksanaan Perizinan Berusaha",
        issuing_ministry="Kementerian Investasi",
    )


@pytest.fixture
def chapter_bab1(uu_cipta_kerja: Law) -> Chapter:
    return Chapter(
        id="uu_11_2020_bab_I",
        number="I",
        title="Ketentuan Umum",
        parent_regulation_id=uu_cipta_kerja.id,
    )


@pytest.fixture
def chapter_bab3(uu_cipta_kerja: Law) -> Chapter:
    return Chapter(
        id="uu_11_2020_bab_III",
        number="III",
        title="Penanaman Modal",
        parent_regulation_id=uu_cipta_kerja.id,
    )


@pytest.fixture
def article_pasal1(uu_cipta_kerja: Law, chapter_bab1: Chapter) -> Article:
    return Article(
        id="uu_11_2020_pasal_1",
        number="1",
        content_summary="Definisi dan ketentuan umum",
        full_text=(
            "Dalam Undang-Undang ini yang dimaksud dengan: "
            "a. Penanaman Modal adalah kegiatan menanamkan modal."
        ),
        parent_chapter_id=chapter_bab1.id,
        parent_regulation_id=uu_cipta_kerja.id,
    )


@pytest.fixture
def article_pasal5(uu_cipta_kerja: Law, chapter_bab3: Chapter) -> Article:
    return Article(
        id="uu_11_2020_pasal_5",
        number="5",
        content_summary="Hak penanam modal",
        full_text=(
            "Setiap penanam modal berhak mendapatkan kemudahan "
            "sebagaimana dimaksud dalam Pasal 1."
        ),
        parent_chapter_id=chapter_bab3.id,
        parent_regulation_id=uu_cipta_kerja.id,
    )


@pytest.fixture
def populated_graph(
    uu_cipta_kerja: Law,
    uu_pdp: Law,
    pp_perizinan: GovernmentRegulation,
    perpres_nib: PresidentialRegulation,
    chapter_bab1: Chapter,
    chapter_bab3: Chapter,
    article_pasal1: Article,
    article_pasal5: Article,
) -> LegalKnowledgeGraph:
    """A graph pre-populated with a realistic set of nodes and edges."""
    kg = LegalKnowledgeGraph()
    kg.add_regulation(uu_cipta_kerja)
    kg.add_regulation(uu_pdp)
    kg.add_regulation(pp_perizinan)
    kg.add_regulation(perpres_nib)
    kg.add_chapter(chapter_bab1)
    kg.add_chapter(chapter_bab3)
    kg.add_article(article_pasal1)
    kg.add_article(article_pasal5)
    # PP implements UU
    kg.add_edge("pp_24_2018", "uu_11_2020", EdgeType.IMPLEMENTS)
    # Perpres implements UU
    kg.add_edge("perpres_49_2021", "uu_11_2020", EdgeType.IMPLEMENTS)
    # Cross-reference: pasal 5 references pasal 1
    kg.add_edge(
        "uu_11_2020_pasal_5",
        "uu_11_2020_pasal_1",
        EdgeType.REFERENCES,
        metadata={"reference_text": "sebagaimana dimaksud dalam Pasal 1"},
    )
    return kg


# ── Schema Model Tests ───────────────────────────────────────────────────────


class TestSchemaModels:
    """Tests for Pydantic model creation and validation."""

    def test_law_creation(self, uu_cipta_kerja: Law) -> None:
        assert uu_cipta_kerja.id == "uu_11_2020"
        assert uu_cipta_kerja.node_type == "law"
        assert uu_cipta_kerja.number == 11
        assert uu_cipta_kerja.year == 2020
        assert uu_cipta_kerja.title == "Cipta Kerja"
        assert uu_cipta_kerja.status == "active"

    def test_law_default_status(self) -> None:
        law = Law(id="uu_1_2020", number=1, year=2020, title="Test", about="Test")
        assert law.status == "active"
        assert law.enactment_date is None

    def test_law_amended_status(self) -> None:
        law = Law(
            id="uu_1_2020",
            number=1,
            year=2020,
            title="Test",
            about="Test",
            status="amended",
        )
        assert law.status == "amended"

    def test_law_repealed_status(self) -> None:
        law = Law(
            id="uu_1_2020",
            number=1,
            year=2020,
            title="Test",
            about="Test",
            status="repealed",
        )
        assert law.status == "repealed"

    def test_government_regulation_creation(self, pp_perizinan: GovernmentRegulation) -> None:
        assert pp_perizinan.id == "pp_24_2018"
        assert pp_perizinan.node_type == "government_regulation"
        assert pp_perizinan.parent_law_id == "uu_11_2020"

    def test_presidential_regulation_creation(self, perpres_nib: PresidentialRegulation) -> None:
        assert perpres_nib.id == "perpres_49_2021"
        assert perpres_nib.node_type == "presidential_regulation"
        assert perpres_nib.parent_law_id == "uu_11_2020"

    def test_ministerial_regulation_creation(self, permen_example: MinisterialRegulation) -> None:
        assert permen_example.id == "permen_5_2021"
        assert permen_example.node_type == "ministerial_regulation"
        assert permen_example.issuing_ministry == "Kementerian Investasi"

    def test_chapter_creation(self, chapter_bab1: Chapter) -> None:
        assert chapter_bab1.id == "uu_11_2020_bab_I"
        assert chapter_bab1.node_type == "chapter"
        assert chapter_bab1.number == "I"
        assert chapter_bab1.title == "Ketentuan Umum"
        assert chapter_bab1.parent_regulation_id == "uu_11_2020"

    def test_article_creation(self, article_pasal1: Article) -> None:
        assert article_pasal1.id == "uu_11_2020_pasal_1"
        assert article_pasal1.node_type == "article"
        assert article_pasal1.number == "1"
        assert article_pasal1.parent_chapter_id == "uu_11_2020_bab_I"
        assert article_pasal1.parent_regulation_id == "uu_11_2020"
        assert "Penanaman Modal" in article_pasal1.full_text

    def test_article_without_chapter(self) -> None:
        article = Article(
            id="pp_24_2018_pasal_1",
            number="1",
            full_text="Perizinan Berusaha adalah lisensi...",
            parent_regulation_id="pp_24_2018",
        )
        assert article.parent_chapter_id is None
        assert article.content_summary is None

    def test_edge_type_values(self) -> None:
        assert EdgeType.CONTAINS.value == "CONTAINS"
        assert EdgeType.IMPLEMENTS.value == "IMPLEMENTS"
        assert EdgeType.AMENDS.value == "AMENDS"
        assert EdgeType.REFERENCES.value == "REFERENCES"
        assert EdgeType.SUPERSEDES.value == "SUPERSEDES"

    def test_law_model_dump(self, uu_cipta_kerja: Law) -> None:
        data = uu_cipta_kerja.model_dump()
        assert data["id"] == "uu_11_2020"
        assert data["node_type"] == "law"
        assert data["number"] == 11
        assert data["year"] == 2020

    def test_law_with_enactment_date(self) -> None:
        law = Law(
            id="uu_11_2020",
            number=11,
            year=2020,
            title="Cipta Kerja",
            about="Penciptaan Lapangan Kerja",
            enactment_date="2020-11-02",
        )
        assert law.enactment_date == "2020-11-02"


# ── Graph Add/Get Tests ──────────────────────────────────────────────────────


class TestGraphOperations:
    """Tests for graph add and get operations."""

    def test_add_and_get_regulation(self, uu_cipta_kerja: Law) -> None:
        kg = LegalKnowledgeGraph()
        kg.add_regulation(uu_cipta_kerja)
        result = kg.get_regulation("uu_11_2020")
        assert result is not None
        assert result["title"] == "Cipta Kerja"
        assert result["node_type"] == "law"

    def test_get_nonexistent_regulation(self) -> None:
        kg = LegalKnowledgeGraph()
        assert kg.get_regulation("nonexistent") is None

    def test_add_chapter_creates_contains_edge(
        self, uu_cipta_kerja: Law, chapter_bab1: Chapter
    ) -> None:
        kg = LegalKnowledgeGraph()
        kg.add_regulation(uu_cipta_kerja)
        kg.add_chapter(chapter_bab1)
        # Check CONTAINS edge exists
        assert kg.graph.has_edge("uu_11_2020", "uu_11_2020_bab_I")
        edge_data = kg.graph.edges["uu_11_2020", "uu_11_2020_bab_I"]
        assert edge_data["edge_type"] == EdgeType.CONTAINS.value

    def test_add_article_creates_contains_edge_to_chapter(
        self,
        uu_cipta_kerja: Law,
        chapter_bab1: Chapter,
        article_pasal1: Article,
    ) -> None:
        kg = LegalKnowledgeGraph()
        kg.add_regulation(uu_cipta_kerja)
        kg.add_chapter(chapter_bab1)
        kg.add_article(article_pasal1)
        # Edge from chapter to article
        assert kg.graph.has_edge("uu_11_2020_bab_I", "uu_11_2020_pasal_1")

    def test_add_article_without_chapter_links_to_regulation(self) -> None:
        kg = LegalKnowledgeGraph()
        pp = GovernmentRegulation(
            id="pp_24_2018",
            number=24,
            year=2018,
            title="Perizinan",
            about="Perizinan",
        )
        kg.add_regulation(pp)
        article = Article(
            id="pp_24_2018_pasal_1",
            number="1",
            full_text="Perizinan Berusaha adalah lisensi...",
            parent_regulation_id="pp_24_2018",
        )
        kg.add_article(article)
        # Edge from regulation to article (no chapter)
        assert kg.graph.has_edge("pp_24_2018", "pp_24_2018_pasal_1")

    def test_add_edge_with_metadata(self) -> None:
        kg = LegalKnowledgeGraph()
        kg.add_edge(
            "a",
            "b",
            EdgeType.REFERENCES,
            metadata={"reason": "cross-ref"},
        )
        edge = kg.graph.edges["a", "b"]
        assert edge["edge_type"] == EdgeType.REFERENCES.value
        assert edge["metadata"]["reason"] == "cross-ref"


# ── Hierarchy Tests ──────────────────────────────────────────────────────────


class TestHierarchy:
    """Tests for hierarchy traversal."""

    def test_get_hierarchy_full(self, populated_graph: LegalKnowledgeGraph) -> None:
        hierarchy = populated_graph.get_hierarchy("uu_11_2020")
        assert hierarchy["title"] == "Cipta Kerja"
        assert len(hierarchy["children"]) == 2  # bab I and bab III
        # Each chapter should have its article
        for child in hierarchy["children"]:
            assert child["node_type"] == "chapter"
            assert len(child["children"]) == 1

    def test_get_hierarchy_nonexistent(self) -> None:
        kg = LegalKnowledgeGraph()
        assert kg.get_hierarchy("nonexistent") == {}

    def test_hierarchy_chapter_articles(self, populated_graph: LegalKnowledgeGraph) -> None:
        hierarchy = populated_graph.get_hierarchy("uu_11_2020")
        # Find bab I
        bab1 = next(c for c in hierarchy["children"] if c["number"] == "I")
        assert bab1["title"] == "Ketentuan Umum"
        assert bab1["children"][0]["number"] == "1"


# ── Cross-reference Tests ────────────────────────────────────────────────────


class TestReferences:
    """Tests for cross-reference tracking."""

    def test_get_references_outgoing(self, populated_graph: LegalKnowledgeGraph) -> None:
        refs = populated_graph.get_references("uu_11_2020_pasal_5")
        assert len(refs) == 1
        assert refs[0]["number"] == "1"

    def test_get_references_incoming(self, populated_graph: LegalKnowledgeGraph) -> None:
        refs = populated_graph.get_references("uu_11_2020_pasal_1")
        assert len(refs) == 1
        assert refs[0]["number"] == "5"

    def test_get_references_none(self) -> None:
        kg = LegalKnowledgeGraph()
        assert kg.get_references("nonexistent") == []


# ── Amendment Tests ──────────────────────────────────────────────────────────


class TestAmendments:
    """Tests for amendment chain tracking."""

    def test_amendment_chain(self) -> None:
        kg = LegalKnowledgeGraph()
        original = Law(
            id="uu_40_2007", number=40, year=2007, title="PT", about="Perseroan Terbatas"
        )
        amending = Law(
            id="uu_11_2020",
            number=11,
            year=2020,
            title="Cipta Kerja",
            about="Penciptaan Lapangan Kerja",
        )
        kg.add_regulation(original)
        kg.add_regulation(amending)
        kg.add_edge("uu_11_2020", "uu_40_2007", EdgeType.AMENDS)

        amendments = kg.get_amendments("uu_40_2007")
        assert len(amendments) == 1
        assert amendments[0]["title"] == "Cipta Kerja"

    def test_amendment_outgoing(self) -> None:
        kg = LegalKnowledgeGraph()
        original = Law(
            id="uu_40_2007", number=40, year=2007, title="PT", about="Perseroan Terbatas"
        )
        amending = Law(
            id="uu_11_2020",
            number=11,
            year=2020,
            title="Cipta Kerja",
            about="Penciptaan Lapangan Kerja",
        )
        kg.add_regulation(original)
        kg.add_regulation(amending)
        kg.add_edge("uu_11_2020", "uu_40_2007", EdgeType.AMENDS)

        amendments = kg.get_amendments("uu_11_2020")
        assert len(amendments) == 1
        assert amendments[0]["title"] == "PT"


# ── Implementing Regulations Tests ───────────────────────────────────────────


class TestImplementingRegulations:
    """Tests for finding implementing regulations."""

    def test_get_implementing_regulations(
        self, populated_graph: LegalKnowledgeGraph
    ) -> None:
        impls = populated_graph.get_implementing_regulations("uu_11_2020")
        assert len(impls) == 2
        impl_ids = {r["id"] for r in impls}
        assert "pp_24_2018" in impl_ids
        assert "perpres_49_2021" in impl_ids

    def test_no_implementing_regulations(
        self, populated_graph: LegalKnowledgeGraph
    ) -> None:
        impls = populated_graph.get_implementing_regulations("uu_27_2022")
        assert impls == []


# ── Search Tests ─────────────────────────────────────────────────────────────


class TestSearch:
    """Tests for text search across nodes."""

    def test_search_by_title(self, populated_graph: LegalKnowledgeGraph) -> None:
        results = populated_graph.search_nodes("Cipta Kerja")
        assert len(results) >= 1
        assert any(r["title"] == "Cipta Kerja" for r in results)

    def test_search_case_insensitive(self, populated_graph: LegalKnowledgeGraph) -> None:
        results = populated_graph.search_nodes("cipta kerja")
        assert len(results) >= 1

    def test_search_with_node_type_filter(
        self, populated_graph: LegalKnowledgeGraph
    ) -> None:
        results = populated_graph.search_nodes("Perizinan", node_type="government_regulation")
        assert len(results) == 1
        assert results[0]["node_type"] == "government_regulation"

    def test_search_no_results(self, populated_graph: LegalKnowledgeGraph) -> None:
        results = populated_graph.search_nodes("zzz_nonexistent_zzz")
        assert results == []

    def test_search_full_text(self, populated_graph: LegalKnowledgeGraph) -> None:
        results = populated_graph.search_nodes("Penanaman Modal", node_type="article")
        assert len(results) >= 1


# ── Stats Tests ──────────────────────────────────────────────────────────────


class TestStats:
    """Tests for graph statistics."""

    def test_stats_node_counts(self, populated_graph: LegalKnowledgeGraph) -> None:
        stats = populated_graph.get_stats()
        assert stats["total_nodes"] == 8  # 3 regs + 1 perpres + 2 chapters + 2 articles
        assert stats["nodes_by_type"]["law"] == 2
        assert stats["nodes_by_type"]["government_regulation"] == 1
        assert stats["nodes_by_type"]["presidential_regulation"] == 1
        assert stats["nodes_by_type"]["chapter"] == 2
        assert stats["nodes_by_type"]["article"] == 2

    def test_stats_edge_counts(self, populated_graph: LegalKnowledgeGraph) -> None:
        stats = populated_graph.get_stats()
        assert stats["total_edges"] == 7  # 2 CONTAINS(reg→chap) + 2 CONTAINS(chap→art) + 2 IMPLEMENTS + 1 REFERENCES
        assert stats["edges_by_type"]["CONTAINS"] == 4
        assert stats["edges_by_type"]["IMPLEMENTS"] == 2
        assert stats["edges_by_type"]["REFERENCES"] == 1

    def test_stats_empty_graph(self) -> None:
        kg = LegalKnowledgeGraph()
        stats = kg.get_stats()
        assert stats["total_nodes"] == 0
        assert stats["total_edges"] == 0
        assert stats["nodes_by_type"] == {}
        assert stats["edges_by_type"] == {}


# ── Serialization Tests ──────────────────────────────────────────────────────


class TestSerialization:
    """Tests for to_dict / from_dict round-trip."""

    def test_to_dict_structure(self, populated_graph: LegalKnowledgeGraph) -> None:
        data = populated_graph.to_dict()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 8
        assert len(data["edges"]) == 7

    def test_round_trip(self, populated_graph: LegalKnowledgeGraph) -> None:
        data = populated_graph.to_dict()
        restored = LegalKnowledgeGraph.from_dict(data)
        restored_data = restored.to_dict()

        assert len(restored_data["nodes"]) == len(data["nodes"])
        assert len(restored_data["edges"]) == len(data["edges"])

    def test_round_trip_preserves_node_data(
        self, populated_graph: LegalKnowledgeGraph
    ) -> None:
        data = populated_graph.to_dict()
        restored = LegalKnowledgeGraph.from_dict(data)
        reg = restored.get_regulation("uu_11_2020")
        assert reg is not None
        assert reg["title"] == "Cipta Kerja"
        assert reg["node_type"] == "law"

    def test_round_trip_preserves_edges(
        self, populated_graph: LegalKnowledgeGraph
    ) -> None:
        data = populated_graph.to_dict()
        restored = LegalKnowledgeGraph.from_dict(data)
        assert restored.graph.has_edge("uu_11_2020", "uu_11_2020_bab_I")
        edge = restored.graph.edges["uu_11_2020", "uu_11_2020_bab_I"]
        assert edge["edge_type"] == EdgeType.CONTAINS.value

    def test_round_trip_preserves_hierarchy(
        self, populated_graph: LegalKnowledgeGraph
    ) -> None:
        data = populated_graph.to_dict()
        restored = LegalKnowledgeGraph.from_dict(data)
        hierarchy = restored.get_hierarchy("uu_11_2020")
        assert len(hierarchy["children"]) == 2

    def test_from_dict_empty(self) -> None:
        kg = LegalKnowledgeGraph.from_dict({"nodes": [], "edges": []})
        assert kg.graph.number_of_nodes() == 0
        assert kg.graph.number_of_edges() == 0


# ── Supersedes Edge Test ─────────────────────────────────────────────────────


class TestSupersedes:
    """Test the SUPERSEDES relationship."""

    def test_supersedes_edge(self) -> None:
        kg = LegalKnowledgeGraph()
        old_law = Law(
            id="uu_5_1999", number=5, year=1999, title="Old Law", about="Old", status="repealed"
        )
        new_law = Law(
            id="uu_13_2003", number=13, year=2003, title="New Law", about="New"
        )
        kg.add_regulation(old_law)
        kg.add_regulation(new_law)
        kg.add_edge("uu_13_2003", "uu_5_1999", EdgeType.SUPERSEDES)

        assert kg.graph.has_edge("uu_13_2003", "uu_5_1999")
        edge = kg.graph.edges["uu_13_2003", "uu_5_1999"]
        assert edge["edge_type"] == EdgeType.SUPERSEDES.value
