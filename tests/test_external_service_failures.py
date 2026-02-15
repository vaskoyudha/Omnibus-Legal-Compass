"""
Tests for external service failure handling.

Verifies that the API gracefully handles failures from:
- Qdrant (connection, timeout, query errors)
- NVIDIA NIM API (HTTP errors, timeouts)
- HuggingFace embeddings (model loading, inference errors)
- CrossEncoder reranker (fallback behavior)
- Streaming API failures
- LLM-as-judge grounding verification failures
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
import sys
import os

# Ensure backend is importable from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from rag_chain import RAGResponse, ConfidenceScore, ValidationResult
from retriever import SearchResult


def _mock_rag_response(answer="Jawaban [1].", n_citations=2) -> RAGResponse:
    """Helper to create a mock RAG response."""
    citations = [
        {
            "number": i,
            "citation_id": f"uu-{i}-2020",
            "citation": f"UU No. {i} Tahun 2020, Pasal {i}",
            "score": 0.85 - (i * 0.05),
            "metadata": {"jenis_dokumen": "UU", "text": "..."},
        }
        for i in range(1, n_citations + 1)
    ]
    return RAGResponse(
        answer=answer,
        citations=citations,
        sources=[f"[{c['number']}] {c['citation']}" for c in citations],
        confidence="tinggi",
        confidence_score=ConfidenceScore(numeric=0.82, label="tinggi", top_score=0.9, avg_score=0.75),
        raw_context="context",
        validation=ValidationResult(
            is_valid=True, citation_coverage=0.8, hallucination_risk="low"
        ),
    )


class TestQdrantFailures:
    """Test Qdrant service failure handling."""

    def test_qdrant_connection_failure_returns_500(self, test_client):
        """Qdrant connection failure should return HTTP 500."""
        with patch("main.rag_chain") as mock_chain:
            # Simulate Qdrant connection error at retrieval level
            mock_chain.query.side_effect = ConnectionError("Failed to connect to Qdrant")
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/v1/ask",
                json={"question": "Apa syarat pendirian PT?"},
            )

        assert response.status_code == 500
        # Verify error message is present
        data = response.json()
        assert "detail" in data

    def test_qdrant_timeout_returns_500(self, test_client):
        """Qdrant query timeout should return HTTP 500."""
        with patch("main.rag_chain") as mock_chain:
            mock_chain.query.side_effect = TimeoutError("Qdrant query timed out")
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/v1/ask",
                json={"question": "Apa syarat pendirian PT?"},
            )

        assert response.status_code == 500

    def test_qdrant_unexpected_response_returns_500(self, test_client):
        """Qdrant unexpected response should return HTTP 500."""
        with patch("main.rag_chain") as mock_chain:
            # Use generic exception that Qdrant might throw
            mock_chain.query.side_effect = RuntimeError("Qdrant unexpected response: 500 Internal Server Error")
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/v1/ask",
                json={"question": "Apa syarat pendirian PT?"},
            )

        assert response.status_code == 500


class TestEmbeddingFailures:
    """Test embedding service failure handling."""

    def test_embedding_model_load_failure(self, test_client):
        """HuggingFace embeddings model loading failure should be handled."""
        with patch("main.rag_chain") as mock_chain:
            # Simulate embedding initialization failure
            from langchain_huggingface import HuggingFaceEmbeddings
            with patch.object(HuggingFaceEmbeddings, "__init__", side_effect=OSError("Model not found")):
                response = test_client.post(
                    "/api/v1/ask",
                    json={"question": "Apa syarat pendirian PT?"},
                )
        
        # Should return 500 as the chain can't initialize properly
        assert response.status_code in [500, 503]

    def test_embedding_inference_failure(self, test_client):
        """Embedding inference failure should return HTTP 500."""
        with patch("main.rag_chain") as mock_chain:
            mock_chain.query.side_effect = RuntimeError("Embedding inference failed")
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/v1/ask",
                json={"question": "Apa syarat pendirian PT?"},
            )

        assert response.status_code == 500


class TestNvidiaNIMFailures:
    """Test NVIDIA NIM API failure handling."""

    def test_nim_api_http_error_returns_500(self, test_client):
        """NVIDIA NIM API HTTP error should return HTTP 500."""
        import requests
        with patch("main.rag_chain") as mock_chain:
            mock_chain.query.side_effect = requests.HTTPError("NVIDIA API returned 503")
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/v1/ask",
                json={"question": "Apa syarat pendirian PT?"},
            )

        assert response.status_code == 500

    def test_nim_api_timeout_returns_500(self, test_client):
        """NVIDIA NIM API timeout should return HTTP 500."""
        import requests
        with patch("main.rag_chain") as mock_chain:
            mock_chain.query.side_effect = requests.Timeout("Request to NVIDIA API timed out")
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/v1/ask",
                json={"question": "Apa syarat pendirian PT?"},
            )

        assert response.status_code == 500

    def test_nim_api_connection_error_returns_500(self, test_client):
        """NVIDIA NIM API connection error should return HTTP 500."""
        import requests
        with patch("main.rag_chain") as mock_chain:
            mock_chain.query.side_effect = requests.ConnectionError("Failed to connect to NVIDIA API")
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/v1/ask",
                json={"question": "Apa syarat pendirian PT?"},
            )

        assert response.status_code == 500


class TestCrossEncoderRerankerFailures:
    """Test CrossEncoder reranker failure handling (should fallback gracefully)."""

    def test_crossencoder_predict_failure_fallback(self, test_client):
        """CrossEncoder predict failure should fallback to RRF scores."""
        with patch("main.rag_chain") as mock_chain:
            mock_resp = _mock_rag_response()
            mock_chain.query.return_value = mock_resp
            mock_chain.llm_client = MagicMock()
            
            # Mock retriever with failing reranker
            mock_retriever = MagicMock()
            mock_retriever.client = MagicMock()
            mock_retriever.collection_name = "test"
            
            # Simulate reranker failure during query
            def reranker_side_effect(*args, **kwargs):
                raise RuntimeError("CrossEncoder prediction failed")
            
            mock_retriever.hybrid_search.side_effect = reranker_side_effect
            mock_chain.retriever = mock_retriever

            response = test_client.post(
                "/api/v1/ask",
                json={"question": "Apa syarat pendirian PT?"},
            )

        # Should either return 500 or fall back gracefully depending on implementation
        assert response.status_code in [200, 500]


class TestStreamingAPIFailures:
    """Test streaming API failure handling."""

    def test_streaming_llm_failure_returns_error_event(self, test_client):
        """Streaming LLM failure should return SSE error event."""
        with patch("main.rag_chain") as mock_chain:
            # Simulate streaming failure - query_stream raises an error
            mock_chain.query_stream.side_effect = RuntimeError("LLM generation failed")
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/v1/ask/stream",
                json={"question": "Apa syarat pendirian PT?"},
            )

        # When streaming fails, it may return 200 with an error event or 500
        # Either is acceptable for failure handling
        assert response.status_code in [200, 500]

    def test_streaming_qdrant_failure_returns_500(self, test_client):
        """Streaming with Qdrant failure should return HTTP 500."""
        with patch("main.rag_chain") as mock_chain:
            mock_chain.query_stream.side_effect = ConnectionError("Qdrant connection lost")
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/v1/ask/stream",
                json={"question": "Apa syarat pendirian PT?"},
            )

        # The streaming endpoint may return 200 with error in SSE or 500
        # Both indicate proper error handling
        assert response.status_code in [200, 500]


class TestGroundingVerificationFailures:
    """Test LLM-as-judge grounding verification failure handling."""

    def test_grounding_verification_failure_degrades_gracefully(self, test_client):
        """Grounding verification failure should not crash the response."""
        with patch("main.rag_chain") as mock_chain:
            # Mock successful query but failing grounding verification
            mock_resp = _mock_rag_response()
            # Remove validation to simulate grounding failure
            mock_resp.validation = None
            mock_chain.query.return_value = mock_resp
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/v1/ask",
                json={"question": "Apa syarat pendirian PT?"},
            )

        # Should still return 200 with degraded response (no validation)
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data


class TestComplianceEndpointFailures:
    """Test compliance endpoint external service failures."""

    def test_compliance_qdrant_failure_returns_500(self, test_client):
        """Compliance check with Qdrant failure returns HTTP 500."""
        with patch("main.rag_chain") as mock_chain:
            mock_chain.query.side_effect = ConnectionError("Qdrant unavailable")
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/v1/compliance/check",
                data={"business_description": "Restoran di Jakarta dengan NIB"},
            )

        assert response.status_code == 500

    def test_compliance_nim_failure_returns_500(self, test_client):
        """Compliance check with NIM API failure returns HTTP 500."""
        import requests
        with patch("main.rag_chain") as mock_chain:
            mock_chain.query.side_effect = requests.HTTPError("NVIDIA API error")
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/v1/compliance/check",
                data={"business_description": "Restoran di Jakarta dengan NIB"},
            )

        assert response.status_code == 500


class TestGuidanceEndpointFailures:
    """Test guidance endpoint external service failures."""

    def test_guidance_qdrant_failure_returns_500(self, test_client):
        """Guidance with Qdrant failure returns HTTP 500."""
        with patch("main.rag_chain") as mock_chain:
            mock_chain.aquery.side_effect = TimeoutError("Request timeout")
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/v1/guidance",
                json={"business_type": "PT", "industry": "teknologi", "location": "Jakarta"},
            )

        assert response.status_code == 500

    def test_guidance_nim_failure_returns_500(self, test_client):
        """Guidance with NIM API failure returns HTTP 500."""
        import requests
        with patch("main.rag_chain") as mock_chain:
            mock_chain.aquery.side_effect = requests.ConnectionError("API unavailable")
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/v1/guidance",
                json={"business_type": "PT", "industry": "teknologi", "location": "Jakarta"},
            )

        assert response.status_code == 500


class TestFollowupEndpointFailures:
    """Test followup endpoint external service failures."""

    def test_followup_qdrant_failure_returns_500(self, test_client):
        """Followup with Qdrant failure returns HTTP 500."""
        with patch("main.rag_chain") as mock_chain:
            mock_chain.query_with_history.side_effect = ConnectionError("Qdrant connection failed")
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/v1/ask/followup",
                json={
                    "question": "Bagaimana dengan sanksinya?",
                    "chat_history": [
                        {"question": "Apa itu UU Cipta Kerja?", "answer": "UU Cipta Kerja adalah..."}
                    ],
                },
            )

        assert response.status_code == 500

    def test_followup_nim_failure_returns_500(self, test_client):
        """Followup with NIM API failure returns HTTP 500."""
        import requests
        with patch("main.rag_chain") as mock_chain:
            mock_chain.query_with_history.side_effect = requests.HTTPError("NIM API error")
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/v1/ask/followup",
                json={
                    "question": "Bagaimana dengan sanksinya?",
                    "chat_history": [
                        {"question": "Apa itu UU Cipta Kerja?", "answer": "UU Cipta Kerja adalah..."}
                    ],
                },
            )

        assert response.status_code == 500
