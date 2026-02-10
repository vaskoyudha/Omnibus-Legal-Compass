"""
Qdrant ingestion pipeline with HuggingFace embeddings.
Ingests Indonesian legal documents for RAG retrieval.

Uses intfloat/multilingual-e5-base for search-optimized multilingual
embeddings with query/passage prefix support.
"""
import json
import os
import hashlib
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_huggingface import HuggingFaceEmbeddings

# Load environment variables
load_dotenv()

# Constants - HuggingFace multilingual model (free, local, supports Indonesian)
EMBEDDING_MODEL = "intfloat/multilingual-e5-base"
EMBEDDING_DIM = 768  # multilingual-e5-base dimension
COLLECTION_NAME = "indonesian_legal_docs"

# Document type mappings for citations
DOC_TYPE_NAMES = {
    "UU": "UU",
    "PP": "PP",
    "Perpres": "Perpres",
    "Perda": "Perda",
    "Permen": "Permen",
}


def format_citation(metadata: dict[str, Any]) -> str:
    """
    Format citation string from document metadata.
    
    Examples:
    - UU No. 11 Tahun 2020 tentang Cipta Kerja, Pasal 5 Ayat (1)
    - PP No. 24 Tahun 2018 tentang Perizinan Berusaha, Pasal 3
    """
    doc_type = metadata.get("jenis_dokumen", "")
    nomor = metadata.get("nomor", "")
    tahun = metadata.get("tahun", "")
    judul = metadata.get("judul", "")
    
    # Base citation
    citation = f"{doc_type} No. {nomor} Tahun {tahun}"
    
    if judul:
        citation += f" tentang {judul}"
    
    # Add article reference
    pasal = metadata.get("pasal")
    if pasal:
        citation += f", Pasal {pasal}"
    
    ayat = metadata.get("ayat")
    if ayat:
        citation += f" Ayat ({ayat})"
    
    bab = metadata.get("bab")
    if bab and not pasal:
        citation += f", Bab {bab}"
    
    return citation


def generate_citation_id(metadata: dict[str, Any]) -> str:
    """
    Generate unique citation ID for a document chunk.
    
    Format: {jenis}_{nomor}_{tahun}_Pasal{pasal}[_Ayat{ayat}]
    Example: UU_11_2020_Pasal5_Ayat1
    """
    parts = [
        metadata.get("jenis_dokumen", "DOC"),
        str(metadata.get("nomor", "0")),
        str(metadata.get("tahun", "0")),
    ]
    
    if metadata.get("pasal"):
        parts.append(f"Pasal{metadata['pasal']}")
    
    if metadata.get("ayat"):
        parts.append(f"Ayat{metadata['ayat']}")
    
    if metadata.get("bab") and not metadata.get("pasal"):
        parts.append(f"Bab{metadata['bab']}")
    
    return "_".join(parts)


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 100,
) -> list[str]:
    """
    Split long text into overlapping chunks by sentence boundaries.
    
    Args:
        text: Input text to split
        chunk_size: Target chunk size in characters
        overlap: Overlap between consecutive chunks in characters
    
    Returns:
        List of text chunks (single-element list if text is short enough)
    """
    if len(text) <= chunk_size:
        return [text]
    
    import re
    
    # Split by sentence boundaries common in Indonesian legal text
    # Handles ". ", "; ", and newlines
    sentences = re.split(r'(?<=[.;])\s+|\n+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        candidate = (current_chunk + " " + sentence).strip() if current_chunk else sentence
        
        if len(candidate) <= chunk_size:
            current_chunk = candidate
        else:
            # Save current chunk if it has content
            if current_chunk:
                chunks.append(current_chunk)
                # Start new chunk with overlap from end of previous
                if overlap > 0 and len(current_chunk) > overlap:
                    overlap_text = current_chunk[-overlap:]
                    # Find word boundary in overlap region
                    space_idx = overlap_text.find(" ")
                    if space_idx > 0:
                        overlap_text = overlap_text[space_idx + 1:]
                    current_chunk = (overlap_text + " " + sentence).strip()
                else:
                    current_chunk = sentence
            else:
                # Single sentence exceeds chunk_size — keep it as-is
                chunks.append(sentence)
                current_chunk = ""
    
    # Don't forget the last chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def parse_legal_structure(text: str, metadata: dict[str, Any]) -> list[dict[str, Any]] | None:
    """
    Parse Indonesian legal text into structural chunks by Pasal boundaries.
    
    Returns list of chunk dicts with text and metadata, or None if no
    structure detected (signals fallback to character-based chunking).
    """
    import re as _re
    
    # Try to split by Pasal boundaries
    pasal_pattern = r'(?=Pasal\s+(\d+))'
    pasal_splits = _re.split(pasal_pattern, text)
    
    if len(pasal_splits) <= 1:
        return None  # No Pasal structure — use fallback
    
    # Build parent context prefix
    doc_type = metadata.get("jenis_dokumen", "")
    doc_nomor = metadata.get("nomor", "")
    doc_tahun = metadata.get("tahun", "")
    doc_title = metadata.get("judul", "")
    parent_prefix = f"{doc_type} No. {doc_nomor} Tahun {doc_tahun}"
    if doc_title:
        parent_prefix += f" tentang {doc_title}"
    
    chunks = []
    i = 1  # Skip preamble at index 0
    while i < len(pasal_splits) - 1:
        pasal_num = pasal_splits[i]
        pasal_text = pasal_splits[i + 1].strip()
        
        # Inject parent context
        chunk_text_str = f"[{parent_prefix}, Pasal {pasal_num}]\n\n{pasal_text}"
        
        chunk_meta = {**metadata, "pasal": pasal_num}
        chunks.append({
            "text": chunk_text_str,
            "metadata": chunk_meta,
        })
        i += 2
    
    return chunks if chunks else None


def create_document_chunks(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Create chunks from legal documents with metadata for citations.
    
    Uses structure-aware parsing (Pasal boundaries) when possible,
    falls back to character-based chunking for unstructured text.
    """
    chunks = []
    
    for doc in documents:
        text = doc.get("text", "")
        if not text:
            continue
        
        # Build metadata
        metadata = {
            "jenis_dokumen": doc.get("jenis_dokumen", ""),
            "nomor": doc.get("nomor", ""),
            "tahun": doc.get("tahun", 0),
            "judul": doc.get("judul", ""),
            "tentang": doc.get("tentang", ""),
        }
        for field in ["bab", "pasal", "ayat"]:
            if field in doc:
                metadata[field] = doc[field]
        
        # Try structure-aware parsing first
        structured = parse_legal_structure(text, metadata)
        
        if structured:
            for chunk_data in structured:
                cid = generate_citation_id(chunk_data["metadata"])
                cit = format_citation(chunk_data["metadata"])
                sub_chunks = chunk_text(chunk_data["text"], chunk_size=500, overlap=100)
                for idx, sub in enumerate(sub_chunks):
                    suffix = f"_chunk{idx+1}" if len(sub_chunks) > 1 else ""
                    part_label = f" (bagian {idx+1})" if len(sub_chunks) > 1 else ""
                    chunks.append({
                        "text": sub,
                        "citation_id": f"{cid}{suffix}",
                        "citation": f"{cit}{part_label}",
                        "metadata": chunk_data["metadata"],
                    })
        else:
            # Fallback to character-based chunking
            base_cid = generate_citation_id(metadata)
            base_cit = format_citation(metadata)
            text_chunks = chunk_text(text, chunk_size=500, overlap=100)
            for idx, piece in enumerate(text_chunks):
                suffix = f"_chunk{idx+1}" if len(text_chunks) > 1 else ""
                part_label = f" (bagian {idx+1})" if len(text_chunks) > 1 else ""
                chunks.append({
                    "text": piece,
                    "citation_id": f"{base_cid}{suffix}",
                    "citation": f"{base_cit}{part_label}",
                    "metadata": metadata,
                })
    
    return chunks


def get_collection_config() -> dict[str, Any]:
    """
    Get Qdrant collection configuration.
    
    Configured for NVIDIA NV-Embed-QA embeddings with cosine similarity.
    """
    return {
        "vectors_config": {
            "size": EMBEDDING_DIM,
            "distance": "Cosine",
        }
    }


def create_point_struct(
    point_id: int,
    chunk: dict[str, Any],
    embedding: list[float]
) -> PointStruct:
    """
    Create a Qdrant PointStruct from a chunk and its embedding.
    """
    # Flatten metadata into payload for filtering
    payload = {
        "text": chunk["text"],
        "citation_id": chunk["citation_id"],
        "citation": chunk.get("citation", ""),
        **chunk["metadata"]
    }
    
    return PointStruct(
        id=point_id,
        vector=embedding,
        payload=payload
    )


def ingest_documents(
    json_path: str,
    collection_name: str = COLLECTION_NAME,
    qdrant_url: str | None = None,
    qdrant_api_key: str | None = None,
    batch_size: int = 50
) -> dict[str, Any]:
    """
    Main ingestion pipeline.
    
    1. Load documents from JSON
    2. Create chunks with metadata
    3. Generate embeddings using HuggingFace
    4. Upsert to Qdrant collection
    
    Args:
        json_path: Path to JSON file with legal documents
        collection_name: Qdrant collection name
        qdrant_url: Qdrant server URL (defaults to env var or localhost)
        qdrant_api_key: API key for Qdrant Cloud (optional)
        batch_size: Number of documents to embed at once
    
    Returns:
        Status dict with ingestion results
    """
    # Get config from environment
    qdrant_url = qdrant_url or os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = qdrant_api_key or os.getenv("QDRANT_API_KEY")
    
    # Initialize clients (with API key for Qdrant Cloud)
    if qdrant_api_key:
        client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    else:
        client = QdrantClient(url=qdrant_url)
    
    embedder = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    
    # Load documents
    with open(json_path, "r", encoding="utf-8") as f:
        documents = json.load(f)
    
    print(f"Loaded {len(documents)} documents from {json_path}")
    
    # Create chunks
    chunks = create_document_chunks(documents)
    print(f"Created {len(chunks)} chunks")
    
    # Create/recreate collection
    config = get_collection_config()
    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=config["vectors_config"]["size"],
            distance=Distance.COSINE
        )
    )
    print(f"Created collection: {collection_name}")
    
    # Generate embeddings
    texts = [f"passage: {chunk['text']}" for chunk in chunks]
    print(f"Generating embeddings for {len(texts)} chunks...")
    embeddings = embedder.embed_documents(texts)
    print(f"Generated {len(embeddings)} embeddings")
    
    # Create points
    points = [
        create_point_struct(i, chunk, embedding)
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
    ]
    
    # Upsert to Qdrant
    client.upsert(
        collection_name=collection_name,
        points=points,
        wait=True
    )
    print(f"Upserted {len(points)} points to Qdrant")
    
    return {
        "status": "success",
        "documents_ingested": len(documents),
        "chunks_created": len(chunks),
        "collection_name": collection_name,
    }


def main():
    """CLI entry point for ingestion."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest legal documents to Qdrant")
    parser.add_argument(
        "--json-path",
        default="data/peraturan/regulations.json",
        help="Path to JSON file with documents"
    )
    parser.add_argument(
        "--collection",
        default=COLLECTION_NAME,
        help="Qdrant collection name"
    )
    parser.add_argument(
        "--qdrant-url",
        default=os.getenv("QDRANT_URL", "http://localhost:6333"),
        help="Qdrant server URL"
    )
    
    args = parser.parse_args()
    
    # Note: HuggingFace embeddings run locally, no API key needed for embeddings
    # NVIDIA_API_KEY is still used for the LLM (Llama 3.1) in later stages
    
    result = ingest_documents(
        json_path=args.json_path,
        collection_name=args.collection,
        qdrant_url=args.qdrant_url
    )
    
    print("\n=== Ingestion Complete ===")
    print(f"Status: {result['status']}")
    print(f"Documents: {result['documents_ingested']}")
    print(f"Chunks: {result['chunks_created']}")
    print(f"Collection: {result['collection_name']}")


if __name__ == "__main__":
    main()
