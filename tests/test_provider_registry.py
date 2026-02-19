"""Tests for backend/provider_registry.py — OpenCode-style provider registry."""
import os
import pytest
from unittest.mock import patch

from provider_registry import (
    ModelInfo,
    ProviderInfo,
    SUPPORTED_MODELS,
    PROVIDER_REGISTRY,
    get_available_providers,
    get_models_for_provider,
    get_model_info,
)


# ---------------------------------------------------------------------------
# TestModelInfo
# ---------------------------------------------------------------------------


class TestModelInfo:
    """Tests for the ModelInfo frozen dataclass."""

    def test_model_info_is_frozen(self):
        """ModelInfo cannot be modified (frozen dataclass)."""
        m = SUPPORTED_MODELS["gpt-4o"]
        with pytest.raises(AttributeError):
            m.id = "changed"

    def test_model_info_fields_exist(self):
        """A ModelInfo has id, name, api_model, context_window, default_max_tokens."""
        m = SUPPORTED_MODELS["gpt-4o"]
        assert isinstance(m.id, str)
        assert isinstance(m.name, str)
        assert isinstance(m.api_model, str)
        assert isinstance(m.context_window, int)
        assert isinstance(m.default_max_tokens, int)

    def test_model_info_defaults(self):
        """supports_streaming defaults True, supports_vision defaults False, can_reason defaults False."""
        m = ModelInfo(
            id="test",
            name="Test",
            api_model="test-model",
            context_window=1000,
            default_max_tokens=100,
        )
        assert m.supports_streaming is True
        assert m.supports_vision is False
        assert m.can_reason is False

    def test_model_info_can_reason_true(self):
        """At least one ModelInfo in SUPPORTED_MODELS has can_reason=True."""
        assert any(m.can_reason for m in SUPPORTED_MODELS.values())

    def test_model_info_vision_support(self):
        """At least one ModelInfo has supports_vision=True."""
        assert any(m.supports_vision for m in SUPPORTED_MODELS.values())


# ---------------------------------------------------------------------------
# TestProviderInfo
# ---------------------------------------------------------------------------


class TestProviderInfo:
    """Tests for the ProviderInfo dataclass and is_available property."""

    def test_provider_info_fields(self):
        """ProviderInfo has id, name, env_key, sort_order, models."""
        p = PROVIDER_REGISTRY["copilot"]
        assert isinstance(p.id, str)
        assert isinstance(p.name, str)
        assert isinstance(p.env_key, str)
        assert isinstance(p.sort_order, int)
        assert isinstance(p.models, list)

    def test_copilot_always_available(self):
        """Copilot (env_key='') is_available is always True."""
        p = PROVIDER_REGISTRY["copilot"]
        assert p.env_key == ""
        assert p.is_available is True

    def test_provider_unavailable_when_env_missing(self):
        """Anthropic is_available=False when ANTHROPIC_API_KEY is unset."""
        with patch.dict(os.environ, {}, clear=True):
            p = PROVIDER_REGISTRY["anthropic"]
            assert p.is_available is False

    def test_provider_available_when_env_set(self):
        """Anthropic is_available=True when ANTHROPIC_API_KEY is set."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-key"}):  # pragma: allowlist secret
            p = PROVIDER_REGISTRY["anthropic"]
            assert p.is_available is True

    def test_sort_order_unique(self):
        """All providers have unique sort_order values."""
        orders = [p.sort_order for p in PROVIDER_REGISTRY.values()]
        assert len(orders) == len(set(orders))


# ---------------------------------------------------------------------------
# TestSupportedModels
# ---------------------------------------------------------------------------


class TestSupportedModels:
    """Tests for the SUPPORTED_MODELS global dict."""

    def test_total_model_count(self):
        """SUPPORTED_MODELS has exactly 21 entries."""
        assert len(SUPPORTED_MODELS) == 21

    def test_all_model_ids_unique(self):
        """All model ids are unique keys (dict keys are unique by definition)."""
        ids = list(SUPPORTED_MODELS.keys())
        assert len(ids) == len(set(ids))

    def test_specific_model_exists_gpt4o(self):
        """SUPPORTED_MODELS contains 'gpt-4o'."""
        assert "gpt-4o" in SUPPORTED_MODELS

    def test_specific_model_exists_claude(self):
        """SUPPORTED_MODELS contains 'claude-sonnet-4'."""
        assert "claude-sonnet-4" in SUPPORTED_MODELS

    def test_specific_model_api_model_different(self):
        """For 'claude-sonnet-4', api_model != id (OpenCode key pattern)."""
        m = SUPPORTED_MODELS["claude-sonnet-4"]
        assert m.api_model != m.id


# ---------------------------------------------------------------------------
# TestProviderRegistry
# ---------------------------------------------------------------------------


class TestProviderRegistry:
    """Tests for the PROVIDER_REGISTRY global dict."""

    def test_total_provider_count(self):
        """PROVIDER_REGISTRY has exactly 7 providers."""
        assert len(PROVIDER_REGISTRY) == 7

    def test_all_provider_ids(self):
        """Registry contains all expected provider ids."""
        expected = sorted(["copilot", "anthropic", "nvidia", "groq", "gemini", "mistral", "openrouter"])
        assert sorted(PROVIDER_REGISTRY.keys()) == expected

    def test_copilot_provider(self):
        """Copilot provider has correct name and 6 models."""
        p = PROVIDER_REGISTRY["copilot"]
        assert p.name == "Copilot"
        assert len(p.models) == 6

    def test_anthropic_provider(self):
        """Anthropic provider has correct env_key and 3 models."""
        p = PROVIDER_REGISTRY["anthropic"]
        assert p.env_key == "ANTHROPIC_API_KEY"
        assert len(p.models) == 3

    def test_openrouter_provider(self):
        """OpenRouter provider has correct env_key and 4 models."""
        p = PROVIDER_REGISTRY["openrouter"]
        assert p.env_key == "OPENROUTER_API_KEY"
        assert len(p.models) == 4


# ---------------------------------------------------------------------------
# TestHelperFunctions
# ---------------------------------------------------------------------------


class TestHelperFunctions:
    """Tests for get_available_providers, get_models_for_provider, get_model_info."""

    def test_get_available_providers_returns_copilot(self):
        """Copilot is always in get_available_providers() result."""
        providers = get_available_providers()
        provider_ids = [p.id for p in providers]
        assert "copilot" in provider_ids

    def test_get_available_providers_sorted_by_sort_order(self):
        """Result is sorted by sort_order ascending."""
        providers = get_available_providers()
        orders = [p.sort_order for p in providers]
        assert orders == sorted(orders)

    def test_get_available_providers_filters_unavailable(self):
        """With all API key env vars unset, only copilot is returned."""
        env_keys = [
            "ANTHROPIC_API_KEY", "NVIDIA_API_KEY", "GROQ_API_KEY",
            "GEMINI_API_KEY", "MISTRAL_API_KEY", "OPENROUTER_API_KEY",
        ]
        clean_env = {k: v for k, v in os.environ.items() if k not in env_keys}
        with patch.dict(os.environ, clean_env, clear=True):
            providers = get_available_providers()
            provider_ids = [p.id for p in providers]
            assert provider_ids == ["copilot"]

    def test_get_models_for_provider_returns_list(self):
        """get_models_for_provider('copilot') returns non-empty list."""
        models = get_models_for_provider("copilot")
        assert isinstance(models, list)
        assert len(models) > 0

    def test_get_models_for_provider_unknown(self):
        """get_models_for_provider('unknown_xyz') returns []."""
        assert get_models_for_provider("unknown_xyz") == []

    def test_get_model_info_known(self):
        """get_model_info('gpt-4o') returns ModelInfo with id=='gpt-4o'."""
        m = get_model_info("gpt-4o")
        assert m is not None
        assert m.id == "gpt-4o"

    def test_get_model_info_unknown(self):
        """get_model_info('nonexistent-xyz') returns None."""
        assert get_model_info("nonexistent-xyz") is None
