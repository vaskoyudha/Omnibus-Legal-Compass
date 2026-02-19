"""Tests for GET /api/v1/providers endpoint."""
import os
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# TestProvidersEndpoint
# ---------------------------------------------------------------------------


class TestProvidersEndpoint:
    """Tests for the GET /api/v1/providers endpoint."""

    def test_get_providers_returns_200(self, test_client):
        """GET /api/v1/providers returns HTTP 200."""
        response = test_client.get("/api/v1/providers")
        assert response.status_code == 200

    def test_get_providers_response_structure(self, test_client):
        """Response JSON has 'providers' key."""
        response = test_client.get("/api/v1/providers")
        data = response.json()
        assert "providers" in data

    def test_get_providers_is_list(self, test_client):
        """response['providers'] is a list."""
        response = test_client.get("/api/v1/providers")
        data = response.json()
        assert isinstance(data["providers"], list)

    def test_get_providers_copilot_always_present(self, test_client):
        """Copilot provider is always in the list."""
        response = test_client.get("/api/v1/providers")
        data = response.json()
        provider_ids = [p["id"] for p in data["providers"]]
        assert "copilot" in provider_ids

    def test_provider_has_required_fields(self, test_client):
        """Each provider has 'id', 'name', 'is_available', 'models'."""
        response = test_client.get("/api/v1/providers")
        data = response.json()
        for provider in data["providers"]:
            assert "id" in provider
            assert "name" in provider
            assert "is_available" in provider
            assert "models" in provider

    def test_provider_models_is_list(self, test_client):
        """models field is a list for each provider."""
        response = test_client.get("/api/v1/providers")
        data = response.json()
        for provider in data["providers"]:
            assert isinstance(provider["models"], list)

    def test_model_has_required_fields(self, test_client):
        """Each model has 'id', 'name', 'context_window', 'supports_streaming'."""
        response = test_client.get("/api/v1/providers")
        data = response.json()
        for provider in data["providers"]:
            for model in provider["models"]:
                assert "id" in model
                assert "name" in model
                assert "context_window" in model
                assert "supports_streaming" in model

    def test_copilot_is_available(self, test_client):
        """Copilot provider has is_available=True."""
        response = test_client.get("/api/v1/providers")
        data = response.json()
        copilot = next(p for p in data["providers"] if p["id"] == "copilot")
        assert copilot["is_available"] is True

    def test_copilot_has_six_models(self, test_client):
        """Copilot provider has 6 models."""
        response = test_client.get("/api/v1/providers")
        data = response.json()
        copilot = next(p for p in data["providers"] if p["id"] == "copilot")
        assert len(copilot["models"]) == 6

    def test_providers_sorted_by_order(self, test_client):
        """Copilot comes first (sort_order=1)."""
        response = test_client.get("/api/v1/providers")
        data = response.json()
        providers = data["providers"]
        if providers:
            assert providers[0]["id"] == "copilot"

    def test_anthropic_not_available_without_key(self, test_client):
        """Without ANTHROPIC_API_KEY, anthropic is not available."""
        # Remove the key if present, keep everything else
        env_copy = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        with patch.dict(os.environ, env_copy, clear=True):
            response = test_client.get("/api/v1/providers")
            data = response.json()
            anthropic_providers = [
                p for p in data["providers"] if p["id"] == "anthropic"
            ]
            # Either anthropic is not in the list, or it's there but not available
            if anthropic_providers:
                assert anthropic_providers[0]["is_available"] is False
            else:
                # Not present at all because get_available_providers filters
                assert True

    def test_anthropic_available_with_key(self, test_client):
        """With ANTHROPIC_API_KEY set, anthropic IS in providers with is_available=True."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):  # pragma: allowlist secret
            response = test_client.get("/api/v1/providers")
            data = response.json()
            anthropic_providers = [
                p for p in data["providers"] if p["id"] == "anthropic"
            ]
            assert len(anthropic_providers) == 1
            assert anthropic_providers[0]["is_available"] is True

    def test_get_providers_no_auth_required(self, test_client):
        """No auth headers needed — 200 OK without credentials."""
        response = test_client.get("/api/v1/providers")
        assert response.status_code == 200
