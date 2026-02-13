"""
Aggregate metrics for the dashboard stats endpoint.

Combines Knowledge Graph statistics with coverage data to produce
a single summary for the frontend stats cards.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from knowledge_graph.graph import LegalKnowledgeGraph

from .coverage import CoverageComputer, DomainCoverage


class DashboardStats(BaseModel):
    """Aggregate dashboard statistics."""

    overall_coverage_percent: float = Field(
        ..., ge=0, le=100, description="Overall coverage across all articles"
    )
    total_regulations: int = Field(0, ge=0, description="Total regulation nodes")
    total_articles: int = Field(0, ge=0, description="Total article nodes")
    total_chapters: int = Field(0, ge=0, description="Total chapter nodes")
    indexed_articles: int = Field(0, ge=0, description="Articles in vector index")
    total_edges: int = Field(0, ge=0, description="Total edges in graph")
    domain_count: int = Field(0, ge=0, description="Number of legal domains")
    most_covered_domain: str | None = Field(
        None, description="Domain with highest coverage"
    )
    least_covered_domain: str | None = Field(
        None, description="Domain with lowest coverage"
    )
    last_updated: str = Field(
        ..., description="ISO timestamp of stats computation"
    )


class MetricsAggregator:
    """
    Aggregates coverage data and graph statistics into a single
    :class:`DashboardStats` payload.
    """

    def __init__(
        self,
        graph: LegalKnowledgeGraph,
        coverage_computer: CoverageComputer,
    ) -> None:
        self._graph = graph
        self._coverage = coverage_computer

    def compute_stats(self) -> DashboardStats:
        """Compute aggregate dashboard statistics."""
        graph_stats = self._graph.get_stats()
        domains = self._coverage.compute_domain_coverage()

        total_articles = sum(d.total_articles for d in domains)
        indexed_articles = sum(d.indexed_articles for d in domains)
        overall_pct = (
            round(indexed_articles / total_articles * 100, 1)
            if total_articles > 0
            else 0.0
        )

        most_covered = self._find_extreme(domains, highest=True)
        least_covered = self._find_extreme(domains, highest=False)

        reg_types = {
            "law", "government_regulation",
            "presidential_regulation", "ministerial_regulation",
        }
        total_regs = sum(
            graph_stats.get("nodes_by_type", {}).get(t, 0) for t in reg_types
        )

        return DashboardStats(
            overall_coverage_percent=overall_pct,
            total_regulations=total_regs,
            total_articles=graph_stats.get("nodes_by_type", {}).get("article", 0),
            total_chapters=graph_stats.get("nodes_by_type", {}).get("chapter", 0),
            indexed_articles=indexed_articles,
            total_edges=graph_stats.get("total_edges", 0),
            domain_count=len(domains),
            most_covered_domain=most_covered,
            least_covered_domain=least_covered,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def _find_extreme(
        domains: list[DomainCoverage], *, highest: bool
    ) -> str | None:
        """Return the domain name with the highest/lowest coverage."""
        if not domains:
            return None
        # Only consider domains with at least one article
        candidates = [d for d in domains if d.total_articles > 0]
        if not candidates:
            return None
        key = max if highest else min
        return key(candidates, key=lambda d: d.coverage_percent).domain
