"""
Legal Knowledge Graph backed by NetworkX DiGraph.

Provides methods for building, querying, and serializing a directed graph
of Indonesian legal documents and their relationships.
"""

from __future__ import annotations

from typing import Any

import networkx as nx

from .schema import (
    Article,
    BaseNode,
    Chapter,
    EdgeType,
    GovernmentRegulation,
    Law,
    MinisterialRegulation,
    NodeType,
    PresidentialRegulation,
    RegulationType,
)


class LegalKnowledgeGraph:
    """
    Knowledge graph for Indonesian legal documents.

    Wraps a ``networkx.DiGraph`` and stores Pydantic node models as
    node attributes.  Edges carry an ``edge_type`` (:class:`EdgeType`)
    plus optional metadata.
    """

    def __init__(self) -> None:
        self._graph: nx.DiGraph[str] = nx.DiGraph()  # pyright: ignore[reportMissingTypeArgument]

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def graph(self) -> nx.DiGraph[str]:  # pyright: ignore[reportMissingTypeArgument]
        """Return the underlying NetworkX DiGraph."""
        return self._graph

    # ── Add operations ───────────────────────────────────────────────────

    def _add_node(self, node: BaseNode) -> None:
        """Store a Pydantic node in the graph."""
        self._graph.add_node(node.id, **node.model_dump())

    def add_regulation(self, reg: RegulationType) -> None:
        """Add a regulation node (Law, PP, Perpres, or Permen)."""
        self._add_node(reg)

    def add_chapter(self, chapter: Chapter) -> None:
        """Add a chapter node and a CONTAINS edge from its parent regulation."""
        self._add_node(chapter)
        self.add_edge(
            chapter.parent_regulation_id,
            chapter.id,
            EdgeType.CONTAINS,
        )

    def add_article(self, article: Article) -> None:
        """Add an article node and a CONTAINS edge from its parent (chapter or regulation)."""
        self._add_node(article)
        parent_id = article.parent_chapter_id or article.parent_regulation_id
        self.add_edge(parent_id, article.id, EdgeType.CONTAINS)

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a typed, directed edge between two nodes."""
        attrs: dict[str, Any] = {"edge_type": edge_type.value}
        if metadata:
            attrs["metadata"] = metadata
        self._graph.add_edge(source_id, target_id, **attrs)

    # ── Query operations ─────────────────────────────────────────────────

    def get_regulation(self, reg_id: str) -> dict[str, Any] | None:
        """Return regulation node data by ID, or ``None`` if not found."""
        if reg_id not in self._graph:
            return None
        return dict(self._graph.nodes[reg_id])

    def get_hierarchy(self, regulation_id: str) -> dict[str, Any]:
        """
        Return the full hierarchy tree rooted at *regulation_id*.

        Returns a dict with the regulation data plus ``children`` — a list
        of chapters, each with their own ``children`` articles.
        """
        reg_data = self.get_regulation(regulation_id)
        if reg_data is None:
            return {}

        result: dict[str, Any] = {**reg_data, "children": []}

        # Direct children via CONTAINS edges
        for _, child_id, edata in self._graph.out_edges(regulation_id, data=True):
            if edata.get("edge_type") != EdgeType.CONTAINS.value:
                continue
            child_data = dict(self._graph.nodes[child_id])
            child_node: dict[str, Any] = {**child_data, "children": []}

            # Grandchildren (articles under chapters)
            for _, grandchild_id, ge in self._graph.out_edges(child_id, data=True):
                if ge.get("edge_type") != EdgeType.CONTAINS.value:
                    continue
                grandchild_data = dict(self._graph.nodes[grandchild_id])
                child_node["children"].append(grandchild_data)

            result["children"].append(child_node)

        return result

    def get_references(self, article_id: str) -> list[dict[str, Any]]:
        """Return nodes that the given article references or is referenced by."""
        refs: list[dict[str, Any]] = []
        # Outgoing REFERENCES
        for _, target_id, edata in self._graph.out_edges(article_id, data=True):
            if edata.get("edge_type") == EdgeType.REFERENCES.value:
                refs.append(dict(self._graph.nodes[target_id]))
        # Incoming REFERENCES
        for source_id, _, edata in self._graph.in_edges(article_id, data=True):
            if edata.get("edge_type") == EdgeType.REFERENCES.value:
                refs.append(dict(self._graph.nodes[source_id]))
        return refs

    def get_amendments(self, law_id: str) -> list[dict[str, Any]]:
        """Return the amendment chain for a given law (both directions)."""
        amendments: list[dict[str, Any]] = []
        # Laws that amend this law (incoming AMENDS)
        for source_id, _, edata in self._graph.in_edges(law_id, data=True):
            if edata.get("edge_type") == EdgeType.AMENDS.value:
                amendments.append(dict(self._graph.nodes[source_id]))
        # Laws that this law amends (outgoing AMENDS)
        for _, target_id, edata in self._graph.out_edges(law_id, data=True):
            if edata.get("edge_type") == EdgeType.AMENDS.value:
                amendments.append(dict(self._graph.nodes[target_id]))
        return amendments

    def get_implementing_regulations(self, law_id: str) -> list[dict[str, Any]]:
        """Return PP/Perpres that implement the given law."""
        impls: list[dict[str, Any]] = []
        for source_id, _, edata in self._graph.in_edges(law_id, data=True):
            if edata.get("edge_type") == EdgeType.IMPLEMENTS.value:
                impls.append(dict(self._graph.nodes[source_id]))
        return impls

    def search_nodes(
        self, query: str, node_type: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Simple text search across node titles/about fields.

        Matches *query* (case-insensitive) against ``title``, ``about``,
        ``full_text``, or ``content_summary`` attributes.
        """
        query_lower = query.lower()
        results: list[dict[str, Any]] = []
        for _, data in self._graph.nodes(data=True):
            if node_type and data.get("node_type") != node_type:
                continue
            searchable = " ".join(
                str(data.get(f, ""))
                for f in ("title", "about", "full_text", "content_summary")
            ).lower()
            if query_lower in searchable:
                results.append(dict(data))
        return results

    def get_stats(self) -> dict[str, Any]:
        """Return node and edge counts grouped by type."""
        node_counts: dict[str, int] = {}
        for _, data in self._graph.nodes(data=True):
            nt = data.get("node_type", "unknown")
            node_counts[nt] = node_counts.get(nt, 0) + 1

        edge_counts: dict[str, int] = {}
        for _, _, data in self._graph.edges(data=True):
            et = data.get("edge_type", "unknown")
            edge_counts[et] = edge_counts.get(et, 0) + 1

        return {
            "total_nodes": self._graph.number_of_nodes(),
            "total_edges": self._graph.number_of_edges(),
            "nodes_by_type": node_counts,
            "edges_by_type": edge_counts,
        }

    # ── Serialization ────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serialize the entire graph to a JSON-compatible dict."""
        nodes: list[dict[str, Any]] = []
        for node_id, data in self._graph.nodes(data=True):
            nodes.append({"id": node_id, **data})

        edges: list[dict[str, Any]] = []
        for source, target, data in self._graph.edges(data=True):
            edges.append({"source": source, "target": target, **data})

        return {"nodes": nodes, "edges": edges}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LegalKnowledgeGraph:
        """Deserialize a graph from a dict produced by :meth:`to_dict`."""
        kg = cls()
        for node in data.get("nodes", []):
            node_data = {k: v for k, v in node.items()}
            node_id = node_data.pop("id")
            kg._graph.add_node(node_id, **node_data)

        for edge in data.get("edges", []):
            edge_data = {k: v for k, v in edge.items()}
            source = edge_data.pop("source")
            target = edge_data.pop("target")
            kg._graph.add_edge(source, target, **edge_data)

        return kg
