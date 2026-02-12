"""
Persistence utilities for the Legal Knowledge Graph.

Provides save/load to JSON for the LegalKnowledgeGraph instance,
enabling startup-time loading without re-ingestion.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .graph import LegalKnowledgeGraph


def save_graph(graph: LegalKnowledgeGraph, filepath: str | Path) -> None:
    """Serialize *graph* to a JSON file at *filepath*."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = graph.to_dict()
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def load_graph(filepath: str | Path) -> LegalKnowledgeGraph:
    """Deserialize a LegalKnowledgeGraph from a JSON file."""
    with open(filepath, encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)
    return LegalKnowledgeGraph.from_dict(data)
