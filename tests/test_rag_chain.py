"""
Tests for LegalRAGChain — confidence scoring, hallucination detection, prompt construction.

Uses mocked NVIDIA NIM and retriever to avoid external dependencies.
"""

import pytest
from unittest.mock import MagicMock, patch

from rag_chain import (
    ConfidenceScore,
    LegalRAGChain,
    NVIDIANimClient,
    RAGResponse,
    ValidationResult,
)
from retriever import SearchResult


# ---------------------------------------------------------------------------
# Dataclass unit tests
# ---------------------------------------------------------------------------


class TestConfidenceScore:
    """Tests for ConfidenceScore dataclass."""

    def test_creation(self):
        cs = ConfidenceScore(numeric=0.85, label="tinggi", top_score=0.9, avg_score=0.7)
        assert cs.numeric == 0.85
        assert cs.label == "tinggi"

    def test_to_dict(self):
        cs = ConfidenceScore(numeric=0.8512, label="tinggi", top_score=0.91, avg_score=0.72)
        d = cs.to_dict()
        assert isinstance(d, dict)
        assert d["numeric"] == 0.8512
        assert d["label"] == "tinggi"
        assert "top_score" in d and "avg_score" in d

    def test_zero_confidence(self):
        cs = ConfidenceScore(numeric=0.0, label="tidak ada", top_score=0.0, avg_score=0.0)
        assert cs.to_dict()["numeric"] == 0.0


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_valid_result(self):
        vr = ValidationResult(is_valid=True, citation_coverage=0.8, hallucination_risk="low")
        assert vr.is_valid is True
        assert vr.hallucination_risk == "low"

    def test_invalid_with_warnings(self):
        vr = ValidationResult(
            is_valid=False,
            citation_coverage=0.2,
            warnings=["Missing source"],
            hallucination_risk="high",
            missing_citations=[4, 5],
        )
        assert vr.is_valid is False
        assert len(vr.warnings) == 1
        assert vr.missing_citations == [4, 5]

    def test_to_dict(self):
        vr = ValidationResult(is_valid=True, citation_coverage=0.75)
        d = vr.to_dict()
        assert d["is_valid"] is True
        assert d["citation_coverage"] == 0.75
        assert "warnings" in d


class TestRAGResponse:
    """Tests for RAGResponse dataclass."""

    def test_creation_full(self):
        cs = ConfidenceScore(numeric=0.8, label="tinggi", top_score=0.9, avg_score=0.7)
        vr = ValidationResult(is_valid=True, citation_coverage=0.8)
        r = RAGResponse(
            answer="Test answer",
            citations=[{"number": 1, "citation": "UU 40/2007"}],
            sources=["[1] UU 40/2007"],
            confidence="tinggi",
            confidence_score=cs,
            raw_context="context",
            validation=vr,
        )
        assert r.answer == "Test answer"
        assert r.confidence == "tinggi"
        assert r.confidence_score.numeric == 0.8

    def test_creation_minimal(self):
        r = RAGResponse(
            answer="No result",
            citations=[],
            sources=[],
            confidence="tidak ada",
            confidence_score=None,
            raw_context="",
        )
        assert r.validation is None
        assert r.confidence_score is None


# ---------------------------------------------------------------------------
# NVIDIANimClient tests (mocked HTTP)
# ---------------------------------------------------------------------------


class TestNVIDIANimClient:
    """Tests for NVIDIANimClient with mocked requests."""

    @patch("llm_client.requests.post")
    def test_generate_returns_content(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Jawaban hukum"}}]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client = NVIDIANimClient(api_key="test-key")
        result = client.generate("Apa itu PT?")
        assert result == "Jawaban hukum"
        mock_post.assert_called_once()

    @patch("llm_client.requests.post")
    def test_generate_with_system_message(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "answer"}}]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client = NVIDIANimClient(api_key="test-key")
        client.generate("q", system_message="You are a lawyer")
        # verify system message was included
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        messages = payload["messages"]
        assert messages[0]["role"] == "system"

    @patch("llm_client.requests.post")
    def test_generate_handles_reasoning_content(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"reasoning_content": "reasoning answer", "content": None}}]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client = NVIDIANimClient(api_key="test-key")
        result = client.generate("q")
        assert result == "reasoning answer"

    @patch("llm_client.time.sleep")
    @patch("llm_client.requests.post")
    def test_generate_api_error(self, mock_post, mock_sleep):
        import requests as req
        mock_post.side_effect = req.exceptions.ConnectionError("timeout")

        client = NVIDIANimClient(api_key="test-key")
        with pytest.raises(RuntimeError, match="Gagal mendapatkan respons"):
            client.generate("q")
        # Verify retry was attempted (3 total calls, 2 sleeps)
        assert mock_post.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("llm_client.requests.post")
    def test_generate_stream_yields_chunks(self, mock_post):
        # Simulate SSE stream
        lines = [
            b'data: {"choices":[{"delta":{"content":"chunk1"}}]}',
            b'data: {"choices":[{"delta":{"content":"chunk2"}}]}',
            b'data: [DONE]',
        ]
        mock_resp = MagicMock()
        mock_resp.iter_lines.return_value = lines
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client = NVIDIANimClient(api_key="test-key")
        chunks = list(client.generate_stream("q"))
        assert chunks == ["chunk1", "chunk2"]

    def test_init_without_key_raises(self):
        with patch("llm_client.NVIDIA_API_KEY", None):
            with pytest.raises(ValueError, match="NVIDIA_API_KEY"):
                NVIDIANimClient(api_key=None)


# ---------------------------------------------------------------------------
# LegalRAGChain tests (mocked retriever + LLM)
# ---------------------------------------------------------------------------


def _make_results(n=3, score_base=0.8, doc_type="UU"):
    """Helper to create n SearchResult objects."""
    return [
        SearchResult(
            id=i,
            text=f"Pasal {i} tentang hukum Indonesia",
            citation=f"UU No. {i} Tahun 2020, Pasal {i}",
            citation_id=f"uu-{i}-2020-pasal-{i}",
            score=max(0.1, score_base - (i * 0.1)),
            metadata={"jenis_dokumen": doc_type, "tahun": 2020},
        )
        for i in range(1, n + 1)
    ]


class TestAssessConfidence:
    """Tests for LegalRAGChain._assess_confidence."""

    def _make_chain(self):
        mock_r = MagicMock()
        mock_l = MagicMock()
        return LegalRAGChain(retriever=mock_r, llm_client=mock_l)

    def test_empty_results(self):
        chain = self._make_chain()
        cs = chain._assess_confidence([])
        assert cs.numeric == 0.0
        assert cs.label == "tidak ada"

    def test_high_confidence(self):
        chain = self._make_chain()
        results = _make_results(4, score_base=0.9, doc_type="UU")
        cs = chain._assess_confidence(results)
        assert cs.label == "tinggi"
        assert cs.numeric >= 0.5

    def test_low_confidence(self):
        chain = self._make_chain()
        results = _make_results(1, score_base=0.15, doc_type="Perda")
        cs = chain._assess_confidence(results)
        assert cs.label in ("rendah", "sedang")
        assert cs.numeric < 0.65

    def test_single_result_moderate(self):
        chain = self._make_chain()
        results = _make_results(1, score_base=0.5)
        cs = chain._assess_confidence(results)
        assert 0.0 < cs.numeric <= 1.0


class TestValidateAnswer:
    """Tests for LegalRAGChain._validate_answer."""

    def _make_chain(self):
        return LegalRAGChain(retriever=MagicMock(), llm_client=MagicMock())

    def test_valid_answer_with_citations(self):
        chain = self._make_chain()
        citations = [
            {"number": 1, "citation": "UU 40/2007"},
            {"number": 2, "citation": "PP 5/2021"},
        ]
        vr = chain._validate_answer("Jawaban berdasarkan [1] dan [2].", citations)
        assert vr.is_valid is True
        assert vr.hallucination_risk == "low"
        assert vr.citation_coverage == 1.0

    def test_no_citations_high_risk(self):
        chain = self._make_chain()
        citations = [{"number": 1, "citation": "UU"}]
        vr = chain._validate_answer("Jawaban tanpa sitasi apapun.", citations)
        assert vr.hallucination_risk == "high"

    def test_invalid_citation_references(self):
        chain = self._make_chain()
        citations = [{"number": 1, "citation": "UU"}]
        vr = chain._validate_answer("Menurut [1] dan [5].", citations)
        assert vr.hallucination_risk == "medium"
        assert 5 in vr.missing_citations

    def test_partial_coverage(self):
        chain = self._make_chain()
        citations = [
            {"number": 1, "citation": "UU1"},
            {"number": 2, "citation": "UU2"},
            {"number": 3, "citation": "UU3"},
            {"number": 4, "citation": "UU4"},
        ]
        vr = chain._validate_answer("Berdasarkan [1].", citations)
        assert vr.citation_coverage == 0.25


class TestFormatContext:
    """Tests for LegalRAGChain._format_context."""

    def test_format_context_basic(self):
        chain = LegalRAGChain(retriever=MagicMock(), llm_client=MagicMock())
        results = _make_results(2)
        context, citations = chain._format_context(results)
        assert "[1]" in context
        assert "[2]" in context
        assert len(citations) == 2
        assert citations[0]["number"] == 1
        assert citations[0]["score"] > 0

    def test_format_context_empty(self):
        chain = LegalRAGChain(retriever=MagicMock(), llm_client=MagicMock())
        context, citations = chain._format_context([])
        assert context == ""
        assert citations == []


class TestQueryEndToEnd:
    """Tests for LegalRAGChain.query with mocked deps."""

    def test_query_no_results(self):
        mock_r = MagicMock()
        mock_r.hybrid_search.return_value = []
        mock_l = MagicMock()
        chain = LegalRAGChain(retriever=mock_r, llm_client=mock_l)

        resp = chain.query("Pertanyaan tanpa hasil")
        assert "tidak menemukan" in resp.answer
        assert resp.confidence == "tidak ada"
        assert resp.citations == []
        mock_l.generate.assert_not_called()

    def test_query_with_results(self):
        results = _make_results(3)
        mock_r = MagicMock()
        mock_r.hybrid_search.return_value = results
        mock_l = MagicMock()
        mock_l.generate.return_value = "Berdasarkan [1] dan [2], jawabannya..."

        chain = LegalRAGChain(retriever=mock_r, llm_client=mock_l)
        resp = chain.query("Apa itu PT?")

        assert resp.answer == "Berdasarkan [1] dan [2], jawabannya..."
        assert len(resp.citations) == 3
        assert len(resp.sources) == 3
        assert resp.confidence in ("tinggi", "sedang", "rendah")
        # generate is called twice: once for main answer, once for grounding check (Task 1.3)
        assert mock_l.generate.call_count == 2

    def test_query_with_document_filter(self):
        results = _make_results(2)
        mock_r = MagicMock()
        mock_r.search_by_document_type.return_value = results
        mock_l = MagicMock()
        mock_l.generate.return_value = "Jawaban [1]."

        chain = LegalRAGChain(retriever=mock_r, llm_client=mock_l)
        resp = chain.query("Apa itu PT?", filter_jenis_dokumen="UU")
        mock_r.search_by_document_type.assert_called_once()
        assert resp.answer == "Jawaban [1]."

    def test_query_with_history(self):
        mock_r = MagicMock()
        mock_r.hybrid_search.return_value = _make_results(2)
        mock_l = MagicMock()
        mock_l.generate.return_value = "Follow up [1]."

        chain = LegalRAGChain(retriever=mock_r, llm_client=mock_l)
        history = [{"question": "Apa itu PT?", "answer": "PT adalah..."}]
        resp = chain.query_with_history("Bagaimana cara mendirikannya?", chat_history=history)
        assert resp.answer == "Follow up [1]."

    def test_query_stream_no_results(self):
        mock_r = MagicMock()
        mock_r.hybrid_search.return_value = []
        mock_l = MagicMock()
        chain = LegalRAGChain(retriever=mock_r, llm_client=mock_l)

        events = list(chain.query_stream("no results"))
        assert len(events) >= 2
        assert events[0][0] == "metadata"
        assert events[1][0] == "chunk"

    def test_query_stream_with_results(self):
        mock_r = MagicMock()
        mock_r.hybrid_search.return_value = _make_results(2)
        mock_l = MagicMock()
        mock_l.generate_stream.return_value = iter(["chunk1", "chunk2"])
        chain = LegalRAGChain(retriever=mock_r, llm_client=mock_l)

        events = list(chain.query_stream("Apa itu?"))
        event_types = [e[0] for e in events]
        assert "metadata" in event_types
        assert "chunk" in event_types
        assert "done" in event_types


# ---------------------------------------------------------------------------
# JSON metadata extraction tests (Task 2.1)
# ---------------------------------------------------------------------------


class TestExtractJsonMetadata:
    """Tests for LegalRAGChain._extract_json_metadata."""

    def test_extract_json_with_code_fence(self):
        """JSON block wrapped in ```json ... ``` at end of answer."""
        raw = (
            "Pendirian PT diatur dalam UU No. 40 Tahun 2007 [1].\n\n"
            "```json\n"
            '{"cited_sources": [1, 2]}\n'
            "```"
        )
        clean, meta = LegalRAGChain._extract_json_metadata(raw)
        assert meta is not None
        assert meta["cited_sources"] == [1, 2]
        assert "```json" not in clean
        assert "Pendirian PT" in clean

    def test_extract_json_bare_object(self):
        """Bare JSON object at end without code fence."""
        raw = (
            "Jawaban berdasarkan [1] dan [2].\n\n"
            '{"cited_sources": [1, 2, 3]}'
        )
        clean, meta = LegalRAGChain._extract_json_metadata(raw)
        assert meta is not None
        assert meta["cited_sources"] == [1, 2, 3]
        assert "Jawaban berdasarkan" in clean

    def test_extract_json_no_json_present(self):
        """No JSON block in the answer — returns None."""
        raw = "Jawaban sederhana tanpa JSON apapun [1]."
        clean, meta = LegalRAGChain._extract_json_metadata(raw)
        assert meta is None
        assert clean == raw

    def test_extract_json_invalid_json(self):
        """Malformed JSON block — returns None for metadata."""
        raw = (
            "Jawaban [1].\n\n"
            "```json\n"
            '{"cited_sources": [1, 2,}\n'  # invalid JSON
            "```"
        )
        clean, meta = LegalRAGChain._extract_json_metadata(raw)
        assert meta is None

    def test_extract_json_empty_sources(self):
        """JSON with empty cited_sources array."""
        raw = (
            "Jawaban tanpa sitasi.\n\n"
            "```json\n"
            '{"cited_sources": []}\n'
            "```"
        )
        clean, meta = LegalRAGChain._extract_json_metadata(raw)
        assert meta is not None
        assert meta["cited_sources"] == []


class TestValidateAnswerWithJsonSources:
    """Tests for _validate_answer with json_cited_sources parameter."""

    def _make_chain(self):
        return LegalRAGChain(retriever=MagicMock(), llm_client=MagicMock())

    def test_json_sources_used_when_provided(self):
        """When json_cited_sources is provided, use it instead of regex."""
        chain = self._make_chain()
        citations = [
            {"number": 1, "citation": "UU 40/2007"},
            {"number": 2, "citation": "PP 5/2021"},
        ]
        # Answer text has [1] only, but JSON says [1, 2]
        vr = chain._validate_answer(
            "Jawaban berdasarkan [1].",
            citations,
            json_cited_sources=[1, 2],
        )
        assert vr.citation_coverage == 1.0  # Both sources cited via JSON
        assert vr.hallucination_risk == "low"

    def test_regex_fallback_when_json_is_none(self):
        """When json_cited_sources is None, fall back to regex."""
        chain = self._make_chain()
        citations = [
            {"number": 1, "citation": "UU 40/2007"},
            {"number": 2, "citation": "PP 5/2021"},
        ]
        vr = chain._validate_answer(
            "Jawaban berdasarkan [1].",
            citations,
            json_cited_sources=None,
        )
        assert vr.citation_coverage == 0.5  # Only [1] found via regex

    def test_json_parse_fallback_to_regex(self):
        """Full end-to-end: LLM returns no JSON → regex fallback works."""
        results = _make_results(2)
        mock_r = MagicMock()
        mock_r.hybrid_search.return_value = results
        mock_l = MagicMock()
        # LLM returns plain text without JSON block
        mock_l.generate.return_value = "Berdasarkan [1] dan [2], jawabannya..."

        chain = LegalRAGChain(retriever=mock_r, llm_client=mock_l)
        resp = chain.query("Apa itu PT?")

        assert resp.answer == "Berdasarkan [1] dan [2], jawabannya..."
        assert resp.validation is not None
        assert resp.validation.citation_coverage == 1.0  # Both cited via regex
        assert resp.validation.hallucination_risk == "low"

    def test_json_parse_success_extracts_answer(self):
        """Full end-to-end: LLM returns JSON → answer is cleaned, sources extracted."""
        results = _make_results(3)
        mock_r = MagicMock()
        mock_r.hybrid_search.return_value = results
        mock_l = MagicMock()
        # LLM returns answer with JSON metadata block
        mock_l.generate.return_value = (
            "Berdasarkan UU No. 40 [1], syarat PT adalah...\n\n"
            "```json\n"
            '{"cited_sources": [1, 3]}\n'
            "```"
        )

        chain = LegalRAGChain(retriever=mock_r, llm_client=mock_l)
        resp = chain.query("Apa itu PT?")

        # Answer should be cleaned (no JSON block)
        assert "```json" not in resp.answer
        assert "cited_sources" not in resp.answer
        assert "Berdasarkan UU No. 40" in resp.answer
        # Validation should use JSON-extracted sources
        assert resp.validation is not None
