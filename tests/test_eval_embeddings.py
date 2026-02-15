"""Tests for the embedding evaluation module — validates metrics computation and report generation."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from scripts.eval_embeddings import (
    load_corpus,
    load_golden_qa,
    cosine_similarity_matrix,
    evaluate_retrieval,
    format_report,
    report_to_dict,
    RetrievalResult,
    EvalReport,
    CORPUS_PATH,
    GOLDEN_QA_PATH,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_corpus():
    """Minimal corpus for testing."""
    return [
        {
            "text": "Perseroan Terbatas didirikan oleh dua orang dengan akta notaris",
            "regulation_key": "UU 40/2007",
            "pasal": "1",
            "metadata": {"jenis_dokumen": "UU", "nomor": "40", "tahun": "2007"},
        },
        {
            "text": "Modal dasar minimal Rp50.000.000",
            "regulation_key": "UU 40/2007",
            "pasal": "32",
            "metadata": {"jenis_dokumen": "UU", "nomor": "40", "tahun": "2007"},
        },
        {
            "text": "Bank terdiri dari Bank Umum dan Bank Perkreditan Rakyat",
            "regulation_key": "UU 10/1998",
            "pasal": "5",
            "metadata": {"jenis_dokumen": "UU", "nomor": "10", "tahun": "1998"},
        },
        {
            "text": "Hak Cipta adalah hak eksklusif pencipta",
            "regulation_key": "UU 28/2014",
            "pasal": "1",
            "metadata": {"jenis_dokumen": "UU", "nomor": "28", "tahun": "2014"},
        },
        {
            "text": "Kepailitan adalah sita umum atas kekayaan debitor",
            "regulation_key": "UU 37/2004",
            "pasal": "1",
            "metadata": {"jenis_dokumen": "UU", "nomor": "37", "tahun": "2004"},
        },
    ]


@pytest.fixture
def sample_golden_qa():
    """Minimal golden QA pairs for testing."""
    return [
        {
            "id": "test_001",
            "question": "Apa syarat pendirian PT?",
            "expected_answer_contains": ["akta notaris"],
            "regulations": ["UU 40/2007"],
        },
        {
            "id": "test_002",
            "question": "Apa jenis bank di Indonesia?",
            "expected_answer_contains": ["Bank Umum"],
            "regulations": ["UU 10/1998"],
        },
        {
            "id": "test_003",
            "question": "Apa itu kepailitan?",
            "expected_answer_contains": ["sita umum"],
            "regulations": ["UU 37/2004"],
        },
    ]


@pytest.fixture
def sample_eval_report():
    """Pre-built evaluation report for testing format/serialization."""
    return EvalReport(
        model_name="test-model",
        corpus_size=100,
        num_queries=3,
        mrr=0.7778,
        hit_rate=0.6667,
        recall_at={1: 0.6667, 3: 0.8333, 5: 1.0, 10: 1.0},
        per_query=[
            RetrievalResult(
                query_id="q1",
                question="Test question 1",
                expected_regulations=["UU 40/2007"],
                top_k_citations=["UU 40/2007", "UU 10/1998"],
                reciprocal_rank=1.0,
                recall_at={1: 1.0, 3: 1.0, 5: 1.0, 10: 1.0},
                first_relevant_rank=1,
            ),
            RetrievalResult(
                query_id="q2",
                question="Test question 2",
                expected_regulations=["UU 10/1998"],
                top_k_citations=["UU 40/2007", "UU 10/1998"],
                reciprocal_rank=0.5,
                recall_at={1: 0.0, 3: 1.0, 5: 1.0, 10: 1.0},
                first_relevant_rank=2,
            ),
            RetrievalResult(
                query_id="q3",
                question="Test question 3",
                expected_regulations=["PP 24/2018"],
                top_k_citations=["UU 40/2007", "UU 10/1998"],
                reciprocal_rank=0.0,
                recall_at={1: 0.0, 3: 0.0, 5: 0.0, 10: 0.0},
                first_relevant_rank=None,
            ),
        ],
        elapsed_seconds=1.5,
    )


# ── Test: load_corpus ────────────────────────────────────────────────────────


class TestLoadCorpus:
    """Tests for corpus loading from regulations.json."""

    def test_loads_real_corpus(self):
        """Verify real corpus loads successfully."""
        corpus = load_corpus(CORPUS_PATH)
        assert len(corpus) >= 250, f"Expected >= 250 articles, got {len(corpus)}"

    def test_corpus_has_required_keys(self):
        """Each corpus entry has text, regulation_key, metadata."""
        corpus = load_corpus(CORPUS_PATH)
        for doc in corpus[:5]:
            assert "text" in doc
            assert "regulation_key" in doc
            assert "metadata" in doc
            assert len(doc["text"]) > 0

    def test_regulation_key_format(self):
        """Regulation keys are formatted as 'JENIS NOMOR/TAHUN'."""
        corpus = load_corpus(CORPUS_PATH)
        for doc in corpus[:20]:
            key = doc["regulation_key"]
            parts = key.split(" ")
            assert len(parts) == 2, f"Bad key format: {key}"
            assert "/" in parts[1], f"Missing '/' in key: {key}"

    def test_missing_file_raises(self):
        """FileNotFoundError on missing corpus file."""
        with pytest.raises(FileNotFoundError):
            load_corpus("/nonexistent/path.json")

    def test_empty_text_articles_excluded(self, tmp_path):
        """Articles with empty text are excluded."""
        data = [
            {"jenis_dokumen": "UU", "nomor": "1", "tahun": 2020, "judul": "Test", "text": ""},
            {"jenis_dokumen": "UU", "nomor": "1", "tahun": 2020, "judul": "Test", "text": "Actual content"},
        ]
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        corpus = load_corpus(path)
        assert len(corpus) == 1


# ── Test: load_golden_qa ─────────────────────────────────────────────────────


class TestLoadGoldenQA:
    """Tests for golden QA loading."""

    def test_loads_real_golden_qa(self):
        """Verify real golden_qa.json loads successfully."""
        qa = load_golden_qa(GOLDEN_QA_PATH)
        assert len(qa) >= 40, f"Expected >= 40 QA pairs, got {len(qa)}"

    def test_qa_has_required_fields(self):
        """Each QA pair has id, question, regulations."""
        qa = load_golden_qa(GOLDEN_QA_PATH)
        for pair in qa:
            assert "id" in pair
            assert "question" in pair
            assert "regulations" in pair
            assert len(pair["regulations"]) > 0

    def test_qa_covers_new_regulations(self):
        """Golden QA covers the 8 new regulation domains."""
        qa = load_golden_qa(GOLDEN_QA_PATH)
        all_regs = set()
        for pair in qa:
            all_regs.update(pair["regulations"])

        new_regs = {
            "UU 31/1999",  # Anti-corruption
            "UU 5/1999",   # Competition
            "UU 10/1998",  # Banking
            "UU 8/1995",   # Capital markets
            "UU 28/2014",  # Copyright
            "UU 13/2016",  # Patents
            "UU 20/2016",  # Trademarks
            "UU 37/2004",  # Bankruptcy
        }
        missing = new_regs - all_regs
        assert not missing, f"Golden QA missing coverage for: {missing}"

    def test_missing_file_raises(self):
        """FileNotFoundError on missing QA file."""
        with pytest.raises(FileNotFoundError):
            load_golden_qa("/nonexistent/path.json")


# ── Test: cosine_similarity_matrix ───────────────────────────────────────────


class TestCosineSimilarity:
    """Tests for cosine similarity computation."""

    def test_identical_vectors(self):
        """Identical vectors have similarity 1.0."""
        vec = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
        sim = cosine_similarity_matrix(vec, vec)
        assert sim.shape == (1, 1)
        assert abs(sim[0, 0] - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        """Orthogonal vectors have similarity 0.0."""
        q = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
        c = np.array([[0.0, 1.0, 0.0]], dtype=np.float32)
        sim = cosine_similarity_matrix(q, c)
        assert abs(sim[0, 0]) < 1e-6

    def test_opposite_vectors(self):
        """Opposite vectors have similarity -1.0."""
        q = np.array([[1.0, 0.0]], dtype=np.float32)
        c = np.array([[-1.0, 0.0]], dtype=np.float32)
        sim = cosine_similarity_matrix(q, c)
        assert abs(sim[0, 0] - (-1.0)) < 1e-6

    def test_matrix_shape(self):
        """Output shape matches (num_queries, num_corpus)."""
        q = np.random.randn(3, 10).astype(np.float32)
        c = np.random.randn(7, 10).astype(np.float32)
        sim = cosine_similarity_matrix(q, c)
        assert sim.shape == (3, 7)

    def test_values_in_range(self):
        """All similarity values are in [-1, 1]."""
        q = np.random.randn(5, 20).astype(np.float32)
        c = np.random.randn(10, 20).astype(np.float32)
        sim = cosine_similarity_matrix(q, c)
        assert np.all(sim >= -1.0 - 1e-6)
        assert np.all(sim <= 1.0 + 1e-6)

    def test_zero_vector_handling(self):
        """Zero vectors don't cause division by zero."""
        q = np.array([[0.0, 0.0, 0.0]], dtype=np.float32)
        c = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
        sim = cosine_similarity_matrix(q, c)
        # Should not raise, result is near-zero
        assert not np.isnan(sim[0, 0])


# ── Test: evaluate_retrieval (with mock embeddings) ──────────────────────────


class TestEvaluateRetrieval:
    """Tests for the full evaluation pipeline (mocked embeddings)."""

    def _make_mock_embeddings(self, corpus, golden_qa):
        """
        Create embeddings where queries are close to their expected regulation.

        Strategy: Each regulation gets a unique direction in embedding space.
        Query embeddings point toward their expected regulation's direction.
        """
        # Assign a direction per regulation
        reg_keys = list(set(doc["regulation_key"] for doc in corpus))
        dim = 16
        reg_dirs = {}
        for i, key in enumerate(reg_keys):
            vec = np.zeros(dim, dtype=np.float32)
            vec[i % dim] = 1.0
            if (i // dim) < dim:
                vec[(i // dim)] += 0.3
            reg_dirs[key] = vec / np.linalg.norm(vec)

        # Corpus embeddings: each doc gets its regulation's direction + small noise
        corpus_embeddings = []
        for doc in corpus:
            base = reg_dirs[doc["regulation_key"]]
            noise = np.random.randn(dim).astype(np.float32) * 0.05
            vec = base + noise
            corpus_embeddings.append(vec / np.linalg.norm(vec))

        # Query embeddings: point toward expected regulation
        query_embeddings = []
        for qa in golden_qa:
            expected_reg = qa["regulations"][0]
            if expected_reg in reg_dirs:
                base = reg_dirs[expected_reg]
            else:
                base = np.random.randn(dim).astype(np.float32)
            noise = np.random.randn(dim).astype(np.float32) * 0.1
            vec = base + noise
            query_embeddings.append(vec / np.linalg.norm(vec))

        return np.array(corpus_embeddings), np.array(query_embeddings)

    def test_perfect_retrieval(self, sample_corpus, sample_golden_qa):
        """When embeddings perfectly distinguish regulations, MRR should be high."""
        corpus_emb, query_emb = self._make_mock_embeddings(
            sample_corpus, sample_golden_qa
        )

        with patch("scripts.eval_embeddings.embed_texts") as mock_embed:
            call_count = 0

            def side_effect(texts, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return corpus_emb
                return query_emb

            mock_embed.side_effect = side_effect

            report = evaluate_retrieval(
                corpus=sample_corpus,
                golden_qa=sample_golden_qa,
                k_values=[1, 3, 5],
            )

            assert report.num_queries == 3
            assert report.corpus_size == 5
            assert report.mrr > 0.5  # Should be high with distinct directions
            assert report.elapsed_seconds >= 0

    def test_report_structure(self, sample_corpus, sample_golden_qa):
        """Evaluate report has all required fields."""
        corpus_emb, query_emb = self._make_mock_embeddings(
            sample_corpus, sample_golden_qa
        )

        with patch("scripts.eval_embeddings.embed_texts") as mock_embed:
            call_count = 0

            def side_effect(texts, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return corpus_emb
                return query_emb

            mock_embed.side_effect = side_effect

            report = evaluate_retrieval(
                corpus=sample_corpus,
                golden_qa=sample_golden_qa,
            )

            assert isinstance(report, EvalReport)
            assert len(report.per_query) == 3
            for r in report.per_query:
                assert isinstance(r, RetrievalResult)
                assert r.query_id.startswith("test_")
                assert len(r.expected_regulations) > 0
                assert r.reciprocal_rank >= 0.0

    def test_empty_qa_returns_zero_metrics(self, sample_corpus):
        """Empty QA list produces zero metrics."""
        with patch("scripts.eval_embeddings.embed_texts") as mock_embed:
            mock_embed.return_value = np.random.randn(len(sample_corpus), 16).astype(
                np.float32
            )

            report = evaluate_retrieval(
                corpus=sample_corpus,
                golden_qa=[],
            )

            assert report.mrr == 0.0
            assert report.num_queries == 0


# ── Test: format_report ──────────────────────────────────────────────────────


class TestFormatReport:
    """Tests for human-readable report formatting."""

    def test_contains_key_sections(self, sample_eval_report):
        """Report text contains key sections."""
        text = format_report(sample_eval_report)
        assert "EMBEDDING RETRIEVAL EVALUATION REPORT" in text
        assert "AGGREGATE METRICS" in text
        assert "PER-QUERY RESULTS" in text
        assert "SUMMARY" in text

    def test_contains_metrics(self, sample_eval_report):
        """Report shows MRR, Hit Rate, Recall values."""
        text = format_report(sample_eval_report)
        assert "MRR" in text
        assert "Hit Rate" in text
        assert "Recall@1" in text
        assert "Recall@5" in text

    def test_contains_model_info(self, sample_eval_report):
        """Report shows model name and corpus size."""
        text = format_report(sample_eval_report)
        assert "test-model" in text
        assert "100" in text  # corpus size

    def test_shows_missed_queries(self, sample_eval_report):
        """Missed queries are marked as MISS."""
        text = format_report(sample_eval_report)
        assert "MISS" in text
        assert "not found" in text

    def test_no_unicode_issues(self, sample_eval_report):
        """Report can be encoded to ASCII-safe format."""
        text = format_report(sample_eval_report)
        # Should not contain problematic Unicode characters
        text.encode("ascii", errors="strict")


# ── Test: report_to_dict ─────────────────────────────────────────────────────


class TestReportToDict:
    """Tests for JSON serialization of reports."""

    def test_serializable(self, sample_eval_report):
        """Report dict is JSON-serializable."""
        d = report_to_dict(sample_eval_report)
        serialized = json.dumps(d, ensure_ascii=False)
        assert len(serialized) > 0

    def test_contains_all_fields(self, sample_eval_report):
        """Dict has all expected top-level keys."""
        d = report_to_dict(sample_eval_report)
        expected_keys = {
            "model_name", "corpus_size", "num_queries",
            "mrr", "hit_rate", "recall_at",
            "elapsed_seconds", "per_query",
        }
        assert expected_keys.issubset(d.keys())

    def test_per_query_fields(self, sample_eval_report):
        """Each per-query entry has required fields."""
        d = report_to_dict(sample_eval_report)
        for entry in d["per_query"]:
            assert "query_id" in entry
            assert "question" in entry
            assert "reciprocal_rank" in entry
            assert "first_relevant_rank" in entry

    def test_recall_at_keys_are_strings(self, sample_eval_report):
        """Recall@K keys are strings (for JSON compatibility)."""
        d = report_to_dict(sample_eval_report)
        for key in d["recall_at"]:
            assert isinstance(key, str)
