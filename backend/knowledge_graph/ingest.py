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

# Regex for amendment detection in regulation titles
# Matches: "Perubahan Atas ...", "Perubahan Kedua Atas ...", "Perubahan Ketiga Atas ..."
_AMENDMENT_ORDER_MAP: dict[str, int] = {
    "": 1,  # bare "Perubahan Atas" → first amendment
    "kedua": 2,
    "ketiga": 3,
    "keempat": 4,
    "kelima": 5,
    "keenam": 6,
    "ketujuh": 7,
    "kedelapan": 8,
    "kesembilan": 9,
    "kesepuluh": 10,
}

_AMENDS_TITLE_RE = re.compile(
    r"Perubahan\s+(?:(Kedua|Ketiga|Keempat|Kelima|Keenam|Ketujuh|Kedelapan|Kesembilan|Kesepuluh)\s+)?Atas\s+",
    re.IGNORECASE,
)

# Regex for cross-regulation citation detection (regulation-level, not article-level)
_CROSS_REG_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("UU", re.compile(
        r"Undang[- ]?Undang\s+(?:Nomor|No\.?)\s+(\d+)\s+Tahun\s+(\d{4})",
        re.IGNORECASE,
    )),
    ("UU", re.compile(
        r"UU\s+(?:Nomor|No\.?)\s+(\d+)\s+(?:Tahun\s+)?(\d{4})",
        re.IGNORECASE,
    )),
    ("PP", re.compile(
        r"Peraturan\s+Pemerintah\s+(?:Nomor|No\.?)\s+(\d+)\s+Tahun\s+(\d{4})",
        re.IGNORECASE,
    )),
    ("PP", re.compile(
        r"PP\s+(?:Nomor|No\.?)\s+(\d+)\s+(?:Tahun\s+)?(\d{4})",
        re.IGNORECASE,
    )),
    ("Perpres", re.compile(
        r"Peraturan\s+Presiden\s+(?:Nomor|No\.?)\s+(\d+)\s+Tahun\s+(\d{4})",
        re.IGNORECASE,
    )),
    ("Permen", re.compile(
        r"Peraturan\s+Menteri\s+\w+\s+(?:Nomor|No\.?)\s+(\d+)\s+Tahun\s+(\d{4})",
        re.IGNORECASE,
    )),
]


def _make_reg_id(jenis: str, nomor: str, tahun: int) -> str:
    """Generate a canonical regulation ID like ``uu_11_2020``."""
    return f"{jenis.lower()}_{nomor}_{tahun}"


def _make_chapter_id(reg_id: str, bab: str) -> str:
    return f"{reg_id}_bab_{bab}"


def _make_article_id(reg_id: str, pasal: str) -> str:
    return f"{reg_id}_pasal_{pasal}"


def _ensure_stub_node(kg: LegalKnowledgeGraph, target_id: str) -> None:
    """Create a stub regulation node if *target_id* doesn't exist in the graph.

    This allows edges to reference regulations not in the ingested corpus
    (e.g. a PP references a UU that wasn't part of our data files).
    """
    if target_id in kg.graph:
        return

    prefix = target_id.split("_")[0]
    jenis_map = {"uu": "UU", "pp": "PP", "perpres": "Perpres", "permen": "Permen", "perda": "Perda"}
    inferred_jenis = jenis_map.get(prefix, "UU")
    stub_cls = _DOC_TYPE_MAP.get(inferred_jenis, Law)
    parts = target_id.split("_")
    stub_nomor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    stub_tahun = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    stub_title = f"{inferred_jenis} {stub_nomor}/{stub_tahun}"

    if stub_cls is GovernmentRegulation:
        stub: Law | GovernmentRegulation | PresidentialRegulation | MinisterialRegulation = GovernmentRegulation(id=target_id, number=stub_nomor, year=stub_tahun, title=stub_title, about=f"{stub_title} (stub)")
    elif stub_cls is PresidentialRegulation:
        stub = PresidentialRegulation(id=target_id, number=stub_nomor, year=stub_tahun, title=stub_title, about=f"{stub_title} (stub)")
    elif stub_cls is MinisterialRegulation:
        stub = MinisterialRegulation(id=target_id, number=stub_nomor, year=stub_tahun, title=stub_title, about=f"{stub_title} (stub)")
    else:
        stub = Law(id=target_id, number=stub_nomor, year=stub_tahun, title=stub_title, about=f"{stub_title} (stub)")
    kg.add_regulation(stub)
    logger.debug("Created stub node: %s", target_id)


def ingest_from_json(
    filepath: str | Path,
    kg: LegalKnowledgeGraph | None = None,
) -> LegalKnowledgeGraph:
    """Parse a legal JSON file and build (or extend) a knowledge graph.

    The JSON file must be an array of chunk objects with fields:
    ``jenis_dokumen``, ``nomor``, ``tahun``, ``judul``, ``tentang``,
    and optionally ``bab``, ``pasal``, ``ayat``, ``text``.

    Args:
        filepath: Path to a JSON file containing legal chunks.
        kg: Optional existing graph to merge into.  When *None* a fresh
            graph is created.  This allows incremental ingestion from
            multiple data sources without duplicating nodes.
    """
    path = Path(filepath)
    with open(path, encoding="utf-8") as fh:
        chunks: list[dict[str, Any]] = json.load(fh)

    if kg is None:
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
    # Strategy:
    # a) Title-match: check if UU judul appears in PP/Perpres tentang (original).
    # b) Regex: scan PP/Perpres tentang, judul, AND chunk text for UU number/year
    #    patterns. This catches "Pelaksanaan Undang-Undang Nomor 23 Tahun 2006"
    #    style references that title-match misses.
    # c) Create stub UU nodes for referenced UUs not already in the graph.

    _UU_REF_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r"Undang[- ]?Undang\s+(?:Nomor|No\.?)\s+(\d+)\s+Tahun\s+(\d{4})", re.IGNORECASE),
        re.compile(r"UU\s+(?:Nomor|No\.?)\s+(\d+)\s+(?:Tahun\s+)?(\d{4})", re.IGNORECASE),
        re.compile(r"UU\s+(\d+)/(\d{4})", re.IGNORECASE),
    ]

    seen_implements: set[tuple[str, str]] = set()  # (source_reg, target_uu) dedup

    for reg_id, meta in reg_meta.items():
        jenis = meta["jenis"]
        if jenis not in ("PP", "Perpres"):
            continue

        # a) Title-match (original logic)
        tentang = (meta.get("tentang") or "").lower()
        for other_id, other_meta in reg_meta.items():
            if other_meta["jenis"] == "UU" and other_id != reg_id:
                uu_judul = (other_meta.get("judul") or "").lower()
                if uu_judul and uu_judul in tentang:
                    pair = (reg_id, other_id)
                    if pair not in seen_implements:
                        seen_implements.add(pair)
                        kg.add_edge(reg_id, other_id, EdgeType.IMPLEMENTS)

        # b) Regex on tentang + judul + chunk text
        search_texts: list[str] = [
            meta.get("tentang") or "",
            meta.get("judul") or "",
        ]
        for chunk in reg_chunks.get(reg_id, []):
            search_texts.append(chunk.get("text", ""))

        combined_search = " ".join(search_texts)
        for pat in _UU_REF_PATTERNS:
            for m in pat.finditer(combined_search):
                ref_nomor = m.group(1)
                ref_tahun = m.group(2)
                target_id = _make_reg_id("UU", ref_nomor, int(ref_tahun))
                if target_id == reg_id:
                    continue
                pair = (reg_id, target_id)
                if pair in seen_implements:
                    continue
                seen_implements.add(pair)

                # c) Create stub UU node if it doesn't exist in graph
                _ensure_stub_node(kg, target_id)

                kg.add_edge(reg_id, target_id, EdgeType.IMPLEMENTS)

    # ── Phase 6: Detect amendment relationships (AMENDS) ─────────────────
    # Scan regulation titles AND tentang for "Perubahan Atas" / "Perubahan Kedua Atas" etc.
    # Also create stub nodes for AMENDS targets not in graph.
    for reg_id, meta in reg_meta.items():
        # Check both judul and tentang for AMENDS pattern
        judul = meta.get("judul") or ""
        tentang = meta.get("tentang") or ""

        judul_match = _AMENDS_TITLE_RE.search(judul)
        tentang_match = _AMENDS_TITLE_RE.search(tentang)
        match = judul_match or tentang_match
        if not match:
            continue

        # Use whichever text had the match for extracting the target
        matched_text = judul if judul_match else tentang

        # Determine amendment order (Kedua=2, Ketiga=3, bare=1)
        order_word = (match.group(1) or "").lower()
        amendment_order = _AMENDMENT_ORDER_MAP.get(order_word, 1)

        # Extract the target regulation info from the text after "Atas"
        after_atas = matched_text[match.end():]

        # Try to match a specific regulation reference in the title/tentang
        target_reg_id: str | None = None
        for jenis_prefix, pattern in _CROSS_REG_PATTERNS:
            ref_match = pattern.search(after_atas)
            if ref_match:
                ref_nomor = ref_match.group(1)
                ref_tahun = ref_match.group(2)
                candidate_id = _make_reg_id(jenis_prefix, ref_nomor, int(ref_tahun))
                target_reg_id = candidate_id
                break

        # Also try short-form references (e.g. "UU 11/2008")
        if target_reg_id is None:
            short_uu_re = re.compile(r"UU\s+(\d+)/(\d{4})", re.IGNORECASE)
            short_match = short_uu_re.search(after_atas)
            if short_match:
                target_reg_id = _make_reg_id("UU", short_match.group(1), int(short_match.group(2)))

        # Fallback: fuzzy match against known regulation titles
        if target_reg_id is None:
            after_atas_lower = after_atas.lower()
            for other_id, other_meta in reg_meta.items():
                if other_id == reg_id:
                    continue
                other_judul = (other_meta.get("judul") or "").lower()
                other_tentang = (other_meta.get("tentang") or "").lower()
                if other_judul and other_judul in after_atas_lower:
                    target_reg_id = other_id
                    break
                if other_tentang and other_tentang in after_atas_lower:
                    target_reg_id = other_id
                    break

        if target_reg_id and target_reg_id != reg_id:
            # Create stub node for target if it doesn't exist
            _ensure_stub_node(kg, target_reg_id)

            kg.add_edge(
                reg_id,
                target_reg_id,
                EdgeType.AMENDS,
                metadata={
                    "amendment_order": amendment_order,
                    "amendment_year": str(meta.get("tahun", "")),
                },
            )
            logger.debug(
                "AMENDS edge: %s -[order=%d]-> %s",
                reg_id, amendment_order, target_reg_id,
            )

    # ── Phase 7: Detect cross-regulation REFERENCES ──────────────────────
    # Scan article/chunk text for citations to OTHER regulations
    # (Phase 4 above handles intra-regulation Pasal references)
    seen_cross_refs: set[tuple[str, str]] = set()  # (source_reg, target_reg) dedup

    for reg_id, chunk_list in reg_chunks.items():
        for chunk in chunk_list:
            text = chunk.get("text", "")
            judul = chunk.get("judul", "")
            tentang = chunk.get("tentang", "")
            combined_text = f"{text} {judul} {tentang}"

            for jenis_prefix, pattern in _CROSS_REG_PATTERNS:
                for ref_match in pattern.finditer(combined_text):
                    ref_nomor = ref_match.group(1)
                    ref_tahun = ref_match.group(2)
                    target_id = _make_reg_id(jenis_prefix, ref_nomor, int(ref_tahun))

                    # Skip self-references
                    if target_id == reg_id:
                        continue

                    # Dedup: one edge per (source, target) pair
                    pair = (reg_id, target_id)
                    if pair in seen_cross_refs:
                        continue
                    seen_cross_refs.add(pair)

                    # Ensure stub node exists for target
                    _ensure_stub_node(kg, target_id)

                    # Extract context snippet around the match
                    start = max(0, ref_match.start() - 50)
                    end = min(len(combined_text), ref_match.end() + 50)
                    context_snippet = combined_text[start:end].strip()

                    pasal = chunk.get("pasal")
                    kg.add_edge(
                        reg_id,
                        target_id,
                        EdgeType.REFERENCES,
                        metadata={
                            "context": context_snippet,
                            "source_pasal": str(pasal) if pasal else None,
                        },
                    )

    return kg


def ingest_all(data_dir: str | Path = "data/peraturan") -> LegalKnowledgeGraph:
    """Ingest all legal JSON files and build a combined knowledge graph.

    Processes the following data sources in order:
    1. ``regulations.json`` — curated primary corpus in *data_dir*.
    2. ``data/external/azzindani/converted.json`` — large-scale Azzindani
       dataset with 616 unique regulations.

    Duplicates (same ``jenis_dokumen``/``nomor``/``tahun``) are handled
    gracefully: ``ingest_from_json`` uses ``add_node`` which is an
    upsert in NetworkX (last write wins for attributes, but all chunks
    from both files contribute articles and edges).
    """
    data_path = Path(data_dir)
    regulations_path = data_path / "regulations.json"
    kg: LegalKnowledgeGraph | None = None

    # Source 1: curated regulations.json
    if regulations_path.exists():
        logger.info("Ingesting primary corpus from %s ...", regulations_path)
        kg = ingest_from_json(regulations_path)
        stats = kg.get_stats()
        logger.info(
            "  → %d nodes, %d edges after regulations.json",
            stats["total_nodes"], stats["total_edges"],
        )
    else:
        logger.warning(
            "No regulations.json found in %s; skipping primary corpus.",
            data_path,
        )

    # Source 2: Azzindani external corpus
    # Resolve relative to project root (data_dir is typically data/peraturan,
    # so project root is two levels up).
    project_root = data_path.resolve().parent.parent if data_path.is_absolute() else Path(data_dir).resolve().parent.parent
    azzindani_path = project_root / "data" / "external" / "azzindani" / "converted.json"
    if azzindani_path.exists():
        logger.info("Ingesting Azzindani corpus from %s ...", azzindani_path)
        kg = ingest_from_json(azzindani_path, kg=kg)
        stats = kg.get_stats()
        logger.info(
            "  → %d nodes, %d edges after Azzindani merge",
            stats["total_nodes"], stats["total_edges"],
        )
    else:
        logger.info("No Azzindani corpus found at %s; skipping.", azzindani_path)

    if kg is None:
        logger.warning("No data sources found; returning empty knowledge graph.")
        return LegalKnowledgeGraph()

    return kg


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
