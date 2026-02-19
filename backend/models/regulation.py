"""Pydantic response models for the Regulation Library API endpoints."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field


def normalize_regulation_id(citation_id: str) -> str:
    """Normalize various citation_id formats to KG node ID format.

    Handles: 'UU_11_2020', 'uu-11-2020', 'UU No. 11 Tahun 2020', 'uu_11_2020'
    Returns: 'uu_11_2020' (lowercase, underscore-separated)
    """
    # Already normalized
    if re.match(r'^[a-z_]+_\d+_\d{4}$', citation_id):
        return citation_id
    # Normalize: lowercase, replace hyphens/spaces with underscores, strip text
    normalized = citation_id.lower().strip()
    normalized = re.sub(r'[\s\-]+', '_', normalized)
    normalized = re.sub(r'no\.?\s*', '', normalized)
    normalized = re.sub(r'tahun\s*', '', normalized)
    normalized = re.sub(r'_+', '_', normalized).strip('_')
    return normalized


class RegulationListItem(BaseModel):
    """Single regulation in the library listing."""

    id: str
    node_type: str
    number: int
    year: int
    title: str
    about: str
    status: str = "active"
    chapter_count: int = 0
    article_count: int = 0
    indexed_chunk_count: int = 0
    amendment_count: int = 0
    cross_reference_count: int = 0


class RegulationListResponse(BaseModel):
    """Paginated regulation list."""

    items: list[RegulationListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class ArticleDetail(BaseModel):
    """Single article within a regulation."""

    id: str
    number: str
    full_text: str = ""
    content_summary: str | None = None
    parent_chapter_id: str | None = None
    cross_references: list[str] = Field(default_factory=list)


class ChapterDetail(BaseModel):
    """Single chapter with its articles."""

    id: str
    number: str
    title: str | None = None
    articles: list[ArticleDetail] = Field(default_factory=list)


class AmendmentInfo(BaseModel):
    """Amendment relationship info."""

    regulation_id: str
    regulation_title: str
    year: int
    direction: str  # "amends" or "amended_by"
    edge_type: str  # AMENDS, AMENDED_BY, REVOKES, etc.


class RegulationDetailResponse(BaseModel):
    """Full regulation detail for the detail page."""

    id: str
    node_type: str
    number: int
    year: int
    title: str
    about: str
    status: str = "active"
    enactment_date: str | None = None
    chapters: list[ChapterDetail] = Field(default_factory=list)
    amendments: list[AmendmentInfo] = Field(default_factory=list)
    implementing_regulations: list[RegulationListItem] = Field(default_factory=list)
    parent_law: RegulationListItem | None = None
    cross_reference_count: int = 0
    indexed_chunk_count: int = 0


class AmendmentTimelineEntry(BaseModel):
    """Single entry in the amendment timeline."""

    regulation_id: str
    regulation_title: str
    year: int
    number: int
    edge_type: str
    direction: str  # "forward" or "backward"
    target_id: str
    target_title: str


class AmendmentTimelineResponse(BaseModel):
    """Full amendment timeline for a regulation."""

    regulation_id: str
    regulation_title: str
    entries: list[AmendmentTimelineEntry] = Field(default_factory=list)
