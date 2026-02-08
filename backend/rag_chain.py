"""
RAG Chain Module for Indonesian Legal Q&A

Uses NVIDIA NIM Llama 3.1 as the LLM with custom retriever for legal documents.
Provides citations and "I don't know" guardrails.
"""

from __future__ import annotations

import os
import json
import logging
from dataclasses import dataclass
from typing import Any

import requests
from dotenv import load_dotenv

from backend.retriever import HybridRetriever, SearchResult

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_MODEL = "meta/llama-3.1-8b-instruct"  # Switched from kimi-k2.5 (timeout issues)
MAX_TOKENS = 4096
TEMPERATURE = 0.7

# Retriever configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "indonesian_legal_docs")
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


# Indonesian Legal Q&A System Prompt
SYSTEM_PROMPT = """Anda adalah asisten hukum Indonesia yang ahli dan terpercaya. Tugas Anda adalah menjawab pertanyaan tentang peraturan perundang-undangan Indonesia berdasarkan dokumen yang diberikan.

ATURAN PENTING:
1. Jawab HANYA berdasarkan konteks dokumen yang diberikan
2. Jika informasi tidak ada dalam konteks, katakan: "Maaf, saya tidak menemukan informasi tersebut dalam dokumen yang tersedia."
3. Selalu sertakan SITASI dengan format [Nomor] untuk setiap fakta yang Anda sebutkan
4. Gunakan Bahasa Indonesia yang formal dan jelas
5. Jangan mengarang atau berasumsi informasi yang tidak ada dalam konteks
6. Jika ada ketidakjelasan, sebutkan dengan jujur

FORMAT JAWABAN:
- Jawaban harus terstruktur dan mudah dipahami
- Setiap klaim harus disertai sitasi [1], [2], dst
- Di akhir jawaban, cantumkan daftar SUMBER dengan format lengkap"""


USER_PROMPT_TEMPLATE = """Berdasarkan dokumen hukum berikut, jawab pertanyaan dengan menyertakan sitasi.

DOKUMEN:
{context}

PERTANYAAN: {question}

JAWABAN (dengan sitasi):"""


@dataclass
class RAGResponse:
    """Response from RAG chain with citations."""
    
    answer: str
    citations: list[dict[str, Any]]
    sources: list[str]
    confidence: str
    raw_context: str


class NVIDIANimClient:
    """Client for NVIDIA NIM API with Llama 3.1 model."""
    
    def __init__(
        self,
        api_key: str | None = None,
        api_url: str = NVIDIA_API_URL,
        model: str = NVIDIA_MODEL,
        max_tokens: int = MAX_TOKENS,
        temperature: float = TEMPERATURE,
    ):
        self.api_key = api_key or NVIDIA_API_KEY
        if not self.api_key:
            raise ValueError("NVIDIA_API_KEY not found in environment variables")
        
        self.api_url = api_url
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    def generate(
        self,
        user_message: str,
        system_message: str | None = None,
    ) -> str:
        """Generate response from NVIDIA NIM API."""
        messages = []
        
        if system_message:
            messages.append({
                "role": "system",
                "content": system_message,
            })
        
        messages.append({
            "role": "user",
            "content": user_message,
        })
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False,
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            
            result = response.json()
            message = result["choices"][0]["message"]
            
            # Some models may return 'reasoning' or 'reasoning_content' instead of 'content'
            content = (
                message.get("content") 
                or message.get("reasoning") 
                or message.get("reasoning_content") 
                or ""
            )
            
            if not content:
                logger.warning(f"Empty response from model. Full message: {message}")
                
            return content
        
        except requests.exceptions.RequestException as e:
            logger.error(f"NVIDIA NIM API error: {e}")
            raise RuntimeError(f"Failed to get response from NVIDIA NIM: {e}") from e


class LegalRAGChain:
    """RAG Chain for Indonesian Legal Q&A with citations."""
    
    def __init__(
        self,
        retriever: HybridRetriever | None = None,
        llm_client: NVIDIANimClient | None = None,
        top_k: int = 5,
    ):
        # Initialize retriever
        if retriever is None:
            logger.info("Initializing HybridRetriever...")
            self.retriever = HybridRetriever(
                qdrant_url=QDRANT_URL,
                collection_name=COLLECTION_NAME,
                embedding_model=EMBEDDING_MODEL,
            )
        else:
            self.retriever = retriever
        
        # Initialize LLM client
        if llm_client is None:
            logger.info("Initializing NVIDIA NIM client...")
            self.llm_client = NVIDIANimClient()
        else:
            self.llm_client = llm_client
        
        self.top_k = top_k
    
    def _format_context(self, results: list[SearchResult]) -> tuple[str, list[dict]]:
        """Format search results into context with numbered citations."""
        context_parts = []
        citations = []
        
        for i, result in enumerate(results, 1):
            # Build citation info
            citation_info = {
                "number": i,
                "citation_id": result.citation_id,
                "citation": result.citation,
                "score": round(result.score, 4),
                "metadata": result.metadata,
            }
            citations.append(citation_info)
            
            # Format context block
            context_block = f"""[{i}] {result.citation}
{result.text}
---"""
            context_parts.append(context_block)
        
        return "\n\n".join(context_parts), citations
    
    def _extract_sources(self, citations: list[dict]) -> list[str]:
        """Extract formatted source list from citations."""
        sources = []
        for cit in citations:
            sources.append(f"[{cit['number']}] {cit['citation']}")
        return sources
    
    def _assess_confidence(self, results: list[SearchResult]) -> str:
        """Assess confidence based on retrieval scores."""
        if not results:
            return "tidak ada"
        
        avg_score = sum(r.score for r in results) / len(results)
        top_score = results[0].score if results else 0
        
        if top_score > 0.5 and avg_score > 0.3:
            return "tinggi"
        elif top_score > 0.3 and avg_score > 0.15:
            return "sedang"
        else:
            return "rendah"
    
    def query(
        self,
        question: str,
        filter_jenis_dokumen: str | None = None,
        top_k: int | None = None,
    ) -> RAGResponse:
        """
        Query the RAG chain with a question.
        
        Args:
            question: User question in Indonesian
            filter_jenis_dokumen: Optional filter by document type (UU, PP, Perpres, etc.)
            top_k: Number of documents to retrieve
        
        Returns:
            RAGResponse with answer, citations, and sources
        """
        k = top_k or self.top_k
        
        # Step 1: Retrieve relevant documents
        logger.info(f"Retrieving documents for: {question[:50]}...")
        
        if filter_jenis_dokumen:
            results = self.retriever.search_by_document_type(
                query=question,
                jenis_dokumen=filter_jenis_dokumen,
                top_k=k,
            )
        else:
            results = self.retriever.hybrid_search(
                query=question,
                top_k=k,
            )
        
        # Handle no results
        if not results:
            return RAGResponse(
                answer="Maaf, saya tidak menemukan dokumen yang relevan dengan pertanyaan Anda dalam database.",
                citations=[],
                sources=[],
                confidence="tidak ada",
                raw_context="",
            )
        
        # Step 2: Format context
        context, citations = self._format_context(results)
        sources = self._extract_sources(citations)
        confidence = self._assess_confidence(results)
        
        # Step 3: Generate answer using LLM
        user_prompt = USER_PROMPT_TEMPLATE.format(
            context=context,
            question=question,
        )
        
        logger.info(f"Generating answer with NVIDIA NIM {NVIDIA_MODEL}...")
        answer = self.llm_client.generate(
            user_message=user_prompt,
            system_message=SYSTEM_PROMPT,
        )
        
        # Step 4: Build response
        return RAGResponse(
            answer=answer,
            citations=citations,
            sources=sources,
            confidence=confidence,
            raw_context=context,
        )
    
    def query_with_history(
        self,
        question: str,
        chat_history: list[dict[str, str]] | None = None,
        **kwargs,
    ) -> RAGResponse:
        """
        Query with conversation history for follow-up questions.
        
        Args:
            question: Current question
            chat_history: Previous Q&A pairs [{"question": ..., "answer": ...}, ...]
            **kwargs: Additional args passed to query()
        
        Returns:
            RAGResponse
        """
        # For follow-up questions, prepend context from history
        if chat_history:
            history_context = "\n".join([
                f"Q: {h['question']}\nA: {h['answer'][:200]}..."
                for h in chat_history[-3:]  # Last 3 turns
            ])
            enhanced_question = f"Konteks sebelumnya:\n{history_context}\n\nPertanyaan saat ini: {question}"
        else:
            enhanced_question = question
        
        return self.query(enhanced_question, **kwargs)


def main():
    """Test the RAG chain."""
    print("Initializing Legal RAG Chain...")
    
    try:
        rag = LegalRAGChain()
        
        # Test queries
        test_questions = [
            "Apa itu Undang-Undang Cipta Kerja?",
            "Bagaimana aturan tentang pelindungan data pribadi?",
            "Apa yang dimaksud dengan perizinan berusaha terintegrasi?",
        ]
        
        for question in test_questions:
            print(f"\n{'='*60}")
            print(f"PERTANYAAN: {question}")
            print("="*60)
            
            response = rag.query(question)
            
            print(f"\nJAWABAN:\n{response.answer}")
            print(f"\nKONFIDENSI: {response.confidence}")
            print(f"\nSUMBER:")
            for source in response.sources:
                print(f"  {source}")
    
    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
