"""
Legal Knowledge Graph backed by NetworkX DiGraph.

Provides methods for building, querying, and serializing a directed graph
of Indonesian legal documents and their relationships.
"""

from __future__ import annotations

import time
from collections import deque
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
        # Merge semantics: if an edge already exists between source and
        # target, preserve existing edge types and metadata instead of
        # overwriting. This allows multiple relation types (e.g.
        # IMPLEMENTS and REFERENCES) to coexist on the same node pair.
        existing = None
        try:
            existing = self._graph.get_edge_data(source_id, target_id)
        except Exception:
            existing = None

        if existing:
            # Normalize existing edge types into a set
            existing_types = set()
            if "edge_types" in existing and isinstance(existing["edge_types"], (list, set)):
                existing_types.update(existing["edge_types"])
            elif "edge_type" in existing:
                existing_types.add(existing["edge_type"])

            existing_types.add(edge_type.value)

            # Merge metadata by storing per-edge-type metadata map
            metadata_map = {}
            if "metadata_map" in existing and isinstance(existing["metadata_map"], dict):
                metadata_map.update(existing["metadata_map"])
            # Preserve older top-level metadata if present under key 'metadata'
            if "metadata" in existing and existing.get("metadata"):
                # assign to a fallback key if we can't determine its type
                metadata_map.setdefault("_existing", existing.get("metadata"))

            if metadata:
                metadata_map.setdefault(edge_type.value, metadata)

            # Update the edge attributes in-place
            attrs = {
                "edge_types": sorted(existing_types),
                "edge_type": sorted(existing_types)[-1],
                "metadata_map": metadata_map,
            }
            # Keep convenience top-level metadata if only one type present
            if len(existing_types) == 1:
                only = next(iter(existing_types))
                attrs["metadata"] = metadata_map.get(only)

            self._graph.add_edge(source_id, target_id, **attrs)
        else:
            attrs: dict[str, Any] = {"edge_type": edge_type.value, "edge_types": [edge_type.value]}
            if metadata:
                attrs["metadata"] = metadata
                attrs["metadata_map"] = {edge_type.value: metadata}
            else:
                attrs["metadata_map"] = {}
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

    # ── Regulation Library query methods ─────────────────────────────────

    def get_regulation_list(
        self,
        node_type: str | None = None,
        status: str | None = None,
        year: int | None = None,
        search_query: str | None = None,
        sort_by: str = "year",
        sort_order: str = "desc",
    ) -> list[dict[str, Any]]:
        """Get regulation list with aggregated metadata counts.

        Returns list of regulation dicts enriched with:
        - chapter_count: direct CONTAINS children that are chapters
        - article_count: total CONTAINS grandchildren that are articles
        - amendment_count: AMENDS+AMENDED_BY+REVOKES+REVOKED_BY+REPLACES+REPLACED_BY edges
        - cross_reference_count: REFERENCES edges on child articles
        """
        REGULATION_TYPES = {
            "law", "government_regulation", "presidential_regulation", "ministerial_regulation"
        }
        AMENDMENT_EDGE_TYPES = {
            EdgeType.AMENDS.value, EdgeType.AMENDED_BY.value,
            EdgeType.REVOKES.value, EdgeType.REVOKED_BY.value,
            EdgeType.REPLACES.value, EdgeType.REPLACED_BY.value,
        }

        results: list[dict[str, Any]] = []
        for node_id, data in self._graph.nodes(data=True):
            nt = data.get("node_type", "")
            if nt not in REGULATION_TYPES:
                continue
            if node_type and nt != node_type:
                continue
            if status and data.get("status") != status:
                continue
            if year and data.get("year") != year:
                continue
            if search_query:
                sq = search_query.lower()
                searchable = " ".join(
                    str(data.get(f, "")) for f in ("title", "about")
                ).lower()
                if sq not in searchable:
                    continue

            # Count chapters and articles via CONTAINS edges
            chapter_count = 0
            article_count = 0
            cross_reference_count = 0
            for _, child_id, edata in self._graph.out_edges(node_id, data=True):
                if edata.get("edge_type") == EdgeType.CONTAINS.value:
                    child_data = self._graph.nodes.get(child_id, {})
                    if child_data.get("node_type") == "chapter":
                        chapter_count += 1
                        for _, grandchild_id, ge in self._graph.out_edges(child_id, data=True):
                            if ge.get("edge_type") == EdgeType.CONTAINS.value:
                                article_count += 1
                                # Count REFERENCES edges
                                for _, _, re_data in self._graph.out_edges(grandchild_id, data=True):
                                    if re_data.get("edge_type") == EdgeType.REFERENCES.value:
                                        cross_reference_count += 1
                    elif child_data.get("node_type") == "article":
                        article_count += 1
                        for _, _, re_data in self._graph.out_edges(child_id, data=True):
                            if re_data.get("edge_type") == EdgeType.REFERENCES.value:
                                cross_reference_count += 1

            # Count amendment edges (both out and in)
            amendment_count = 0
            for _, _, edata in self._graph.out_edges(node_id, data=True):
                if edata.get("edge_type") in AMENDMENT_EDGE_TYPES:
                    amendment_count += 1
            for _, _, edata in self._graph.in_edges(node_id, data=True):
                if edata.get("edge_type") in AMENDMENT_EDGE_TYPES:
                    amendment_count += 1

            reg = dict(data)
            reg["chapter_count"] = chapter_count
            reg["article_count"] = article_count
            reg["amendment_count"] = amendment_count
            reg["cross_reference_count"] = cross_reference_count
            reg["indexed_chunk_count"] = 0  # filled in by API layer from Qdrant
            results.append(reg)

        # Sort
        reverse = sort_order == "desc"
        if sort_by in ("year", "number"):
            results.sort(key=lambda r: (r.get(sort_by) or 0), reverse=reverse)
        elif sort_by == "title":
            results.sort(key=lambda r: str(r.get("title") or "").lower(), reverse=reverse)
        elif sort_by == "article_count":
            results.sort(key=lambda r: r.get("article_count", 0), reverse=reverse)

        return results

    def get_regulation_detail(self, regulation_id: str) -> dict[str, Any] | None:
        """Get full regulation detail with chapter/article hierarchy and relationships."""
        if regulation_id not in self._graph:
            return None
        data = dict(self._graph.nodes[regulation_id])
        nt = data.get("node_type", "")
        REGULATION_TYPES = {
            "law", "government_regulation", "presidential_regulation", "ministerial_regulation"
        }
        if nt not in REGULATION_TYPES:
            return None

        # Build chapter/article hierarchy
        chapters: list[dict[str, Any]] = []
        article_ids_seen: set[str] = set()
        cross_reference_count = 0

        for _, child_id, edata in self._graph.out_edges(regulation_id, data=True):
            if edata.get("edge_type") != EdgeType.CONTAINS.value:
                continue
            child_data = dict(self._graph.nodes.get(child_id, {}))
            if child_data.get("node_type") == "chapter":
                articles: list[dict[str, Any]] = []
                for _, grandchild_id, ge in self._graph.out_edges(child_id, data=True):
                    if ge.get("edge_type") != EdgeType.CONTAINS.value:
                        continue
                    gdata = dict(self._graph.nodes.get(grandchild_id, {}))
                    if gdata.get("node_type") == "article":
                        cross_refs = [
                            tgt for _, tgt, re_data in self._graph.out_edges(grandchild_id, data=True)
                            if re_data.get("edge_type") == EdgeType.REFERENCES.value
                        ]
                        cross_reference_count += len(cross_refs)
                        gdata["cross_references"] = cross_refs
                        articles.append(gdata)
                        article_ids_seen.add(grandchild_id)
                child_data["articles"] = articles
                chapters.append(child_data)
            elif child_data.get("node_type") == "article":
                # Articles directly under regulation (no chapter)
                cross_refs = [
                    tgt for _, tgt, re_data in self._graph.out_edges(child_id, data=True)
                    if re_data.get("edge_type") == EdgeType.REFERENCES.value
                ]
                cross_reference_count += len(cross_refs)
                child_data["cross_references"] = cross_refs
                child_data["articles"] = []
                article_ids_seen.add(child_id)

        # Sort chapters by number (Roman numeral → integer attempt)
        def _chapter_sort_key(c: dict[str, Any]) -> int:
            num = str(c.get("number", ""))
            roman = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7,
                     "VIII": 8, "IX": 9, "X": 10, "XI": 11, "XII": 12, "XIII": 13,
                     "XIV": 14, "XV": 15, "XVI": 16, "XVII": 17, "XVIII": 18,
                     "XIX": 19, "XX": 20}
            if num.upper() in roman:
                return roman[num.upper()]
            try:
                return int(num)
            except ValueError:
                return 999
        chapters.sort(key=_chapter_sort_key)

        # Get amendments (both directions)
        AMENDMENT_EDGE_TYPES = {
            EdgeType.AMENDS.value, EdgeType.AMENDED_BY.value,
            EdgeType.REVOKES.value, EdgeType.REVOKED_BY.value,
            EdgeType.REPLACES.value, EdgeType.REPLACED_BY.value,
        }
        amendments: list[dict[str, Any]] = []
        for _, tgt_id, edata in self._graph.out_edges(regulation_id, data=True):
            et = edata.get("edge_type", "")
            if et in AMENDMENT_EDGE_TYPES:
                tgt_data = dict(self._graph.nodes.get(tgt_id, {}))
                amendments.append({
                    "regulation_id": tgt_id,
                    "regulation_title": tgt_data.get("title", ""),
                    "year": tgt_data.get("year", 0),
                    "direction": "forward",
                    "edge_type": et,
                })
        for src_id, _, edata in self._graph.in_edges(regulation_id, data=True):
            et = edata.get("edge_type", "")
            if et in AMENDMENT_EDGE_TYPES:
                src_data = dict(self._graph.nodes.get(src_id, {}))
                amendments.append({
                    "regulation_id": src_id,
                    "regulation_title": src_data.get("title", ""),
                    "year": src_data.get("year", 0),
                    "direction": "backward",
                    "edge_type": et,
                })

        # Get implementing regulations (PP/Perpres that IMPLEMENT this law)
        implementing: list[dict[str, Any]] = []
        for src_id, _, edata in self._graph.in_edges(regulation_id, data=True):
            if edata.get("edge_type") == EdgeType.IMPLEMENTS.value:
                src_data = dict(self._graph.nodes.get(src_id, {}))
                src_data["chapter_count"] = 0
                src_data["article_count"] = 0
                src_data["amendment_count"] = 0
                src_data["cross_reference_count"] = 0
                src_data["indexed_chunk_count"] = 0
                implementing.append(src_data)

        # Get parent law (for PP/Perpres: what law does this implement?)
        parent_law: dict[str, Any] | None = None
        for _, tgt_id, edata in self._graph.out_edges(regulation_id, data=True):
            if edata.get("edge_type") == EdgeType.IMPLEMENTS.value:
                tgt_data = dict(self._graph.nodes.get(tgt_id, {}))
                tgt_data["chapter_count"] = 0
                tgt_data["article_count"] = 0
                tgt_data["amendment_count"] = 0
                tgt_data["cross_reference_count"] = 0
                tgt_data["indexed_chunk_count"] = 0
                parent_law = tgt_data
                break

        result = dict(data)
        result["chapters"] = chapters
        result["amendments"] = amendments
        result["implementing_regulations"] = implementing
        result["parent_law"] = parent_law
        result["cross_reference_count"] = cross_reference_count
        result["indexed_chunk_count"] = 0  # filled by API layer
        return result

    def get_amendment_timeline(self, regulation_id: str) -> list[dict[str, Any]]:
        """Get chronological amendment/revocation timeline for a regulation."""
        if regulation_id not in self._graph:
            return []
        reg_data = dict(self._graph.nodes[regulation_id])

        TIMELINE_EDGE_TYPES = {
            EdgeType.AMENDS.value, EdgeType.AMENDED_BY.value,
            EdgeType.REVOKES.value, EdgeType.REVOKED_BY.value,
            EdgeType.REPLACES.value, EdgeType.REPLACED_BY.value,
            EdgeType.SUPERSEDES.value,
        }
        entries: list[dict[str, Any]] = []

        for _, tgt_id, edata in self._graph.out_edges(regulation_id, data=True):
            et = edata.get("edge_type", "")
            if et not in TIMELINE_EDGE_TYPES:
                continue
            tgt_data = dict(self._graph.nodes.get(tgt_id, {}))
            entries.append({
                "regulation_id": regulation_id,
                "regulation_title": reg_data.get("title", ""),
                "year": reg_data.get("year", 0),
                "number": reg_data.get("number", 0),
                "edge_type": et,
                "direction": "forward",
                "target_id": tgt_id,
                "target_title": tgt_data.get("title", ""),
            })

        for src_id, _, edata in self._graph.in_edges(regulation_id, data=True):
            et = edata.get("edge_type", "")
            if et not in TIMELINE_EDGE_TYPES:
                continue
            src_data = dict(self._graph.nodes.get(src_id, {}))
            entries.append({
                "regulation_id": src_id,
                "regulation_title": src_data.get("title", ""),
                "year": src_data.get("year", 0),
                "number": src_data.get("number", 0),
                "edge_type": et,
                "direction": "backward",
                "target_id": regulation_id,
                "target_title": reg_data.get("title", ""),
            })

        entries.sort(key=lambda e: e.get("year", 0))
        return entries

    def get_article_cross_references(self, article_id: str) -> dict[str, Any]:
        """Get both outgoing and incoming REFERENCES for an article."""
        references_to: list[dict[str, Any]] = []
        referenced_by: list[dict[str, Any]] = []

        for _, tgt_id, edata in self._graph.out_edges(article_id, data=True):
            if edata.get("edge_type") == EdgeType.REFERENCES.value:
                references_to.append(dict(self._graph.nodes.get(tgt_id, {})))

        for src_id, _, edata in self._graph.in_edges(article_id, data=True):
            if edata.get("edge_type") == EdgeType.REFERENCES.value:
                referenced_by.append(dict(self._graph.nodes.get(src_id, {})))

        return {"references_to": references_to, "referenced_by": referenced_by}

    # ── Regulation-level edge types for multi-hop traversal ──────────────
    _REGULATION_EDGE_TYPES: frozenset[str] = frozenset({
        EdgeType.IMPLEMENTS.value,
        EdgeType.AMENDS.value,
        EdgeType.REFERENCES.value,
        EdgeType.SUPERSEDES.value,
    })

    # Node types that represent regulations (not structural children)
    _REGULATION_NODE_TYPES: frozenset[str] = frozenset({
        "law",
        "government_regulation",
        "presidential_regulation",
        "ministerial_regulation",
    })

    def get_related_regulations(
        self,
        reg_id: str,
        max_hops: int = 2,
        timeout_ms: int = 500,
    ) -> list[dict[str, Any]]:
        """Return regulations related to *reg_id* via BFS traversal.

        Follows IMPLEMENTS, AMENDS, REFERENCES, and SUPERSEDES edges
        (both directions) up to *max_hops* hops.  Stops early when
        *timeout_ms* milliseconds have elapsed.

        Each returned dict includes the node data plus:
        - ``_hop``: number of hops from *reg_id*
        - ``_path``: list of ``(edge_type, node_id)`` tuples from source

        Args:
            reg_id: Starting regulation node ID.
            max_hops: Maximum BFS depth (default 2).
            timeout_ms: Timeout in milliseconds (default 500).

        Returns:
            List of related regulation node dicts (excludes the source).
        """
        if reg_id not in self._graph:
            return []

        deadline = time.monotonic() + timeout_ms / 1000.0

        # BFS state: (node_id, hop_count, path)
        queue: deque[tuple[str, int, list[tuple[str, str]]]] = deque()
        queue.append((reg_id, 0, []))
        visited: set[str] = {reg_id}
        results: list[dict[str, Any]] = []

        while queue:
            if time.monotonic() > deadline:
                break

            current_id, hop, path = queue.popleft()

            if hop >= max_hops:
                continue

            # Traverse outgoing edges
            for _, neighbor_id, edata in self._graph.out_edges(current_id, data=True):
                if time.monotonic() > deadline:
                    break
                edge_type = edata.get("edge_type", "")
                if edge_type not in self._REGULATION_EDGE_TYPES:
                    continue
                if neighbor_id in visited:
                    continue

                node_data = dict(self._graph.nodes[neighbor_id])
                node_type = node_data.get("node_type", "")

                # Only include regulation-level nodes
                if node_type not in self._REGULATION_NODE_TYPES:
                    continue

                visited.add(neighbor_id)
                new_path = path + [(edge_type, neighbor_id)]
                results.append({
                    **node_data,
                    "_hop": hop + 1,
                    "_path": new_path,
                })
                queue.append((neighbor_id, hop + 1, new_path))

            # Traverse incoming edges (reverse direction)
            for neighbor_id, _, edata in self._graph.in_edges(current_id, data=True):
                if time.monotonic() > deadline:
                    break
                edge_type = edata.get("edge_type", "")
                if edge_type not in self._REGULATION_EDGE_TYPES:
                    continue
                if neighbor_id in visited:
                    continue

                node_data = dict(self._graph.nodes[neighbor_id])
                node_type = node_data.get("node_type", "")

                if node_type not in self._REGULATION_NODE_TYPES:
                    continue

                visited.add(neighbor_id)
                new_path = path + [(f"~{edge_type}", neighbor_id)]
                results.append({
                    **node_data,
                    "_hop": hop + 1,
                    "_path": new_path,
                })
                queue.append((neighbor_id, hop + 1, new_path))

        return results

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
            # Count each declared edge_type and any additional edge_types
            et = data.get("edge_type")
            if et:
                edge_counts[et] = edge_counts.get(et, 0) + 1
            ets = data.get("edge_types")
            if isinstance(ets, (list, set)):
                for t in ets:
                    edge_counts[t] = edge_counts.get(t, 0) + 1

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

    def ensure_reverse_edges(self) -> int:
        """Create reverse edges for all directional relationships.

        For every AMENDS(A→B) edge, ensures AMENDED_BY(B→A) exists.
        Same for REVOKES/REPLACES/IMPLEMENTS.

        Returns count of new reverse edges added.
        """
        REVERSE_MAP = {
            EdgeType.AMENDS.value: EdgeType.AMENDED_BY.value,
            EdgeType.REVOKES.value: EdgeType.REVOKED_BY.value,
            EdgeType.REPLACES.value: EdgeType.REPLACED_BY.value,
            EdgeType.IMPLEMENTS.value: EdgeType.IMPLEMENTED_BY.value,
        }
        added = 0
        for src, tgt, data in list(self._graph.edges(data=True)):
            edge_type = data.get("edge_type")
            if edge_type in REVERSE_MAP:
                reverse_type = REVERSE_MAP[edge_type]
                if not self._graph.has_edge(tgt, src):
                    self._graph.add_edge(tgt, src, edge_type=reverse_type)
                    added += 1
        return added

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LegalKnowledgeGraph:
        """Deserialize a graph from a dict produced by :meth:`to_dict`."""
        kg = cls()
        for node in data.get("nodes", []):
            node_data = {k: v for k, v in node.items()}
            node_id = node_data.get("id", "")
            # Keep 'id' in attributes so queries return it
            kg._graph.add_node(node_id, **node_data)

        for edge in data.get("edges", []):
            edge_data = {k: v for k, v in edge.items()}
            source = edge_data.pop("source")
            target = edge_data.pop("target")
            kg._graph.add_edge(source, target, **edge_data)

        kg.ensure_reverse_edges()
        return kg
