"""
Tests for backend/provider_config.py — FallbackChain factory.

All tests mock create_llm_client to avoid real API key requirements.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from backend.provider_config import (
    create_fallback_chain,
    DEFAULT_PROVIDER_ORDER,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_create_llm_client(provider, **kwargs):
    """Return a MagicMock client for any provider."""
    client = MagicMock()
    client.name = provider
    return client


def _mock_create_llm_client_selective(available):
    """Return a factory that only succeeds for providers in *available*."""
    def factory(provider, **kwargs):
        if provider in available:
            client = MagicMock()
            client.name = provider
            return client
        raise ValueError(f"{provider} API key not found")
    return factory


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCreateFallbackChain:
    """Tests for create_fallback_chain()."""

    @patch("backend.provider_config.create_llm_client", side_effect=_mock_create_llm_client)
    def test_default_order(self, mock_factory):
        chain = create_fallback_chain()
        names = [name for name, _ in chain.providers]
        assert names == DEFAULT_PROVIDER_ORDER

    @patch("backend.provider_config.create_llm_client", side_effect=_mock_create_llm_client)
    def test_custom_order(self, mock_factory):
        chain = create_fallback_chain(provider_order=["nvidia", "copilot"])
        names = [name for name, _ in chain.providers]
        assert names == ["nvidia", "copilot"]

    @patch(
        "backend.provider_config.create_llm_client",
        side_effect=_mock_create_llm_client_selective({"groq", "nvidia"}),
    )
    def test_skips_unavailable_providers(self, mock_factory):
        chain = create_fallback_chain(provider_order=["groq", "gemini", "nvidia"])
        names = [name for name, _ in chain.providers]
        assert names == ["groq", "nvidia"]

    @patch(
        "backend.provider_config.create_llm_client",
        side_effect=ValueError("no key"),
    )
    def test_all_unavailable_raises(self, mock_factory):
        with pytest.raises(RuntimeError, match="No LLM providers available"):
            create_fallback_chain(provider_order=["groq"])

    @patch("backend.provider_config.create_llm_client", side_effect=_mock_create_llm_client)
    def test_unknown_provider_skipped(self, mock_factory):
        """Unknown providers are logged and skipped, not raising."""
        chain = create_fallback_chain(provider_order=["groq", "unknown_provider"])
        names = [name for name, _ in chain.providers]
        assert names == ["groq"]

    @patch("backend.provider_config.create_llm_client", side_effect=_mock_create_llm_client)
    def test_returns_fallback_chain_instance(self, mock_factory):
        from backend.llm_client import FallbackChain
        chain = create_fallback_chain()
        assert isinstance(chain, FallbackChain)

    @patch("backend.provider_config.create_llm_client", side_effect=_mock_create_llm_client)
    def test_circuit_breakers_created(self, mock_factory):
        chain = create_fallback_chain()
        assert len(chain.circuit_breakers) == len(DEFAULT_PROVIDER_ORDER)
        for name in DEFAULT_PROVIDER_ORDER:
            assert name in chain.circuit_breakers
