"""
Tests for API v1 versioning.

Verifies that all endpoints are accessible under both /api/ (legacy)
and /api/v1/ (versioned) prefixes, and that OpenAPI metadata is enhanced.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from rag_chain import RAGResponse, ConfidenceScore, ValidationResult


# ---------------------------------------------------------------------------
# Helper — build a complete RAGResponse for mocking
# ---------------------------------------------------------------------------


def _mock_rag_response(answer: str = "Jawaban [1].", n_citations: int = 2) -> RAGResponse:
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
        confidence_score=ConfidenceScore(
            numeric=0.82, label="tinggi", top_score=0.9, avg_score=0.75
        ),
        raw_context="context",
        validation=ValidationResult(
            is_valid=True, citation_coverage=0.8, hallucination_risk="low"
        ),
    )


# ===========================================================================
# Test: API v1 routes mirror legacy /api/ routes
# ===========================================================================


class TestV1RoutesExist:
    """Verify that /api/v1/* routes are mounted and respond."""

    def test_v1_ask(self, test_client):
        """POST /api/v1/ask returns 200 with mocked RAG chain."""
        mock_resp = _mock_rag_response()
        with patch("main.rag_chain") as mock_chain:
            mock_chain.query.return_value = mock_resp
            resp = test_client.post(
                "/api/v1/ask",
                json={"question": "Apa itu PT?"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data

    def test_v1_ask_stream(self, test_client):
        """POST /api/v1/ask/stream returns 200 with streaming response."""
        with patch("main.rag_chain") as mock_chain:
            mock_chain.query_stream.return_value = iter([
                ("metadata", {"citations": [], "sources": []}),
                ("chunk", "Hello"),
                ("done", {"validation": None}),
            ])
            resp = test_client.post(
                "/api/v1/ask/stream",
                json={"question": "Apa itu PT?"},
            )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")
        body = resp.text
        assert "event: metadata" in body or "event: chunk" in body

    def test_v1_followup(self, test_client):
        """POST /api/v1/ask/followup returns 200."""
        mock_resp = _mock_rag_response()
        with patch("main.rag_chain") as mock_chain:
            mock_chain.query_with_history.return_value = mock_resp
            resp = test_client.post(
                "/api/v1/ask/followup",
                json={
                    "question": "Bagaimana dengan sanksinya?",
                    "chat_history": [
                        {"question": "Apa itu PT?", "answer": "PT adalah..."}
                    ],
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert "citations" in data

    def test_v1_document_types(self, test_client):
        """GET /api/v1/document-types returns document type list."""
        resp = test_client.get("/api/v1/document-types")
        assert resp.status_code == 200
        data = resp.json()
        assert "document_types" in data
        assert len(data["document_types"]) >= 5

    def test_v1_compliance_check(self, test_client):
        """POST /api/v1/compliance/check returns 200."""
        mock_resp = _mock_rag_response(
            answer="Bisnis ini kemungkinan PATUH. Tingkat risiko: rendah."
        )
        with patch("main.rag_chain") as mock_chain:
            mock_chain.query.return_value = mock_resp
            resp = test_client.post(
                "/api/v1/compliance/check",
                data={"business_description": "Saya ingin membuka restoran di Jakarta dengan NIB dan SIUP lengkap."},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "compliant" in data

    def test_v1_guidance(self, test_client):
        """POST /api/v1/guidance returns 200."""
        mock_resp = _mock_rag_response(
            answer="1. Pemesanan Nama PT melalui AHU Online\n2. Pembuatan Akta Notaris"
        )
        with patch("main.rag_chain") as mock_chain:
            mock_chain.aquery = AsyncMock(return_value=mock_resp)
            resp = test_client.post(
                "/api/v1/guidance",
                json={"business_type": "PT"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "business_type" in data


# ===========================================================================
# Test: Legacy /api/ routes still work (backward compatibility)
# ===========================================================================


class TestLegacyRoutesStillWork:
    """Verify /api/* routes are NOT broken by the v1 addition."""

    def test_legacy_ask(self, test_client):
        """POST /api/ask still works."""
        mock_resp = _mock_rag_response()
        with patch("main.rag_chain") as mock_chain:
            mock_chain.query.return_value = mock_resp
            resp = test_client.post(
                "/api/ask",
                json={"question": "Apa itu UU Cipta Kerja?"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert "citations" in data

    def test_legacy_document_types(self, test_client):
        """GET /api/document-types still works."""
        resp = test_client.get("/api/document-types")
        assert resp.status_code == 200

    def test_legacy_compliance(self, test_client):
        """POST /api/compliance/check still works."""
        mock_resp = _mock_rag_response()
        with patch("main.rag_chain") as mock_chain:
            mock_chain.query.return_value = mock_resp
            resp = test_client.post(
                "/api/compliance/check",
                data={"business_description": "Perusahaan perdagangan umum dengan NIB."},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "compliant" in data or "answer" in data


# ===========================================================================
# Test: OpenAPI metadata enhancement
# ===========================================================================


class TestOpenAPIMetadata:
    """Verify enhanced OpenAPI/Swagger metadata."""

    def test_openapi_title(self, test_client):
        """OpenAPI schema has correct title."""
        resp = test_client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert schema["info"]["title"] == "Omnibus Legal Compass API"

    def test_openapi_version(self, test_client):
        """OpenAPI schema shows version 1.0.0."""
        resp = test_client.get("/openapi.json")
        schema = resp.json()
        assert schema["info"]["version"] == "1.0.0"

    def test_openapi_contact(self, test_client):
        """OpenAPI schema includes contact info."""
        resp = test_client.get("/openapi.json")
        schema = resp.json()
        assert "contact" in schema["info"]
        assert "name" in schema["info"]["contact"]

    def test_openapi_license(self, test_client):
        """OpenAPI schema includes MIT license."""
        resp = test_client.get("/openapi.json")
        schema = resp.json()
        assert "license" in schema["info"]
        assert "MIT" in schema["info"]["license"]["name"]

    def test_openapi_tags(self, test_client):
        """OpenAPI schema includes tag descriptions."""
        resp = test_client.get("/openapi.json")
        schema = resp.json()
        assert "tags" in schema
        tag_names = {t["name"] for t in schema["tags"]}
        assert "System" in tag_names
        assert "Q&A" in tag_names

    def test_v1_paths_present(self, test_client):
        """OpenAPI schema includes /api/v1/ paths."""
        resp = test_client.get("/openapi.json")
        schema = resp.json()
        paths = list(schema["paths"].keys())
        v1_paths = [p for p in paths if p.startswith("/api/v1/")]
        assert len(v1_paths) >= 4, f"Expected >=4 v1 paths, got {v1_paths}"


# ===========================================================================
# Test: Both prefixes serve same data
# ===========================================================================


class TestBothPrefixesConsistent:
    """Verify /api/v1/* and /api/* return equivalent results."""

    def test_document_types_same(self, test_client):
        """Both /api/ and /api/v1/ return same document types."""
        legacy = test_client.get("/api/document-types").json()
        v1 = test_client.get("/api/v1/document-types").json()
        assert legacy == v1

    def test_ask_same_response(self, test_client):
        """Both /api/ask and /api/v1/ask return same answer for same question."""
        mock_resp = _mock_rag_response()
        question = {"question": "Apa itu NIB?"}

        with patch("main.rag_chain") as mock_chain:
            mock_chain.query.return_value = mock_resp
            legacy = test_client.post("/api/ask", json=question).json()

        with patch("main.rag_chain") as mock_chain:
            mock_chain.query.return_value = mock_resp
            v1 = test_client.post("/api/v1/ask", json=question).json()

        assert legacy["answer"] == v1["answer"]
        assert len(legacy["citations"]) == len(v1["citations"])
