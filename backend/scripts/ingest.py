"""
Qdrant ingestion pipeline with HuggingFace embeddings.
Ingests Indonesian legal documents for RAG retrieval.

Uses sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 for
multilingual support (including Bahasa Indonesia).
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
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384  # paraphrase-multilingual-MiniLM-L12-v2 dimension
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


def create_document_chunks(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Create chunks from legal documents with metadata for citations.
    
    For legal documents, each article/ayat is typically a natural chunk.
    We preserve the full metadata for citation generation.
    """
    chunks = []
    
    for doc in documents:
        # Extract text
        text = doc.get("text", "")
        if not text:
            continue
        
        # Build metadata (excluding text)
        metadata = {
            "jenis_dokumen": doc.get("jenis_dokumen", ""),
            "nomor": doc.get("nomor", ""),
            "tahun": doc.get("tahun", 0),
            "judul": doc.get("judul", ""),
            "tentang": doc.get("tentang", ""),
        }
        
        # Optional fields
        for field in ["bab", "pasal", "ayat"]:
            if field in doc:
                metadata[field] = doc[field]
        
        # Generate citation ID
        citation_id = generate_citation_id(metadata)
        
        # Format full citation
        citation = format_citation(metadata)
        
        chunks.append({
            "text": text,
            "citation_id": citation_id,
            "citation": citation,
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
    qdrant_url: str = "http://localhost:6333",
    batch_size: int = 50
) -> dict[str, Any]:
    """
    Main ingestion pipeline.
    
    1. Load documents from JSON
    2. Create chunks with metadata
    3. Generate embeddings using NVIDIA NIM
    4. Upsert to Qdrant collection
    
    Args:
        json_path: Path to JSON file with legal documents
        collection_name: Qdrant collection name
        qdrant_url: Qdrant server URL
        batch_size: Number of documents to embed at once
    
    Returns:
        Status dict with ingestion results
    """
    # Initialize clients
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
    texts = [chunk["text"] for chunk in chunks]
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
        default="data/peraturan/sample.json",
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
