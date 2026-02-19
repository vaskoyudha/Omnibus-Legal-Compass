"""
Tests for Phase 0 reverse-edge support and Pydantic response models.

Covers:
- EdgeType enum has all 11 values (7 original + 4 reverse)
- ensure_reverse_edges() creates correct reverse edges
- ensure_reverse_edges() is idempotent
- Pydantic response models validate correctly
- normalize_regulation_id() handles various formats
"""

from __future__ import annotations

from backend.knowledge_graph.schema import EdgeType, Law
from backend.knowledge_graph.graph import LegalKnowledgeGraph
from backend.models.regulation import (
    AmendmentTimelineResponse,
    RegulationDetailResponse,
    RegulationListItem,
    RegulationListResponse,
    normalize_regulation_id,
)


# ── EdgeType enum tests ─────────────────────────────────────────────────────


def test_reverse_edge_types_exist() -> None:
    """EdgeType enum has 11 members including 4 new reverse types."""
    assert len(EdgeType) == 11
    assert EdgeType.AMENDED_BY.value == "AMENDED_BY"
    assert EdgeType.REVOKED_BY.value == "REVOKED_BY"
    assert EdgeType.REPLACED_BY.value == "REPLACED_BY"
    assert EdgeType.IMPLEMENTED_BY.value == "IMPLEMENTED_BY"


# ── ensure_reverse_edges tests ──────────────────────────────────────────────


def _make_two_law_graph(
    edge_type: EdgeType,
) -> tuple[LegalKnowledgeGraph, str, str]:
    """Helper: build a KG with two laws and one forward edge."""
    kg = LegalKnowledgeGraph()
    law_a = Law(id="uu_1_2020", number=1, year=2020, title="A", about="A")
    law_b = Law(id="uu_2_2019", number=2, year=2019, title="B", about="B")
    kg.add_regulation(law_a)
    kg.add_regulation(law_b)
    kg.add_edge("uu_1_2020", "uu_2_2019", edge_type)
    return kg, "uu_1_2020", "uu_2_2019"


def test_ensure_reverse_edges_amends() -> None:
    """AMENDS(A→B) produces AMENDED_BY(B→A)."""
    kg, a, b = _make_two_law_graph(EdgeType.AMENDS)
    added = kg.ensure_reverse_edges()
    assert added == 1
    assert kg._graph.has_edge(b, a)
    assert kg._graph[b][a].get("edge_type") == EdgeType.AMENDED_BY.value


def test_ensure_reverse_edges_revokes() -> None:
    """REVOKES(A→B) produces REVOKED_BY(B→A)."""
    kg, a, b = _make_two_law_graph(EdgeType.REVOKES)
    added = kg.ensure_reverse_edges()
    assert added == 1
    assert kg._graph.has_edge(b, a)
    assert kg._graph[b][a].get("edge_type") == EdgeType.REVOKED_BY.value


def test_ensure_reverse_edges_replaces() -> None:
    """REPLACES(A→B) produces REPLACED_BY(B→A)."""
    kg, a, b = _make_two_law_graph(EdgeType.REPLACES)
    added = kg.ensure_reverse_edges()
    assert added == 1
    assert kg._graph.has_edge(b, a)
    assert kg._graph[b][a].get("edge_type") == EdgeType.REPLACED_BY.value


def test_ensure_reverse_edges_implements() -> None:
    """IMPLEMENTS(A→B) produces IMPLEMENTED_BY(B→A)."""
    kg, a, b = _make_two_law_graph(EdgeType.IMPLEMENTS)
    added = kg.ensure_reverse_edges()
    assert added == 1
    assert kg._graph.has_edge(b, a)
    assert kg._graph[b][a].get("edge_type") == EdgeType.IMPLEMENTED_BY.value


def test_ensure_reverse_edges_idempotent() -> None:
    """Second call to ensure_reverse_edges() returns 0."""
    kg, _, _ = _make_two_law_graph(EdgeType.AMENDS)
    kg.ensure_reverse_edges()
    second = kg.ensure_reverse_edges()
    assert second == 0


def test_ensure_reverse_edges_no_duplicate() -> None:
    """Edge count stays the same after a second ensure_reverse_edges() call."""
    kg, _, _ = _make_two_law_graph(EdgeType.AMENDS)
    kg.ensure_reverse_edges()
    edge_count_after_first = kg._graph.number_of_edges()
    kg.ensure_reverse_edges()
    assert kg._graph.number_of_edges() == edge_count_after_first


# ── Pydantic response model tests ──────────────────────────────────────────


def test_regulation_list_item_model() -> None:
    """RegulationListItem validates with required fields."""
    item = RegulationListItem(
        id="uu_11_2020",
        node_type="law",
        number=11,
        year=2020,
        title="T",
        about="A",
    )
    assert item.id == "uu_11_2020"
    assert item.status == "active"
    assert item.chapter_count == 0


def test_regulation_list_response_model() -> None:
    """RegulationListResponse validates with empty items."""
    resp = RegulationListResponse(
        items=[], total=0, page=1, page_size=20, total_pages=0
    )
    assert resp.total == 0
    assert resp.page == 1
    assert resp.items == []


def test_regulation_detail_response_model() -> None:
    """Minimal RegulationDetailResponse validates."""
    detail = RegulationDetailResponse(
        id="uu_11_2020",
        node_type="law",
        number=11,
        year=2020,
        title="Cipta Kerja",
        about="Penciptaan Lapangan Kerja",
    )
    assert detail.id == "uu_11_2020"
    assert detail.chapters == []
    assert detail.amendments == []
    assert detail.parent_law is None


def test_amendment_timeline_model() -> None:
    """AmendmentTimelineResponse validates with empty entries."""
    timeline = AmendmentTimelineResponse(
        regulation_id="x", regulation_title="X", entries=[]
    )
    assert timeline.regulation_id == "x"
    assert timeline.entries == []


# ── normalize_regulation_id tests ───────────────────────────────────────────


def test_normalize_regulation_id_lowercase() -> None:
    """Already-normalized ID passes through."""
    assert normalize_regulation_id("uu_11_2020") == "uu_11_2020"


def test_normalize_regulation_id_uppercase() -> None:
    """Uppercase ID is lowercased."""
    assert normalize_regulation_id("UU_11_2020") == "uu_11_2020"


def test_normalize_regulation_id_hyphens() -> None:
    """Hyphen-separated ID is converted to underscores."""
    assert normalize_regulation_id("uu-11-2020") == "uu_11_2020"


def test_normalize_regulation_id_verbose() -> None:
    """Verbose Indonesian citation format is normalized."""
    assert normalize_regulation_id("UU No. 11 Tahun 2020") == "uu_11_2020"
