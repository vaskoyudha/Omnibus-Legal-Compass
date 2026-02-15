"""
Tests for FastAPI API endpoints.

Uses TestClient with mocked Qdrant + NVIDIA NIM dependencies.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from rag_chain import RAGResponse, ConfidenceScore, ValidationResult
from retriever import SearchResult


# ---------------------------------------------------------------------------
# Helper — build a complete RAGResponse for mocking query()
# ---------------------------------------------------------------------------


def _mock_rag_response(answer="Jawaban [1].", n_citations=2) -> RAGResponse:
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


# ---------------------------------------------------------------------------
# Root & Health
# ---------------------------------------------------------------------------


class TestRootEndpoint:
    def test_root_returns_200(self, test_client):
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data or "message" in data or "status" in data

    def test_root_response_has_api_info(self, test_client):
        response = test_client.get("/")
        data = response.json()
        # Should contain project info
        assert isinstance(data, dict)


class TestHealthEndpoint:
    def test_health_returns_200(self, test_client):
        response = test_client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self, test_client):
        response = test_client.get("/health")
        data = response.json()
        assert "status" in data
        assert "qdrant_connected" in data
        assert "llm_configured" in data
        assert "version" in data


# ---------------------------------------------------------------------------
# Ask Endpoint
# ---------------------------------------------------------------------------


class TestAskEndpoint:
    def test_ask_valid_question(self, test_client):
        """POST /api/ask with valid question."""
        with patch("main.rag_chain") as mock_chain:
            mock_chain.query.return_value = _mock_rag_response()
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/ask",
                json={"question": "Apa itu Undang-Undang Cipta Kerja?"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "citations" in data
        assert "confidence" in data
        assert "processing_time_ms" in data

    def test_ask_short_question_returns_422(self, test_client):
        """POST /api/ask with too-short question → 422."""
        response = test_client.post("/api/ask", json={"question": "ab"})
        assert response.status_code == 422

    def test_ask_empty_body_returns_422(self, test_client):
        """POST /api/ask with empty body → 422."""
        response = test_client.post("/api/ask", json={})
        assert response.status_code == 422

    def test_ask_with_document_filter(self, test_client):
        """POST /api/ask with jenis_dokumen filter."""
        with patch("main.rag_chain") as mock_chain:
            mock_chain.query.return_value = _mock_rag_response()
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/ask",
                json={
                    "question": "Apa syarat pendirian PT?",
                    "jenis_dokumen": "UU",
                    "top_k": 3,
                },
            )

        data = response.json()
        assert "answer" in data
        assert "citations" in data
        assert isinstance(data["answer"], str)

    def test_ask_with_custom_top_k(self, test_client):
        """POST /api/ask with custom top_k."""
        with patch("main.rag_chain") as mock_chain:
            mock_chain.query.return_value = _mock_rag_response()
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/ask",
                json={"question": "Bagaimana proses izin usaha?", "top_k": 10},
            )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "citations" in data

    def test_ask_rag_chain_not_initialized(self, test_client):
        """POST /api/ask when rag_chain is None → 503."""
        with patch("main.rag_chain", None):
            response = test_client.post(
                "/api/ask",
                json={"question": "Apa itu Undang-Undang Cipta Kerja?"},
            )
        assert response.status_code == 503

    def test_ask_query_exception_returns_500(self, test_client):
        """POST /api/ask when query() throws → 500."""
        with patch("main.rag_chain") as mock_chain:
            mock_chain.query.side_effect = RuntimeError("LLM timeout")
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/ask",
                json={"question": "Apa itu Undang-Undang Cipta Kerja?"},
            )

        assert response.status_code == 500


# ---------------------------------------------------------------------------
# Followup Endpoint
# ---------------------------------------------------------------------------


class TestFollowupEndpoint:
    def test_followup_valid_request(self, test_client):
        """POST /api/ask/followup with valid body."""
        with patch("main.rag_chain") as mock_chain:
            mock_chain.query_with_history.return_value = _mock_rag_response()
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/ask/followup",
                json={
                    "question": "Bagaimana dengan sanksinya?",
                    "chat_history": [
                        {"question": "Apa itu UU Cipta Kerja?", "answer": "UU Cipta Kerja adalah..."}
                    ],
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "citations" in data

    def test_followup_rag_chain_not_initialized(self, test_client):
        """POST /api/ask/followup when rag_chain is None → 503."""
        with patch("main.rag_chain", None):
            response = test_client.post(
                "/api/ask/followup",
                json={
                    "question": "Bagaimana?",
                    "chat_history": [],
                },
            )
        assert response.status_code == 503

    def test_followup_exception_returns_500(self, test_client):
        """POST /api/ask/followup when query_with_history throws → 500."""
        with patch("main.rag_chain") as mock_chain:
            mock_chain.query_with_history.side_effect = RuntimeError("fail")
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/ask/followup",
                json={
                    "question": "Bagaimana dengan sanksinya?",
                    "chat_history": [],
                },
            )

        assert response.status_code == 500


# ---------------------------------------------------------------------------
# Streaming Endpoint
# ---------------------------------------------------------------------------


class TestStreamingEndpoint:
    def test_stream_rag_chain_not_initialized(self, test_client):
        """POST /api/ask/stream when rag_chain is None → 503."""
        with patch("main.rag_chain", None):
            response = test_client.post(
                "/api/ask/stream",
                json={"question": "Apa itu Undang-Undang Cipta Kerja?"},
            )
        assert response.status_code == 503

    def test_stream_returns_sse_events(self, test_client):
        """POST /api/ask/stream should return SSE events."""
        with patch("main.rag_chain") as mock_chain:
            mock_chain.query_stream.return_value = iter([
                ("metadata", {"citations": [], "sources": []}),
                ("chunk", "Hello "),
                ("chunk", "World"),
                ("done", {"validation": {"is_valid": True}}),
            ])
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/ask/stream",
                json={"question": "Apa itu Undang-Undang Cipta Kerja?"},
            )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        body = response.text
        assert "event: metadata" in body
        assert "event: chunk" in body
        assert "event: done" in body


# ---------------------------------------------------------------------------
# Document Types
# ---------------------------------------------------------------------------


class TestDocumentTypesEndpoint:
    def test_get_document_types(self, test_client):
        response = test_client.get("/api/document-types")
        assert response.status_code == 200
        data = response.json()
        assert "document_types" in data
        types = data["document_types"]
        assert len(types) >= 5
        codes = [t["code"] for t in types]
        assert "UU" in codes
        assert "PP" in codes


# ---------------------------------------------------------------------------
# Compliance Endpoint
# ---------------------------------------------------------------------------


class TestComplianceEndpoint:
    def test_compliance_with_text(self, test_client):
        """POST /api/compliance/check with text description."""
        with patch("main.rag_chain") as mock_chain:
            mock_resp = _mock_rag_response("Bisnis ini perlu izin [1].")
            mock_chain.query.return_value = mock_resp
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/compliance/check",
                data={"business_description": "Saya ingin membuka usaha restoran di Jakarta"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "compliant" in data or "risk_level" in data or "summary" in data

    def test_compliance_no_input_returns_error(self, test_client):
        """POST /api/compliance/check with no input → error."""
        response = test_client.post("/api/compliance/check")
        # Should return 400 or 422 for missing input
        assert response.status_code in (400, 422, 503)

    def test_compliance_rag_chain_not_initialized(self, test_client):
        """POST /api/compliance/check when rag_chain is None → 503."""
        with patch("main.rag_chain", None):
            response = test_client.post(
                "/api/compliance/check",
                data={"business_description": "Restoran Jakarta"},
            )
        assert response.status_code == 503

    def test_compliance_high_risk(self, test_client):
        """POST /api/compliance/check with high risk response."""
        with patch("main.rag_chain") as mock_chain:
            mock_resp = _mock_rag_response(
                "Analisis ini menunjukkan bisnis TIDAK PATUH.\n"
                "Tingkat Risiko: tinggi\n"
                "Masalah yang terdeteksi: tidak memiliki izin.\n"
                "Rekomendasi:\n"
                "- Daftarkan izin usaha melalui OSS\n"
                "- Konsultasikan dengan notaris\n"
                "- Ajukan NPWP perusahaan"
            )
            mock_chain.query.return_value = mock_resp
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/compliance/check",
                data={"business_description": "Saya membuka usaha tanpa izin"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["risk_level"] == "tinggi"
        assert data["compliant"] is False
        assert len(data["recommendations"]) > 0

    def test_compliance_low_risk(self, test_client):
        """POST /api/compliance/check with low risk response."""
        with patch("main.rag_chain") as mock_chain:
            mock_resp = _mock_rag_response(
                "Bisnis ini PATUH dengan peraturan.\nTingkat Risiko: rendah"
            )
            mock_chain.query.return_value = mock_resp
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/compliance/check",
                data={"business_description": "Usaha kecil rumahan di Jakarta"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["risk_level"] == "rendah"
        assert data["compliant"] is True

    def test_compliance_exception(self, test_client):
        """POST /api/compliance/check when query throws → 500."""
        with patch("main.rag_chain") as mock_chain:
            mock_chain.query.side_effect = RuntimeError("LLM fail")
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/compliance/check",
                data={"business_description": "Usaha restoran di Jakarta"},
            )

        assert response.status_code == 500

    def test_compliance_short_description_returns_400(self, test_client):
        """POST /api/compliance/check with too-short text → 400."""
        with patch("main.rag_chain") as mock_chain:
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/compliance/check",
                data={"business_description": "ab"},
            )

        assert response.status_code == 400

    def test_compliance_truncates_long_input(self, test_client):
        """POST /api/compliance/check with very long text still works."""
        with patch("main.rag_chain") as mock_chain:
            mock_resp = _mock_rag_response("Hasil patuh. Risiko rendah.")
            mock_chain.query.return_value = mock_resp
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            long_text = "Deskripsi bisnis yang sangat panjang " * 500
            response = test_client.post(
                "/api/compliance/check",
                data={"business_description": long_text},
            )

        assert response.status_code == 200
        data = response.json()
        assert "compliant" in data or "answer" in data


# ---------------------------------------------------------------------------
# Guidance Endpoint
# ---------------------------------------------------------------------------


class TestGuidanceEndpoint:
    def test_guidance_valid_request(self, test_client):
        """POST /api/guidance with valid business type."""
        with patch("main.rag_chain") as mock_chain:
            mock_resp = _mock_rag_response(
                "Langkah 1: Pemesanan Nama PT melalui AHU Online.\n"
                "Langkah 2: Akta Pendirian oleh Notaris.\n"
                "Langkah 3: Pengesahan SK Kemenkumham.\n"
                "NIB diperlukan melalui OSS. [1]"
            )
            mock_chain.query.return_value = mock_resp
            mock_chain.aquery = AsyncMock(return_value=mock_resp)
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/guidance",
                json={
                    "business_type": "PT",
                    "industry": "teknologi",
                    "location": "Jakarta",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "business_type" in data
        assert "steps" in data or "summary" in data

    def test_guidance_missing_type_returns_422(self, test_client):
        """POST /api/guidance with missing business_type → 422."""
        response = test_client.post("/api/guidance", json={})
        assert response.status_code == 422

    def test_guidance_rag_chain_not_initialized(self, test_client):
        """POST /api/guidance when rag_chain is None → 503."""
        with patch("main.rag_chain", None):
            response = test_client.post(
                "/api/guidance",
                json={"business_type": "PT"},
            )
        assert response.status_code == 503

    def test_guidance_cv_type(self, test_client):
        """POST /api/guidance with CV type."""
        with patch("main.rag_chain") as mock_chain:
            mock_resp = _mock_rag_response("1. Buat akta CV\n2. Daftarkan ke pengadilan")
            mock_chain.aquery = AsyncMock(return_value=mock_resp)
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/guidance",
                json={"business_type": "CV"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["business_type"] == "CV"

    def test_guidance_type_mapping_perseroan(self, test_client):
        """POST /api/guidance with 'PERSEROAN' maps to PT."""
        with patch("main.rag_chain") as mock_chain:
            mock_resp = _mock_rag_response("1. Langkah pertama\n")
            mock_chain.aquery = AsyncMock(return_value=mock_resp)
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/guidance",
                json={"business_type": "PERSEROAN"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["business_type"] == "PT"

    def test_guidance_exception_returns_500(self, test_client):
        """POST /api/guidance when aquery throws → 500."""
        with patch("main.rag_chain") as mock_chain:
            mock_chain.aquery = AsyncMock(side_effect=RuntimeError("fail"))
            mock_chain.llm_client = MagicMock()
            mock_chain.retriever = MagicMock()
            mock_chain.retriever.client = MagicMock()

            response = test_client.post(
                "/api/guidance",
                json={"business_type": "PT"},
            )

        assert response.status_code == 500


# ---------------------------------------------------------------------------
# Utility function tests
# ---------------------------------------------------------------------------


class TestExtractPermits:
    """Test the extract_permits helper function."""

    def test_extract_known_permits(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from main import extract_permits

        answer = "Untuk mendirikan PT, diperlukan NIB dan SIUP serta NPWP perusahaan."
        permits = extract_permits(answer)
        assert "NIB" in permits or "NIB (Nomor Induk Berusaha)" in permits
        assert "SIUP" in permits
        assert "NPWP" in permits

    def test_extract_permits_adds_nib(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from main import extract_permits

        answer = "Usaha memerlukan SIUP untuk beroperasi."
        permits = extract_permits(answer)
        # NIB should be auto-added
        nib_found = any("NIB" in p for p in permits)
        assert nib_found

    def test_extract_permits_limits_to_10(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from main import extract_permits

        # include many keywords
        answer = "NIB SIUP TDP NPWP SKT SKDP IMB OSS AMDAL UKL-UPL Izin Usaha Izin Lokasi Sertifikat"
        permits = extract_permits(answer)
        assert len(permits) <= 10


class TestParseGuidanceSteps:
    """Test the parse_guidance_steps helper function."""

    def test_parse_numbered_steps(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from main import parse_guidance_steps

        answer = (
            "1. Pemesanan Nama PT\n"
            "Ajukan pemesanan nama melalui AHU Online.\n\n"
            "2. Akta Pendirian\n"
            "Buat akta pendirian oleh notaris."
        )
        steps = parse_guidance_steps(answer)
        assert len(steps) >= 1
        assert steps[0].step_number == 1

    def test_parse_empty_answer(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from main import parse_guidance_steps

        steps = parse_guidance_steps("")
        assert isinstance(steps, list)

    def test_parse_step_with_requirements(self):
        """Steps with bullet items should extract requirements."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from main import parse_guidance_steps

        answer = (
            "1. Persiapan Dokumen\n"
            "Siapkan dokumen berikut:\n"
            "- KTP seluruh pendiri\n"
            "- NPWP masing-masing pendiri\n"
            "- Bukti setor modal"
        )
        steps = parse_guidance_steps(answer)
        assert len(steps) >= 1
        assert len(steps[0].requirements) >= 2

    def test_parse_step_with_time_estimate(self):
        """Steps mentioning 'waktu' or 'hari' should extract time estimate."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from main import parse_guidance_steps

        answer = (
            "1. Pendaftaran Online\n"
            "Daftarkan melalui sistem OSS.\n"
            "Estimasi waktu: 3-5 hari kerja\n"
        )
        steps = parse_guidance_steps(answer)
        assert len(steps) >= 1
        assert "hari" in steps[0].estimated_time.lower() or "waktu" in steps[0].estimated_time.lower()

    def test_parse_step_with_fee_info(self):
        """Steps mentioning 'biaya' or 'Rp' should extract fees."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from main import parse_guidance_steps

        answer = (
            "1. Pembuatan Akta Notaris\n"
            "Buat akta pendirian.\n"
            "Biaya notaris sekitar Rp 2.000.000\n"
        )
        steps = parse_guidance_steps(answer)
        assert len(steps) >= 1
        assert steps[0].fees is not None
        assert "Rp" in steps[0].fees or "biaya" in steps[0].fees.lower()

    def test_parse_langkah_header_format(self):
        """Parse 'Langkah X:' format headers."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from main import parse_guidance_steps

        answer = (
            "Langkah 1: Pemesanan Nama\n"
            "Ajukan nama PT.\n"
            "Langkah 2: Akta Pendirian\n"
            "Buat akta."
        )
        steps = parse_guidance_steps(answer)
        assert len(steps) == 2

    def test_parse_bold_header_format(self):
        """Parse **1. Title** format headers."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from main import parse_guidance_steps

        answer = (
            "**1. Pemesanan Nama PT**\n"
            "Ajukan melalui AHU Online.\n"
            "**2. Akta Pendirian**\n"
            "Buat akta di notaris."
        )
        steps = parse_guidance_steps(answer)
        assert len(steps) == 2


class TestExtractJsonFromResponse:
    """Tests for _extract_json_from_response utility."""

    def test_extract_json_code_fence(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from main import _extract_json_from_response

        answer = (
            "Berikut analisis singkat.\n"
            "```json\n"
            "{\"status\": \"compliant\", \"risk_level\": \"rendah\", \"summary\": \"Semua baik\"}\n"
            "```"
        )
        parsed = _extract_json_from_response(answer)
        assert isinstance(parsed, dict)
        assert parsed.get("status") == "compliant"
        assert parsed.get("risk_level") == "rendah"

    def test_extract_json_bare_object(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from main import _extract_json_from_response

        answer = "Analisis akhir. {\"status\": \"non_compliant\", \"risk_level\": \"tinggi\"}"
        parsed = _extract_json_from_response(answer)
        assert isinstance(parsed, dict)
        assert parsed["status"] == "non_compliant"
        assert parsed["risk_level"] == "tinggi"

    def test_extract_json_no_json(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from main import _extract_json_from_response

        answer = "Ini hanyalah teks biasa tanpa JSON terstruktur. Tidak ada data." 
        parsed = _extract_json_from_response(answer)
        assert parsed is None

    def test_extract_json_invalid(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from main import _extract_json_from_response

        # Malformed JSON inside code fence should return None
        answer = (
            "Penjelasan...\n```json\n{\"status\": \"compliant\", \"risk_level\": rendah}\n```")
        parsed = _extract_json_from_response(answer)
        assert parsed is None

    def test_extract_json_nested_braces(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from main import _extract_json_from_response

        # JSON with nested objects should parse correctly
        answer = (
            "Detail: ...\n```json\n"
            "{\"status\": \"non_compliant\", \"risk_level\": \"medium\", "
            "\"details\": {\"found\": true, \"counts\": {\"issues\": 2}}}\n"
            "```"
        )
        parsed = _extract_json_from_response(answer)
        assert isinstance(parsed, dict)
        assert parsed.get("details", {}).get("counts", {}).get("issues") == 2


class TestParseComplianceResponse:
    """Tests for _parse_compliance_response covering JSON-mode and regex fallback."""

    def test_json_mode_compliant(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from main import _parse_compliance_response

        answer = (
            "Ringkasan: bisnis terlihat patuh.\n```json\n"
            "{\"status\": \"compliant\", \"risk_level\": \"rendah\", "
            "\"summary\": \"Tidak ditemukan isu signifikan\", \"issues\": [], \"recommendations\": []}"
            "\n```"
        )
        is_compliant, risk_level, summary, issues, recommendations = _parse_compliance_response(answer)
        assert is_compliant is True
        assert risk_level == "rendah"
        assert isinstance(summary, str)
        assert len(issues) == 0
        assert recommendations == []

    def test_json_mode_non_compliant(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from main import _parse_compliance_response

        answer = (
            "Analisis: ditemukan pelanggaran.\n```json\n"
            "{\"status\": \"non_compliant\", \"risk_level\": \"tinggi\", "
            "\"summary\": \"Tidak memiliki izin usaha\", "
            "\"issues\": [{\"issue\": \"Tidak memiliki izin\", \"severity\": \"tinggi\", \"regulation\": \"UU No. X\", \"pasal\": null, \"recommendation\": \"Segera urus izin\"}], "
            "\"recommendations\": [\"Daftarkan izin usaha melalui OSS\"]}"
            "\n```"
        )
        is_compliant, risk_level, summary, issues, recommendations = _parse_compliance_response(answer)
        assert is_compliant is False
        assert risk_level == "tinggi"
        assert "izin" in summary.lower()
        assert len(issues) == 1
        assert issues[0].issue == "Tidak memiliki izin"
        assert issues[0].severity == "tinggi"
        assert isinstance(recommendations, list) and len(recommendations) == 1

    def test_json_mode_english_risk_level(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from main import _parse_compliance_response

        answer = (
            "Detail: ...\n```json\n"
            "{\"status\": \"non_compliant\", \"risk_level\": \"high\", \"summary\": \"Masalah serius\", \"issues\": [], \"recommendations\": []}"
            "\n```"
        )
        is_compliant, risk_level, summary, issues, recommendations = _parse_compliance_response(answer)
        assert is_compliant is False
        assert risk_level == "tinggi"

    def test_regex_fallback_patuh(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from main import _parse_compliance_response

        answer = "Hasil: BISNIS INI PATUH. Tingkat Risiko: rendah. Tidak ada rekomendasi khusus."
        is_compliant, risk_level, summary, issues, recommendations = _parse_compliance_response(answer)
        assert is_compliant is True
        assert risk_level == "rendah"

    def test_regex_fallback_tidak_patuh(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from main import _parse_compliance_response

        answer = (
            "Analisis menunjukkan: TIDAK PATUH.\nTingkat Risiko: tinggi\n"
            "Rekomendasi:\n- Daftarkan izin usaha melalui OSS segera\n- Konsultasikan dengan notaris untuk akta pendirian\n"
        )
        is_compliant, risk_level, summary, issues, recommendations = _parse_compliance_response(answer)
        assert is_compliant is False
        assert risk_level == "tinggi"
        assert len(recommendations) >= 2
        assert any("OSS" in r for r in recommendations)

    def test_regex_fallback_default_risk(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from main import _parse_compliance_response

        answer = "Analisis singkat tanpa menyebut tingkat risiko atau kata kunci risiko lainnya."
        is_compliant, risk_level, summary, issues, recommendations = _parse_compliance_response(answer)
        assert risk_level == "sedang"


class TestParseGuidanceResponse:
    """Tests for _parse_guidance_response covering JSON-mode and regex fallback."""

    def test_json_mode_with_steps(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from main import _parse_guidance_response

        answer = (
            "Penjelasan...\n```json\n"
            "{\"steps\": [ {\"title\": \"Pemesanan Nama\", \"description\": \"Ajukan nama PT.\", \"requirements\": [\"KTP\", \"NPWP\"], \"estimated_time\": \"1-2 minggu\", \"fees\": \"Rp 1.000.000\"} ] }\n```")
        steps = _parse_guidance_response(answer)
        assert isinstance(steps, list)
        assert len(steps) >= 1
        s = steps[0]
        assert s.step_number == 1
        assert "Pemesanan Nama" in s.title
        assert "Ajukan nama" in s.description
        assert s.requirements == ["KTP", "NPWP"]
        assert "1-2 minggu" in s.estimated_time
        assert s.fees == "Rp 1.000.000"

    def test_json_mode_empty_steps(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from main import _parse_guidance_response

        # JSON with empty steps should fall back to regex parsing of textual steps
        answer = (
            "Berikut panduan singkat:\n1. Pemesanan Nama\nAjukan pemesanan nama melalui AHU Online.\n```")
        # Append an explicit empty JSON block
        answer += "\n```json\n{\"steps\": []}\n```"

        steps = _parse_guidance_response(answer)
        assert isinstance(steps, list)
        assert len(steps) >= 1
        assert steps[0].step_number == 1

    def test_regex_fallback(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from main import _parse_guidance_response

        answer = (
            "1. Pemesanan Nama PT\nAjukan pemesanan nama melalui AHU Online.\n\n"
            "2. Akta Pendirian\nBuat akta pendirian oleh notaris."
        )
        steps = _parse_guidance_response(answer)
        assert isinstance(steps, list)
        assert len(steps) >= 2
        assert steps[0].step_number == 1
        assert steps[1].step_number == 2

    def test_json_mode_multiple_steps(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from main import _parse_guidance_response

        answer = (
            "Intro...\n```json\n{\"steps\": ["
            "{\"title\": \"Langkah Satu\", \"description\": \"Deskripsi 1\", \"requirements\": [], \"estimated_time\": \"1 minggu\", \"fees\": null},"
            "{\"title\": \"Langkah Dua\", \"description\": \"Deskripsi 2\", \"requirements\": [], \"estimated_time\": \"2 minggu\", \"fees\": null},"
            "{\"title\": \"Langkah Tiga\", \"description\": \"Deskripsi 3\", \"requirements\": [], \"estimated_time\": \"3 minggu\", \"fees\": null}"
            "]}\n```"
        )
        steps = _parse_guidance_response(answer)
        assert isinstance(steps, list)
        assert len(steps) == 3
        assert steps[0].step_number == 1
        assert steps[1].step_number == 2
        assert steps[2].step_number == 3
