"""
Test streaming parity: confidence threshold and grounding verification.

Verifies that query_stream() now has the same safety guardrails as query():
1. Refuses to answer when confidence < 0.30
2. Performs LLM-as-judge grounding verification after streaming completes
"""

import pytest
from unittest.mock import Mock, patch
from backend.rag_chain import LegalRAGChain
from backend.retriever import SearchResult


class TestStreamingConfidenceThreshold:
    """Test that streaming respects confidence threshold."""
    
    def test_stream_refuses_low_confidence(self):
        """Stream should refuse to answer when confidence < 0.30."""
        rag = LegalRAGChain()
        
        # Mock retriever to return low-score results using SearchResult dataclass
        mock_results = [
            SearchResult(
                id=1,
                text="Some text",
                citation="UU Test Tahun 2024 Pasal 1",
                citation_id="UU-Test-2024-Pasal-1",
                score=0.15,  # Low score → low confidence
                metadata={
                    "jenis_dokumen": "UU",
                    "nomor": "Test",
                    "tahun": "2024",
                    "pasal": "1",
                }
            )
        ]
        
        with patch.object(rag.retriever, "hybrid_search", return_value=mock_results):
            events = list(rag.query_stream("test question", top_k=1))
        
        # Extract event types and data
        event_types = [e[0] for e in events]
        
        # Should have metadata, chunk, done
        assert "metadata" in event_types
        assert "chunk" in event_types
        assert "done" in event_types
        
        # Find the chunk content
        chunk_contents = [e[1] for e in events if e[0] == "chunk"]
        full_text = "".join(chunk_contents)
        
        # Should contain refusal message
        assert "tidak memiliki cukup informasi" in full_text.lower() or \
               "konsultasikan dengan ahli hukum" in full_text.lower()
        
        # Validation should indicate refusal
        done_event = [e[1] for e in events if e[0] == "done"][0]
        validation = done_event["validation"]
        assert validation["hallucination_risk"] == "refused"
    
    def test_stream_proceeds_with_high_confidence(self):
        """Stream should proceed normally when confidence >= 0.30."""
        rag = LegalRAGChain()
        
        # Mock retriever to return high-score results
        mock_results = [
            SearchResult(
                id=1,
                text="UU 40/2007 mengatur tentang Perseroan Terbatas. Pasal 7 ayat (1) menyatakan bahwa PT didirikan oleh 2 orang atau lebih.",
                citation="UU 40 Tahun 2007 Pasal 7",
                citation_id="UU-40-2007-Pasal-7",
                score=0.85,  # High score → high confidence
                metadata={
                    "jenis_dokumen": "UU",
                    "nomor": "40",
                    "tahun": "2007",
                    "pasal": "7",
                }
            )
        ]
        
        # Mock LLM to return structured answer
        mock_llm_response = "Berdasarkan UU 40/2007 Pasal 7 ayat (1), PT didirikan oleh 2 orang atau lebih. [1]"
        
        with patch.object(rag.retriever, "hybrid_search", return_value=mock_results), \
             patch.object(rag.llm_client, "generate_stream", return_value=iter([mock_llm_response])), \
             patch.object(rag, "_verify_grounding", return_value=(0.95, [])):
            
            events = list(rag.query_stream("Berapa orang minimal untuk mendirikan PT?", top_k=1))
        
        # Extract events
        event_types = [e[0] for e in events]
        assert "metadata" in event_types
        assert "chunk" in event_types
        assert "done" in event_types
        
        # Should NOT be refusal
        chunk_contents = [e[1] for e in events if e[0] == "chunk"]
        full_text = "".join(chunk_contents)
        assert "konsultasikan dengan ahli hukum" not in full_text.lower()
        assert "UU 40/2007" in full_text


class TestStreamingGroundingVerification:
    """Test that streaming performs grounding verification."""
    
    def test_stream_calls_verify_grounding(self):
        """Stream should call _verify_grounding after answer completes."""
        rag = LegalRAGChain()
        
        # Mock high-confidence retrieval
        mock_results = [
            SearchResult(
                id=1,
                text="UU 40/2007 Pasal 7: PT didirikan oleh 2 orang atau lebih.",
                citation="UU 40 Tahun 2007 Pasal 7",
                citation_id="UU-40-2007-Pasal-7",
                score=0.85,
                metadata={
                    "jenis_dokumen": "UU",
                    "nomor": "40",
                    "tahun": "2007",
                    "pasal": "7",
                }
            )
        ]
        
        mock_answer = "PT didirikan oleh 2 orang atau lebih menurut UU 40/2007. [1]"
        
        with patch.object(rag.retriever, "hybrid_search", return_value=mock_results), \
             patch.object(rag.llm_client, "generate_stream", return_value=iter([mock_answer])), \
             patch.object(rag, "_verify_grounding", return_value=(0.90, [])) as mock_verify:
            
            events = list(rag.query_stream("Berapa orang untuk mendirikan PT?", top_k=1))
        
        # Verify that _verify_grounding was called
        mock_verify.assert_called_once()
        
        # Check that grounding_score is in validation
        done_event = [e[1] for e in events if e[0] == "done"][0]
        validation = done_event["validation"]
        assert "grounding_score" in validation
        assert validation["grounding_score"] == 0.90
    
    def test_stream_includes_ungrounded_claims(self):
        """Stream validation should include ungrounded claims from verification."""
        rag = LegalRAGChain()
        
        mock_results = [
            SearchResult(
                id=1,
                text="UU 40/2007 Pasal 7: PT didirikan oleh 2 orang atau lebih.",
                citation="UU 40 Tahun 2007 Pasal 7",
                citation_id="UU-40-2007-Pasal-7",
                score=0.80,
                metadata={
                    "jenis_dokumen": "UU",
                    "nomor": "40",
                    "tahun": "2007",
                    "pasal": "7",
                }
            )
        ]
        
        mock_answer = "PT didirikan oleh 2 orang. Biaya pendirian PT adalah 10 juta rupiah. [1]"
        ungrounded_claims = ["Biaya pendirian PT adalah 10 juta rupiah"]
        
        with patch.object(rag.retriever, "hybrid_search", return_value=mock_results), \
             patch.object(rag.llm_client, "generate_stream", return_value=iter([mock_answer])), \
             patch.object(rag, "_verify_grounding", return_value=(0.50, ungrounded_claims)):
            
            events = list(rag.query_stream("Berapa orang untuk mendirikan PT?", top_k=1))
        
        # Check validation includes ungrounded claims
        done_event = [e[1] for e in events if e[0] == "done"][0]
        validation = done_event["validation"]
        assert validation["grounding_score"] == 0.50
        assert validation["ungrounded_claims"] == ungrounded_claims
    
    def test_stream_logs_low_grounding_warning(self, caplog):
        """Stream should log warning when grounding score < 0.5."""
        rag = LegalRAGChain()
        
        mock_results = [
            SearchResult(
                id=1,
                text="Some legal text",
                citation="UU Test Tahun 2024 Pasal 1",
                citation_id="UU-Test-2024-Pasal-1",
                score=0.80,
                metadata={
                    "jenis_dokumen": "UU",
                    "nomor": "Test",
                    "tahun": "2024",
                    "pasal": "1",
                }
            )
        ]
        
        mock_answer = "This answer has poor grounding."
        
        with patch.object(rag.retriever, "hybrid_search", return_value=mock_results), \
             patch.object(rag.llm_client, "generate_stream", return_value=iter([mock_answer])), \
             patch.object(rag, "_verify_grounding", return_value=(0.30, ["Unverified claim"])):
            
            import logging
            with caplog.at_level(logging.WARNING):
                list(rag.query_stream("test", top_k=1))
        
        # Should have warning log
        assert any("Low grounding score" in record.message for record in caplog.records)


class TestStreamingParityWithNonStreaming:
    """Verify streaming behavior matches non-streaming for safety features."""
    
    def test_both_refuse_low_confidence(self):
        """Both query() and query_stream() should refuse low-confidence queries."""
        rag = LegalRAGChain()
        
        mock_results = [
            SearchResult(
                id=1,
                text="Irrelevant text",
                citation="UU Test Tahun 2024 Pasal 1",
                citation_id="UU-Test-2024-Pasal-1",
                score=0.10,  # Very low score
                metadata={
                    "jenis_dokumen": "UU",
                    "nomor": "Test",
                    "tahun": "2024",
                    "pasal": "1",
                }
            )
        ]
        
        with patch.object(rag.retriever, "hybrid_search", return_value=mock_results):
            # Non-streaming
            response = rag.query("obscure legal question", top_k=1)
            
            # Streaming
            events = list(rag.query_stream("obscure legal question", top_k=1))
            stream_chunks = [e[1] for e in events if e[0] == "chunk"]
            stream_text = "".join(stream_chunks)
        
        # Both should refuse
        assert "konsultasikan dengan ahli hukum" in response.answer.lower()
        assert "konsultasikan dengan ahli hukum" in stream_text.lower()
        assert response.validation.hallucination_risk == "refused"
        
        done_event = [e[1] for e in events if e[0] == "done"][0]
        assert done_event["validation"]["hallucination_risk"] == "refused"
