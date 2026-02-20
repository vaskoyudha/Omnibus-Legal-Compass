"""Tests for AnthropicClient and OpenRouterClient in backend/llm_client.py."""
import os
import pytest
from unittest.mock import MagicMock, patch

from llm_client import (
    AnthropicClient,
    OpenRouterClient,
    OpenAICompatibleClient,
    CopilotChatClient,
    NVIDIANimClient,
    GroqClient,
    GeminiClient,
    MistralClient,
    AntigravityClient,
    create_llm_client,
    KNOWN_PROVIDERS,
    ANTHROPIC_API_URL,
    ANTHROPIC_API_VERSION,
    ANTHROPIC_DEFAULT_MODEL,
    ANTIGRAVITY_API_URL,
    ANTIGRAVITY_DEFAULT_MODEL,
    ANTIGRAVITY_DEFAULT_PROJECT_ID,
)


# ---------------------------------------------------------------------------
# TestKnownProviders
# ---------------------------------------------------------------------------


class TestKnownProviders:
    """Tests for the KNOWN_PROVIDERS constant."""

    def test_known_providers_count(self):
        """KNOWN_PROVIDERS has exactly 8 entries."""
        assert len(KNOWN_PROVIDERS) == 8

    def test_known_providers_contains_anthropic(self):
        """'anthropic' is in KNOWN_PROVIDERS."""
        assert "anthropic" in KNOWN_PROVIDERS

    def test_known_providers_contains_openrouter(self):
        """'openrouter' is in KNOWN_PROVIDERS."""
        assert "openrouter" in KNOWN_PROVIDERS


# ---------------------------------------------------------------------------
# TestAnthropicConstants
# ---------------------------------------------------------------------------


class TestAnthropicConstants:
    """Tests for Anthropic-specific constants."""

    def test_anthropic_api_url(self):
        """ANTHROPIC_API_URL is the messages endpoint."""
        assert ANTHROPIC_API_URL == "https://api.anthropic.com/v1/messages"

    def test_anthropic_api_version(self):
        """ANTHROPIC_API_VERSION is '2023-06-01'."""
        assert ANTHROPIC_API_VERSION == "2023-06-01"

    def test_anthropic_default_model(self):
        """ANTHROPIC_DEFAULT_MODEL starts with 'claude-'."""
        assert ANTHROPIC_DEFAULT_MODEL.startswith("claude-")


# ---------------------------------------------------------------------------
# TestAnthropicClientInit
# ---------------------------------------------------------------------------


class TestAnthropicClientInit:
    """Tests for AnthropicClient initialization."""

    def test_init_with_api_key(self):
        """AnthropicClient(api_key='sk-test') sets self.api_key."""  # pragma: allowlist secret
        client = AnthropicClient(api_key="sk-test")  # pragma: allowlist secret
        assert client.api_key == "sk-test"  # pragma: allowlist secret

    def test_init_default_model(self):
        """Default model matches ANTHROPIC_DEFAULT_MODEL."""
        client = AnthropicClient(api_key="sk-test")  # pragma: allowlist secret
        assert client.model == ANTHROPIC_DEFAULT_MODEL

    def test_init_from_env(self):
        """Client reads API key from ANTHROPIC_API_KEY env var."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-env"}):  # pragma: allowlist secret
            client = AnthropicClient()
            assert client.api_key == "sk-env"  # pragma: allowlist secret


# ---------------------------------------------------------------------------
# TestAnthropicClientGenerate
# ---------------------------------------------------------------------------


class TestAnthropicClientGenerate:
    """Tests for AnthropicClient.generate() method."""

    def _make_mock_response(self, text="Hello"):
        """Create a mock requests.Response for Anthropic Messages API."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"content": [{"type": "text", "text": text}]}
        mock_resp.raise_for_status.return_value = None
        return mock_resp

    @patch("llm_client.requests.post")
    def test_generate_success(self, mock_post):
        """Successful generate returns extracted text."""
        mock_post.return_value = self._make_mock_response("Hello")
        client = AnthropicClient(api_key="sk-test")
        result = client.generate("Say hello")
        assert result == "Hello"

    @patch("llm_client.requests.post")
    def test_generate_uses_xapikey_header(self, mock_post):
        """Headers include 'x-api-key'."""
        mock_post.return_value = self._make_mock_response()
        client = AnthropicClient(api_key="sk-test")
        client.generate("Hi")
        call_kwargs = mock_post.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
        assert "x-api-key" in headers
        assert headers["x-api-key"] == "sk-test"

    @patch("llm_client.requests.post")
    def test_generate_uses_anthropic_version_header(self, mock_post):
        """Headers include 'anthropic-version'."""
        mock_post.return_value = self._make_mock_response()
        client = AnthropicClient(api_key="sk-test")
        client.generate("Hi")
        call_kwargs = mock_post.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
        assert "anthropic-version" in headers
        assert headers["anthropic-version"] == ANTHROPIC_API_VERSION

    @patch("llm_client.requests.post")
    def test_generate_sends_system_prompt(self, mock_post):
        """When system_message is provided, body['system'] is set."""
        mock_post.return_value = self._make_mock_response()
        client = AnthropicClient(api_key="sk-test")
        client.generate("Hi", system_message="You are a lawyer")
        call_kwargs = mock_post.call_args
        body = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert body["system"] == "You are a lawyer"

    @patch("llm_client.requests.post")
    def test_generate_system_not_in_messages(self, mock_post):
        """System message is NOT in the messages array."""
        mock_post.return_value = self._make_mock_response()
        client = AnthropicClient(api_key="sk-test")
        client.generate("Hi", system_message="You are a lawyer")
        call_kwargs = mock_post.call_args
        body = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        roles = [m["role"] for m in body["messages"]]
        assert "system" not in roles

    @patch("llm_client.requests.post")
    def test_generate_max_tokens_required(self, mock_post):
        """Body passed to requests.post contains 'max_tokens'."""
        mock_post.return_value = self._make_mock_response()
        client = AnthropicClient(api_key="sk-test")
        client.generate("Hi")
        call_kwargs = mock_post.call_args
        body = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert "max_tokens" in body

    def test_generate_raises_on_missing_api_key(self):
        """AnthropicClient(api_key='').generate() raises ValueError."""
        # Patch env to ensure no ANTHROPIC_API_KEY fallback
        env_copy = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        with patch.dict(os.environ, env_copy, clear=True):
            client = AnthropicClient(api_key="")
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                client.generate("Hello")

    @patch("llm_client.requests.post")
    def test_generate_raises_on_http_error(self, mock_post):
        """HTTP errors propagate from generate()."""
        import requests as req
        mock_post.return_value = MagicMock()
        mock_post.return_value.raise_for_status.side_effect = req.HTTPError("500 Server Error")
        client = AnthropicClient(api_key="sk-test")
        with pytest.raises(req.HTTPError):
            client.generate("Hello")

    def test_stream_raises_not_implemented(self):
        """stream() raises NotImplementedError."""
        client = AnthropicClient(api_key="sk-test")
        with pytest.raises(NotImplementedError):
            client.generate_stream("Hello")


# ---------------------------------------------------------------------------
# TestOpenRouterClientInit
# ---------------------------------------------------------------------------


class TestOpenRouterClientInit:
    """Tests for OpenRouterClient initialization."""

    def test_init_default_base_url(self):
        """OpenRouterClient uses openrouter.ai URL."""
        client = OpenRouterClient(api_key="or-test")
        assert "openrouter.ai" in client.base_url

    def test_init_from_env(self):
        """Client reads API key from OPENROUTER_API_KEY env var."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "or-test"}):  # pragma: allowlist secret
            client = OpenRouterClient()
            assert client.api_key == "or-test"  # pragma: allowlist secret

    def test_is_openai_compatible(self):
        """OpenRouterClient is an instance of OpenAICompatibleClient."""
        client = OpenRouterClient(api_key="or-test")
        assert isinstance(client, OpenAICompatibleClient)

    def test_init_default_model(self):
        """OpenRouterClient default model starts with 'deepseek'."""
        client = OpenRouterClient(api_key="or-test")
        assert client.model.startswith("deepseek")


# ---------------------------------------------------------------------------
# TestCreateLlmClientFactory
# ---------------------------------------------------------------------------


class TestCreateLlmClientFactory:
    """Tests for the create_llm_client() factory function."""

    def test_factory_creates_anthropic(self):
        """create_llm_client('anthropic') returns AnthropicClient."""
        client = create_llm_client("anthropic", model="claude-haiku-3-5-20241022", api_key="sk-test")
        assert isinstance(client, AnthropicClient)

    def test_factory_creates_openrouter(self):
        """create_llm_client('openrouter') returns OpenRouterClient."""
        client = create_llm_client("openrouter", api_key="or-test")
        assert isinstance(client, OpenRouterClient)

    def test_factory_unknown_raises(self):
        """create_llm_client('invalid-xyz') raises ValueError."""
        with pytest.raises(ValueError, match="Unknown provider"):
            create_llm_client("invalid-xyz")

    @patch("llm_client.CopilotChatClient._auto_discover_oauth_token", return_value="fake-token")
    @patch("llm_client.CopilotChatClient._exchange_and_store_token")
    def test_factory_creates_all_8_providers(self, mock_exchange, mock_discover):
        """Factory can create clients for all 8 known providers."""
        env_keys = {
            "ANTHROPIC_API_KEY": "sk",  # pragma: allowlist secret
            "OPENROUTER_API_KEY": "or",  # pragma: allowlist secret
            "GROQ_API_KEY": "gq",  # pragma: allowlist secret
            "GEMINI_API_KEY": "gm",  # pragma: allowlist secret
            "MISTRAL_API_KEY": "ms",  # pragma: allowlist secret
            "NVIDIA_API_KEY": "nv",  # pragma: allowlist secret
            "ANTIGRAVITY_REFRESH_TOKEN": "ag",  # pragma: allowlist secret
        }
        with patch.dict(os.environ, env_keys):
            for provider in KNOWN_PROVIDERS:
                client = create_llm_client(provider)
                assert client is not None

    def test_factory_model_override_anthropic(self):
        """Model override works for anthropic."""
        client = create_llm_client("anthropic", model="claude-opus-4-20250514", api_key="sk-test")
        assert client.model == "claude-opus-4-20250514"

    def test_factory_model_override_openrouter(self):
        """Model override works for openrouter."""
        client = create_llm_client("openrouter", model="qwen/qwen-2.5-72b-instruct", api_key="or-test")
        assert client.model == "qwen/qwen-2.5-72b-instruct"


# ---------------------------------------------------------------------------
# TestAntigravityConstants
# ---------------------------------------------------------------------------


class TestAntigravityConstants:
    """Tests for Antigravity-specific constants."""

    def test_api_url(self):
        """ANTIGRAVITY_API_URL contains 'daily'."""
        assert "daily" in ANTIGRAVITY_API_URL

    def test_default_model(self):
        """ANTIGRAVITY_DEFAULT_MODEL contains 'gemini'."""
        assert "gemini" in ANTIGRAVITY_DEFAULT_MODEL

    def test_default_project_id(self):
        """ANTIGRAVITY_DEFAULT_PROJECT_ID is non-empty."""
        assert ANTIGRAVITY_DEFAULT_PROJECT_ID


# ---------------------------------------------------------------------------
# TestAntigravityClientInit
# ---------------------------------------------------------------------------


class TestAntigravityClientInit:
    """Tests for AntigravityClient initialization."""

    def test_init_with_token_only(self):
        """AntigravityClient with plain token uses default project."""
        client = AntigravityClient(refresh_token="mytoken")
        assert client._refresh_token == "mytoken"
        assert client.project_id == ANTIGRAVITY_DEFAULT_PROJECT_ID

    def test_init_with_token_and_project(self):
        """AntigravityClient with 'token|project' parses both."""
        client = AntigravityClient(refresh_token="mytoken|myproject")
        assert client._refresh_token == "mytoken"
        assert client.project_id == "myproject"

    def test_init_default_model(self):
        """Default model matches ANTIGRAVITY_DEFAULT_MODEL."""
        client = AntigravityClient(refresh_token="tok")
        assert client.model == ANTIGRAVITY_DEFAULT_MODEL

    def test_init_custom_model(self):
        """Custom model override works."""
        client = AntigravityClient(refresh_token="tok", model="antigravity-gemini-3-pro")
        assert client.model == "antigravity-gemini-3-pro"

    def test_init_missing_token_raises(self):
        """Missing token raises ValueError."""
        env_backup = os.environ.pop("ANTIGRAVITY_REFRESH_TOKEN", None)
        try:
            with pytest.raises(ValueError, match="ANTIGRAVITY_REFRESH_TOKEN"):
                AntigravityClient()
        finally:
            if env_backup:
                os.environ["ANTIGRAVITY_REFRESH_TOKEN"] = env_backup

    def test_init_from_env(self, monkeypatch):
        """Client reads token from ANTIGRAVITY_REFRESH_TOKEN env var."""
        monkeypatch.setenv("ANTIGRAVITY_REFRESH_TOKEN", "envtoken|envproject")
        client = AntigravityClient()
        assert client._refresh_token == "envtoken"
        assert client.project_id == "envproject"


# ---------------------------------------------------------------------------
# TestAntigravityClientGenerate
# ---------------------------------------------------------------------------


class TestAntigravityClientGenerate:
    """Tests for AntigravityClient.generate() method."""

    def _make_sse_stream_response(self, text="Respons hukum", status_code=200):
        """Create a mock requests.Response for Antigravity SSE streaming API.

        The response format wraps candidates inside a 'response' object:
        data: {"response": {"candidates": [{"content": {"parts": [{"text": "..."}]}}]}}
        """
        import json as _json
        sse_chunk = _json.dumps({
            "response": {
                "candidates": [{"content": {"parts": [{"text": text}]}}]
            }
        })
        sse_line = f"data: {sse_chunk}".encode("utf-8")

        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.raise_for_status = MagicMock()
        mock_resp.iter_lines.return_value = iter([sse_line])
        return mock_resp

    def test_generate_success(self):
        """Successful generate returns extracted text."""
        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "acc_tok", "expires_in": 3600}
        mock_token_resp.raise_for_status = MagicMock()

        mock_stream_resp = self._make_sse_stream_response("Respons hukum")

        with patch("llm_client.requests.post", side_effect=[mock_token_resp, mock_stream_resp]):
            client = AntigravityClient(refresh_token="tok")
            result = client.generate("Apa itu PT?")
        assert result == "Respons hukum"

    def test_generate_with_system_message(self):
        """System message is included as user/model pair in contents."""
        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "acc_tok", "expires_in": 3600}
        mock_token_resp.raise_for_status = MagicMock()

        mock_stream_resp = self._make_sse_stream_response("Result")

        with patch("llm_client.requests.post", side_effect=[mock_token_resp, mock_stream_resp]) as mock_post:
            client = AntigravityClient(refresh_token="tok")
            result = client.generate("Question", system_message="Be a lawyer")
        assert result == "Result"
        # Verify the generate_stream POST was called with contents including system turn
        gen_call = mock_post.call_args_list[1]
        body = gen_call.kwargs.get("json") or gen_call[1].get("json")
        contents = body["request"]["contents"]
        assert len(contents) == 3  # system user + model ack + actual user

    def test_generate_empty_candidates_returns_empty(self):
        """Empty candidates list returns empty string."""
        import json as _json
        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "acc_tok", "expires_in": 3600}
        mock_token_resp.raise_for_status = MagicMock()

        sse_line = f'data: {_json.dumps({"response": {"candidates": []}})}'.encode("utf-8")
        mock_stream_resp = MagicMock()
        mock_stream_resp.status_code = 200
        mock_stream_resp.raise_for_status = MagicMock()
        mock_stream_resp.iter_lines.return_value = iter([sse_line])

        with patch("llm_client.requests.post", side_effect=[mock_token_resp, mock_stream_resp]):
            client = AntigravityClient(refresh_token="tok")
            result = client.generate("Q")
        assert result == ""

    def test_generate_raises_after_retries(self):
        """RuntimeError raised after all retries exhausted."""
        import requests as req_lib
        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "acc_tok", "expires_in": 3600}
        mock_token_resp.raise_for_status = MagicMock()

        with patch("llm_client.requests.post", side_effect=[
            mock_token_resp,
            req_lib.exceptions.ConnectionError("timeout"),
            req_lib.exceptions.ConnectionError("timeout"),
            req_lib.exceptions.ConnectionError("timeout"),
        ]):
            with patch("llm_client.time.sleep"):
                client = AntigravityClient(refresh_token="tok")
                with pytest.raises(RuntimeError, match="AntigravityClient"):
                    client.generate("Q")


# ---------------------------------------------------------------------------
# TestCreateLlmClientAntigravity
# ---------------------------------------------------------------------------


class TestCreateLlmClientAntigravity:
    """Tests for create_llm_client('antigravity')."""

    def test_create_antigravity_client(self):
        """create_llm_client('antigravity') returns AntigravityClient."""
        client = create_llm_client("antigravity", refresh_token="tok")
        assert isinstance(client, AntigravityClient)

    def test_antigravity_in_known_providers(self):
        """'antigravity' is in KNOWN_PROVIDERS."""
        assert "antigravity" in KNOWN_PROVIDERS
