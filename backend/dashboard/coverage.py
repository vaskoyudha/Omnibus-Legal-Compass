"""
Coverage computation for the Visual Compliance Dashboard.

Cross-references the Knowledge Graph (total articles per regulation/domain)
with a set of indexed article IDs (from Qdrant or another source) to compute
coverage percentages per law and per legal domain.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from knowledge_graph.graph import LegalKnowledgeGraph
from knowledge_graph.schema import EdgeType


# ── Domain classification ────────────────────────────────────────────────────

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "Ketenagakerjaan": [
        "kerja", "tenaga kerja", "ketenagakerjaan", "upah",
        "pemutusan hubungan kerja", "pekerja", "buruh",
    ],
    "Perizinan Usaha": [
        "perizinan", "berusaha", "izin usaha", "oss", "nib",
        "percepatan pelaksanaan berusaha",
    ],
    "Perlindungan Data": [
        "data pribadi", "perlindungan data", "privasi",
    ],
    "Badan Usaha": [
        "perseroan terbatas", "perseroan", "badan usaha",
        "koperasi", "firma", "cv",
    ],
    "Investasi": [
        "penanaman modal", "investasi", "modal asing",
    ],
    "Lingkungan": [
        "lingkungan hidup", "amdal", "dampak lingkungan",
    ],
    "Perpajakan": [
        "pajak", "perpajakan", "cukai", "bea",
    ],
}

DEFAULT_DOMAIN = "Lainnya"


def classify_domain(about: str) -> str:
    """Classify a regulation into a legal domain based on its *about* field."""
    about_lower = about.lower()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in about_lower:
                return domain
    return DEFAULT_DOMAIN


# ── Response models ──────────────────────────────────────────────────────────


class LawCoverage(BaseModel):
    """Coverage metrics for a single law / regulation."""

    regulation_id: str = Field(..., description="Regulation node ID")
    regulation_type: str = Field(..., description="Node type (law, government_regulation, ...)")
    title: str = Field(..., description="Regulation title")
    about: str = Field("", description="Subject matter")
    domain: str = Field(..., description="Legal domain classification")
    total_articles: int = Field(..., ge=0, description="Total articles in KG")
    indexed_articles: int = Field(..., ge=0, description="Articles found in vector index")
    missing_articles: list[str] = Field(
        default_factory=list, description="IDs of articles NOT indexed"
    )
    coverage_percent: float = Field(
        ..., ge=0, le=100, description="Coverage percentage"
    )
    total_chapters: int = Field(0, ge=0, description="Total chapters")


class DomainCoverage(BaseModel):
    """Aggregated coverage for a legal domain."""

    domain: str = Field(..., description="Legal domain name")
    total_articles: int = Field(default=0, ge=0)
    indexed_articles: int = Field(default=0, ge=0)
    coverage_percent: float = Field(default=0, ge=0, le=100)
    regulation_count: int = Field(default=0, ge=0)
    laws: list[LawCoverage] = Field(default_factory=list)


# ── Coverage computer ────────────────────────────────────────────────────────


class CoverageComputer:
    """
    Computes law coverage metrics by cross-referencing the Knowledge Graph
    with a set of indexed article IDs.

    Parameters
    ----------
    graph : LegalKnowledgeGraph
        The populated knowledge graph.
    indexed_article_ids : set[str] | None
        Article node IDs that have been indexed in the vector store.
        If ``None``, defaults to an empty set (0% indexed).
    """

    def __init__(
        self,
        graph: LegalKnowledgeGraph,
        indexed_article_ids: set[str] | None = None,
    ) -> None:
        self._graph = graph
        self._indexed = indexed_article_ids or set()

    # ── Per-law coverage ─────────────────────────────────────────────────

    def compute_law_coverage(self, regulation_id: str) -> LawCoverage | None:
        """
        Compute coverage for a single regulation by traversing its hierarchy.
        Returns ``None`` if the regulation is not in the graph.
        """
        reg = self._graph.get_regulation(regulation_id)
        if reg is None:
            return None

        node_type: str = reg.get("node_type", "unknown")
        title: str = reg.get("title", "")
        about: str = reg.get("about", "")

        articles, chapters = self._collect_descendants(regulation_id)

        total = len(articles)
        indexed = [a for a in articles if a in self._indexed]
        missing = [a for a in articles if a not in self._indexed]
        pct = (len(indexed) / total * 100) if total > 0 else 0.0

        return LawCoverage(
            regulation_id=regulation_id,
            regulation_type=node_type,
            title=title,
            about=about,
            domain=classify_domain(about),
            total_articles=total,
            indexed_articles=len(indexed),
            missing_articles=missing,
            coverage_percent=round(pct, 1),
            total_chapters=len(chapters),
        )

    # ── Full coverage (all regulations) ──────────────────────────────────

    def compute_all_coverage(self) -> list[LawCoverage]:
        """Compute coverage for every regulation node in the graph."""
        regulation_types = {
            "law", "government_regulation",
            "presidential_regulation", "ministerial_regulation",
        }
        results: list[LawCoverage] = []
        for node_id, data in self._graph.graph.nodes(data=True):
            if data.get("node_type") in regulation_types:
                cov = self.compute_law_coverage(node_id)
                if cov is not None:
                    results.append(cov)
        return results

    # ── Domain-grouped coverage ──────────────────────────────────────────

    def compute_domain_coverage(self) -> list[DomainCoverage]:
        """Group per-law coverage by legal domain."""
        all_laws = self.compute_all_coverage()
        domains: dict[str, DomainCoverage] = {}

        for law in all_laws:
            if law.domain not in domains:
                domains[law.domain] = DomainCoverage(
                    domain=law.domain,
                    total_articles=0,
                    indexed_articles=0,
                    coverage_percent=0,
                    regulation_count=0,
                )
            dc = domains[law.domain]
            dc.total_articles += law.total_articles
            dc.indexed_articles += law.indexed_articles
            dc.regulation_count += 1
            dc.laws.append(law)

        # Compute percentages
        for dc in domains.values():
            if dc.total_articles > 0:
                dc.coverage_percent = round(
                    dc.indexed_articles / dc.total_articles * 100, 1
                )

        return sorted(domains.values(), key=lambda d: d.domain)

    # ── Internal helpers ─────────────────────────────────────────────────

    def _collect_descendants(
        self, regulation_id: str
    ) -> tuple[list[str], list[str]]:
        """
        Walk the CONTAINS hierarchy from *regulation_id* and return
        (article_ids, chapter_ids).
        """
        articles: list[str] = []
        chapters: list[str] = []

        for _, child_id, edata in self._graph.graph.out_edges(
            regulation_id, data=True
        ):
            if edata.get("edge_type") != EdgeType.CONTAINS.value:
                continue
            child_data: dict[str, Any] = dict(
                self._graph.graph.nodes[child_id]
            )
            child_type = child_data.get("node_type")

            if child_type == "article":
                articles.append(child_id)
            elif child_type == "chapter":
                chapters.append(child_id)
                # Articles under this chapter
                for _, grandchild_id, ge in self._graph.graph.out_edges(
                    child_id, data=True
                ):
                    if ge.get("edge_type") != EdgeType.CONTAINS.value:
                        continue
                    gc_data = dict(self._graph.graph.nodes[grandchild_id])
                    if gc_data.get("node_type") == "article":
                        articles.append(grandchild_id)

        return articles, chapters
