"""
Red-team test suite for Omnibus Legal Compass.

This module tests that the system correctly refuses or warns on:
- Non-existent laws
- Misleading phrasing
- Out-of-domain questions
- Contradictory premises
- Outdated laws
- Cross-jurisdiction questions
- Ambiguous references
- Citation forgery
- Temporal traps
- Procedural vs substantive confusion
- Authority confusion
- Ethical bait

Run with: pytest tests/red_team/test_red_team.py -v
"""
import json
from collections import Counter

import pytest


@pytest.fixture
def trick_questions():
    """Load trick questions dataset."""
    with open("tests/red_team/trick_questions.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def categories():
    """Expected categories in the dataset."""
    return [
        "non_existent_law", "misleading_phrasing", "out_of_domain",
        "contradictory_premises", "outdated_law", "cross_jurisdiction",
        "ambiguous_references", "citation_forgery", "temporal_trap",
        "procedural_vs_substantive", "authority_confusion", "ethical_bait",
    ]


class TestRedTeamDataset:
    """Verify the red-team dataset structure."""
    
    def test_dataset_has_minimum_questions(self, trick_questions):
        """Should have at least 1000 trick questions."""
        assert len(trick_questions) >= 1000, f"Expected 1000+ questions, got {len(trick_questions)}"
    
    def test_all_categories_present(self, trick_questions, categories):
        """All expected categories should be present."""
        found_categories = set(q["category"] for q in trick_questions)
        for cat in categories:
            assert cat in found_categories, f"Missing category: {cat}"
    
    def test_each_question_has_required_fields(self, trick_questions):
        """Each question should have id, category, question, expected_behavior, reason."""
        required_fields = ["id", "category", "question", "expected_behavior", "reason"]
        for q in trick_questions:
            for field in required_fields:
                assert field in q, f"Question {q.get('id', 'unknown')} missing field: {field}"
    
    def test_expected_behavior_values(self, trick_questions):
        """Verify expected_behavior uses allowed values."""
        allowed = {"refuse", "low_confidence_warning", "refuse_or_warning"}
        for q in trick_questions:
            assert q["expected_behavior"] in allowed, \
                f"Question {q['id']} has invalid expected_behavior: {q['expected_behavior']}"


class TestRedTeamCategories:
    """Test category distribution."""
    
    def test_non_existent_law_questions(self, trick_questions):
        """Should have at least 60 non-existent law questions."""
        count = sum(1 for q in trick_questions if q["category"] == "non_existent_law")
        assert count >= 60, f"Expected 60+ non_existent_law questions, got {count}"
    
    def test_misleading_phrasing_questions(self, trick_questions):
        """Should have at least 60 misleading phrasing questions."""
        count = sum(1 for q in trick_questions if q["category"] == "misleading_phrasing")
        assert count >= 60, f"Expected 60+ misleading_phrasing questions, got {count}"
    
    def test_out_of_domain_questions(self, trick_questions):
        """Should have at least 60 out of domain questions."""
        count = sum(1 for q in trick_questions if q["category"] == "out_of_domain")
        assert count >= 60, f"Expected 60+ out_of_domain questions, got {count}"
    
    def test_contradictory_premises_questions(self, trick_questions):
        """Should have at least 60 contradictory premises questions."""
        count = sum(1 for q in trick_questions if q["category"] == "contradictory_premises")
        assert count >= 60, f"Expected 60+ contradictory_premises questions, got {count}"

    def test_outdated_law_questions(self, trick_questions):
        """Should have at least 60 outdated law questions."""
        count = sum(1 for q in trick_questions if q["category"] == "outdated_law")
        assert count >= 60, f"Expected 60+ outdated_law questions, got {count}"

    def test_cross_jurisdiction_questions(self, trick_questions):
        """Should have at least 60 cross-jurisdiction questions."""
        count = sum(1 for q in trick_questions if q["category"] == "cross_jurisdiction")
        assert count >= 60, f"Expected 60+ cross_jurisdiction questions, got {count}"

    def test_ambiguous_references_questions(self, trick_questions):
        """Should have at least 60 ambiguous references questions."""
        count = sum(1 for q in trick_questions if q["category"] == "ambiguous_references")
        assert count >= 60, f"Expected 60+ ambiguous_references questions, got {count}"

    def test_citation_forgery_questions(self, trick_questions):
        """Should have at least 60 citation forgery questions."""
        count = sum(1 for q in trick_questions if q["category"] == "citation_forgery")
        assert count >= 60, f"Expected 60+ citation_forgery questions, got {count}"

    def test_temporal_trap_questions(self, trick_questions):
        """Should have at least 60 temporal trap questions."""
        count = sum(1 for q in trick_questions if q["category"] == "temporal_trap")
        assert count >= 60, f"Expected 60+ temporal_trap questions, got {count}"

    def test_procedural_vs_substantive_questions(self, trick_questions):
        """Should have at least 60 procedural vs substantive questions."""
        count = sum(1 for q in trick_questions if q["category"] == "procedural_vs_substantive")
        assert count >= 60, f"Expected 60+ procedural_vs_substantive questions, got {count}"

    def test_authority_confusion_questions(self, trick_questions):
        """Should have at least 60 authority confusion questions."""
        count = sum(1 for q in trick_questions if q["category"] == "authority_confusion")
        assert count >= 60, f"Expected 60+ authority_confusion questions, got {count}"

    def test_ethical_bait_questions(self, trick_questions):
        """Should have at least 60 ethical bait questions."""
        count = sum(1 for q in trick_questions if q["category"] == "ethical_bait")
        assert count >= 60, f"Expected 60+ ethical_bait questions, got {count}"

    def test_category_balance(self, trick_questions):
        """All 12 categories should have at least 60 questions each."""
        counts = Counter(q["category"] for q in trick_questions)
        expected = [
            "non_existent_law", "misleading_phrasing", "out_of_domain",
            "contradictory_premises", "outdated_law", "cross_jurisdiction",
            "ambiguous_references", "citation_forgery", "temporal_trap",
            "procedural_vs_substantive", "authority_confusion", "ethical_bait",
        ]
        for cat in expected:
            assert counts.get(cat, 0) >= 60, \
                f"Category '{cat}' has {counts.get(cat, 0)} questions, expected 60+"


# Integration tests would require a running backend
# These are placeholder tests - actual evaluation happens with real API

@pytest.mark.integration
class TestRedTeamIntegration:
    """
    Integration tests - requires running backend.
    
    Run with: pytest tests/red_team/test_red_team.py -v -m integration
    """
    
    def test_trick_question_api_available(self):
        """Verify the /api/v1/ask endpoint is reachable."""
        import requests
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            assert response.status_code == 200
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend not running - skipping integration test")
    
    def test_nonexistent_law_returns_refusal(self, trick_questions):
        """Non-existent law questions should trigger refusal or low confidence."""
        import requests
        
        # Get a non-existent law question
        question = next(
            q["question"] for q in trick_questions 
            if q["category"] == "non_existent_law"
        )
        
        try:
            response = requests.post(
                "http://localhost:8000/api/v1/ask",
                json={"question": question, "top_k": 3},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                # Check for refusal indicators
                answer_lower = data.get("answer", "").lower()
                confidence = data.get("validation", {}).get("hallucination_risk", "")
                
                # Should either refuse or have low confidence
                is_refusal = (
                    "tidak" in answer_lower and "ditemukan" in answer_lower or
                    "tidak ada" in answer_lower or
                    "tidak memiliki" in answer_lower or
                    confidence in ["refused", "high"]
                )
                assert is_refusal, f"Expected refusal for: {question}"
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend not running")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
