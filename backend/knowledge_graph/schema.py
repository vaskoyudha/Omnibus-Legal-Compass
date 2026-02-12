"""
Pydantic models for Indonesian Legal Knowledge Graph nodes and edges.

Node types map to Indonesian legal document hierarchy:
- UU (Undang-Undang) → Law
- PP (Peraturan Pemerintah) → GovernmentRegulation
- Perpres (Peraturan Presiden) → PresidentialRegulation
- Permen (Peraturan Menteri) → MinisterialRegulation
- Bab → Chapter
- Pasal → Article

ID format: {jenis_dokumen_lower}_{nomor}_{tahun} (e.g., "uu_11_2020")
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# ── Edge Types ───────────────────────────────────────────────────────────────


class EdgeType(str, Enum):
    """Types of relationships between legal document nodes."""

    CONTAINS = "CONTAINS"  # hierarchy: Law → Chapter → Article
    IMPLEMENTS = "IMPLEMENTS"  # PP/Perpres → Law
    AMENDS = "AMENDS"  # Law → Law
    REFERENCES = "REFERENCES"  # Article → Article (cross-reference)
    SUPERSEDES = "SUPERSEDES"  # Law → Law (replacement)


# ── Base Node ────────────────────────────────────────────────────────────────


class BaseNode(BaseModel):
    """Base class for all knowledge graph nodes.

    Subclasses must define a ``node_type`` field with a ``Literal`` default
    to act as a discriminator.
    """

    id: str = Field(..., description="Unique node identifier")


# ── Regulation Nodes ─────────────────────────────────────────────────────────


class Law(BaseNode):
    """Undang-Undang (UU) — primary legislation enacted by parliament."""

    node_type: Literal["law"] = "law"
    number: int = Field(..., description="Regulation number (nomor)")
    year: int = Field(..., description="Year of enactment (tahun)")
    title: str = Field(..., description="Short title (judul)")
    about: str = Field(..., description="Subject matter (tentang)")
    status: Literal["active", "amended", "repealed"] = Field(
        default="active", description="Current legal status"
    )
    enactment_date: str | None = Field(
        default=None, description="Date of enactment (ISO format)"
    )


class GovernmentRegulation(BaseNode):
    """Peraturan Pemerintah (PP) — implementing regulation by government."""

    node_type: Literal["government_regulation"] = "government_regulation"
    number: int = Field(..., description="Regulation number")
    year: int = Field(..., description="Year of issuance")
    title: str = Field(..., description="Short title")
    about: str = Field(..., description="Subject matter")
    parent_law_id: str | None = Field(
        default=None, description="ID of the parent UU this PP implements"
    )


class PresidentialRegulation(BaseNode):
    """Peraturan Presiden (Perpres) — presidential regulation."""

    node_type: Literal["presidential_regulation"] = "presidential_regulation"
    number: int = Field(..., description="Regulation number")
    year: int = Field(..., description="Year of issuance")
    title: str = Field(..., description="Short title")
    about: str = Field(..., description="Subject matter")
    parent_law_id: str | None = Field(
        default=None, description="ID of the parent UU this Perpres implements"
    )


class MinisterialRegulation(BaseNode):
    """Peraturan Menteri (Permen) — ministerial regulation."""

    node_type: Literal["ministerial_regulation"] = "ministerial_regulation"
    number: int = Field(..., description="Regulation number")
    year: int = Field(..., description="Year of issuance")
    title: str = Field(..., description="Short title")
    about: str = Field(..., description="Subject matter")
    issuing_ministry: str | None = Field(
        default=None, description="Name of the issuing ministry"
    )


# ── Structural Nodes ────────────────────────────────────────────────────────


class Chapter(BaseNode):
    """Bab — chapter within a regulation."""

    node_type: Literal["chapter"] = "chapter"
    number: str = Field(
        ..., description="Chapter number in Roman numerals (e.g., 'I', 'II', 'III')"
    )
    title: str | None = Field(default=None, description="Chapter title")
    parent_regulation_id: str = Field(
        ..., description="ID of the parent regulation"
    )


class Article(BaseNode):
    """Pasal — article within a regulation or chapter."""

    node_type: Literal["article"] = "article"
    number: str = Field(..., description="Article number (e.g., '1', '5', '33')")
    content_summary: str | None = Field(
        default=None, description="Brief summary of article content"
    )
    full_text: str = Field(..., description="Full text of the article")
    parent_chapter_id: str | None = Field(
        default=None, description="ID of the parent chapter (if any)"
    )
    parent_regulation_id: str = Field(
        ..., description="ID of the parent regulation"
    )


# ── Union type for all regulation nodes ──────────────────────────────────────

RegulationType = Law | GovernmentRegulation | PresidentialRegulation | MinisterialRegulation
"""Union of all regulation-level node types."""

NodeType = RegulationType | Chapter | Article
"""Union of all node types in the knowledge graph."""
