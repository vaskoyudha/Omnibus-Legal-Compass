"""
Knowledge Graph module for Indonesian legal documents.

Provides Pydantic models for legal document nodes (UU, PP, Perpres, Permen,
Bab, Pasal) and a NetworkX-backed directed graph for traversing legal
hierarchies and cross-references.
"""

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
from .graph import LegalKnowledgeGraph
from .persistence import load_graph, save_graph
from .ingest import ingest_from_json, ingest_all

__all__ = [
    "Law",
    "GovernmentRegulation",
    "PresidentialRegulation",
    "MinisterialRegulation",
    "Chapter",
    "Article",
    "EdgeType",
    "LegalKnowledgeGraph",
    "BaseNode",
    "NodeType",
    "RegulationType",
    "load_graph",
    "save_graph",
    "ingest_from_json",
    "ingest_all",
]
