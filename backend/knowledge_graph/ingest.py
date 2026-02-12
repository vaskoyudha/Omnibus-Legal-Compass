"""
Knowledge Graph ingestion pipeline.

Parses legal JSON documents from the data/ directory and builds a
populated LegalKnowledgeGraph with regulation, chapter, article nodes
and CONTAINS / IMPLEMENTS / REFERENCES edges.

Usage:
    python backend/knowledge_graph/ingest.py
"""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from .graph import LegalKnowledgeGraph
from .schema import (
    Article,
    Chapter,
    EdgeType,
    GovernmentRegulation,
    Law,
    MinisterialRegulation,
    PresidentialRegulation,
)

logger = logging.getLogger(__name__)

# Map jenis_dokumen values to the corresponding schema class
_DOC_TYPE_MAP: dict[str, type] = {
    "UU": Law,
    "PP": GovernmentRegulation,
    "Perpres": PresidentialRegulation,
    "Permen": MinisterialRegulation,
    # Perda, Perppu, Perban fall back to Law for simplicity
    "Perda": Law,
    "Perppu": Law,
    "Perban": MinisterialRegulation,
}

# Regex for cross-reference detection in article text
_CROSS_REF_RE = re.compile(
    r"(?:sebagaimana\s+dimaksud\s+(?:dalam|pada)\s+)?(?:Pasal|pasal)\s+(\d+)",
    re.IGNORECASE,
)


def _make_reg_id(jenis: str, nomor: str, tahun: int) -> str:
    """Generate a canonical regulation ID like ``uu_11_2020``."""
    return f"{jenis.lower()}_{nomor}_{tahun}"


def _make_chapter_id(reg_id: str, bab: str) -> str:
    return f"{reg_id}_bab_{bab}"


def _make_article_id(reg_id: str, pasal: str) -> str:
    return f"{reg_id}_pasal_{pasal}"


def ingest_from_json(filepath: str | Path) -> LegalKnowledgeGraph:
    """Parse a legal JSON file and build a knowledge graph.

    The JSON file must be an array of chunk objects with fields:
    ``jenis_dokumen``, ``nomor``, ``tahun``, ``judul``, ``tentang``,
    and optionally ``bab``, ``pasal``, ``ayat``, ``text``.
    """
    path = Path(filepath)
    with open(path, encoding="utf-8") as fh:
        chunks: list[dict[str, Any]] = json.load(fh)

    kg = LegalKnowledgeGraph()

    # ── Phase 1: Group chunks by regulation ──────────────────────────────
    reg_chunks: dict[str, list[dict[str, Any]]] = defaultdict(list)
    reg_meta: dict[str, dict[str, Any]] = {}

    for chunk in chunks:
        jenis = chunk.get("jenis_dokumen", "")
        nomor = str(chunk.get("nomor", ""))
        tahun = chunk.get("tahun", 0)
        if not jenis or not nomor or not tahun:
            continue
        reg_id = _make_reg_id(jenis, nomor, tahun)
        reg_chunks[reg_id].append(chunk)
        if reg_id not in reg_meta:
            reg_meta[reg_id] = {
                "jenis": jenis,
                "nomor": nomor,
                "tahun": tahun,
                "judul": chunk.get("judul", ""),
                "tentang": chunk.get("tentang", ""),
            }

    # ── Phase 2: Create regulation nodes ─────────────────────────────────
    for reg_id, meta in reg_meta.items():
        cls = _DOC_TYPE_MAP.get(meta["jenis"], Law)
        node_id: str = reg_id
        number: int = int(meta["nomor"]) if str(meta["nomor"]).isdigit() else 0
        year: int = int(meta["tahun"])
        title: str = str(meta["judul"])
        about: str = str(meta["tentang"] or meta["judul"])

        if cls is GovernmentRegulation:
            node = GovernmentRegulation(id=node_id, number=number, year=year, title=title, about=about)
        elif cls is PresidentialRegulation:
            node = PresidentialRegulation(id=node_id, number=number, year=year, title=title, about=about)
        elif cls is MinisterialRegulation:
            node = MinisterialRegulation(id=node_id, number=number, year=year, title=title, about=about)
        else:
            node = Law(id=node_id, number=number, year=year, title=title, about=about)
        kg.add_regulation(node)

    # ── Phase 3: Create chapter and article nodes ────────────────────────
    seen_chapters: set[str] = set()
    article_texts: dict[str, list[str]] = defaultdict(list)
    article_meta: dict[str, dict[str, Any]] = {}

    for reg_id, chunk_list in reg_chunks.items():
        meta = reg_meta[reg_id]
        for chunk in chunk_list:
            bab = chunk.get("bab")
            pasal = chunk.get("pasal")

            # Chapter node
            if bab:
                chap_id = _make_chapter_id(reg_id, str(bab))
                if chap_id not in seen_chapters:
                    seen_chapters.add(chap_id)
                    chapter = Chapter(
                        id=chap_id,
                        number=str(bab),
                        title=chunk.get("bagian"),
                        parent_regulation_id=reg_id,
                    )
                    kg.add_chapter(chapter)

            # Article node (collect text from multiple chunks of same article)
            if pasal:
                art_id = _make_article_id(reg_id, str(pasal))
                text = chunk.get("text", "")
                ayat = chunk.get("ayat")
                if ayat:
                    text = f"Ayat ({ayat}): {text}"
                article_texts[art_id].append(text)
                if art_id not in article_meta:
                    article_meta[art_id] = {
                        "reg_id": reg_id,
                        "pasal": str(pasal),
                        "bab": str(bab) if bab else None,
                    }

    for art_id, texts in article_texts.items():
        meta = article_meta[art_id]
        parent_chap_id = (
            _make_chapter_id(meta["reg_id"], meta["bab"])
            if meta["bab"]
            else None
        )
        full_text = "\n".join(texts)
        article = Article(
            id=art_id,
            number=meta["pasal"],
            content_summary=full_text[:200] if len(full_text) > 200 else None,
            full_text=full_text,
            parent_chapter_id=parent_chap_id,
            parent_regulation_id=meta["reg_id"],
        )
        kg.add_article(article)

    # ── Phase 4: Detect cross-references ─────────────────────────────────
    for art_id in article_texts:
        meta = article_meta[art_id]
        full_text = "\n".join(article_texts[art_id])
        referenced_pasals = set(_CROSS_REF_RE.findall(full_text))
        for ref_pasal in referenced_pasals:
            target_id = _make_article_id(meta["reg_id"], ref_pasal)
            if target_id != art_id and target_id in article_texts:
                kg.add_edge(art_id, target_id, EdgeType.REFERENCES)

    # ── Phase 5: Detect implementing relationships ───────────────────────
    for reg_id, meta in reg_meta.items():
        jenis = meta["jenis"]
        if jenis in ("PP", "Perpres"):
            tentang = (meta.get("tentang") or "").lower()
            for other_id, other_meta in reg_meta.items():
                if other_meta["jenis"] == "UU" and other_id != reg_id:
                    uu_judul = (other_meta.get("judul") or "").lower()
                    if uu_judul and uu_judul in tentang:
                        kg.add_edge(reg_id, other_id, EdgeType.IMPLEMENTS)

    return kg


def ingest_all(data_dir: str | Path = "data/peraturan") -> LegalKnowledgeGraph:
    """Ingest all legal JSON files in *data_dir*.

    Currently processes ``sample.json``.  Extend to ``regulations.json``
    when ready for the full 5,817-document dataset.
    """
    data_path = Path(data_dir)
    sample_path = data_path / "sample.json"
    if not sample_path.exists():
        logger.warning("No sample.json found in %s", data_path)
        return LegalKnowledgeGraph()
    return ingest_from_json(sample_path)


# ── CLI entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    import sys

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Resolve paths relative to project root
    project_root = Path(__file__).resolve().parent.parent.parent
    data_dir = project_root / "data" / "peraturan"
    output_path = project_root / "data" / "knowledge_graph.json"

    # Need to add backend/ to sys.path for imports
    sys.path.insert(0, str(project_root / "backend"))

    logger.info("Ingesting legal documents from %s ...", data_dir)
    graph = ingest_all(data_dir)
    stats = graph.get_stats()

    logger.info(
        "Ingested %d nodes (%s) and %d edges (%s)",
        stats["total_nodes"],
        ", ".join(f"{k}: {v}" for k, v in stats["nodes_by_type"].items()),
        stats["total_edges"],
        ", ".join(f"{k}: {v}" for k, v in stats["edges_by_type"].items()),
    )

    from knowledge_graph.persistence import save_graph  # pyright: ignore[reportImplicitRelativeImport]

    save_graph(graph, output_path)
    logger.info("Knowledge graph saved to %s", output_path)
