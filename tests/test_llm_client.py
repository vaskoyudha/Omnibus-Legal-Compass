"""
Tests for llm_client.py — factory, NVIDIANimClient, CopilotChatClient, and thread safety.

All HTTP calls are mocked. No real API keys or network access required.
"""

import json
import logging
import os
import time
import threading
from unittest.mock import MagicMock, call, patch

import pytest
import requests as req

from llm_client import (
    CopilotChatClient,
    COPILOT_INCLUDED_MODELS,
    GITHUB_COPILOT_CLIENT_ID,
    GITHUB_DEVICE_CODE_URL,
    GITHUB_ACCESS_TOKEN_URL,
    NVIDIANimClient,
    create_llm_client,
    OpenAICompatibleClient,
    GroqClient,
    GeminiClient,
    MistralClient,
    CircuitBreaker,
    FallbackChain,
    KNOWN_PROVIDERS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_token_exchange_response(token="test-bearer-token", expires_in=3600):
    """Return a MagicMock that simulates a successful token-exchange GET."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "token": token,
        "expires_at": time.time() + expires_in,
    }
    return resp


def _mock_chat_response(content="test response"):
    """Return a MagicMock that simulates a successful chat-completion POST."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "choices": [{"message": {"content": content}}],
    }
    return resp


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------


class TestFactory:
    """Tests for create_llm_client factory function."""

    @patch.dict(os.environ, {"NVIDIA_API_KEY": "test-nvidia-key"})  # pragma: allowlist secret
    @patch("llm_client.NVIDIA_API_KEY", "test-nvidia-key")  # pragma: allowlist secret
    def test_create_nvidia_client(self):
        client = create_llm_client("nvidia")
        assert isinstance(client, NVIDIANimClient)

    @patch("llm_client.requests.get")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "gho_test_token"}, clear=False)
    def test_create_copilot_client(self, mock_get):
        mock_get.return_value = _mock_token_exchange_response()
        client = create_llm_client("copilot")
        assert isinstance(client, CopilotChatClient)

    def test_create_unknown_provider(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            create_llm_client("openai")

    @patch("llm_client.requests.get")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "gho_test_token"}, clear=False)
    def test_create_with_model(self, mock_get):
        mock_get.return_value = _mock_token_exchange_response()
        client = create_llm_client("copilot", model="gpt-4o")
        assert isinstance(client, CopilotChatClient)
        assert client.model == "gpt-4o"


# ---------------------------------------------------------------------------
# NVIDIANimClient tests
# ---------------------------------------------------------------------------


class TestNVIDIANimClient:
    """Tests for NVIDIANimClient with mocked HTTP."""

    @patch("llm_client.requests.post")
    def test_nvidia_generate_success(self, mock_post):
        mock_post.return_value = _mock_chat_response("nvidia response")
        client = NVIDIANimClient(api_key="test-key")
        result = client.generate("What is PT?")
        assert result == "nvidia response"
        mock_post.assert_called_once()

    @patch("llm_client.time.sleep")
    @patch("llm_client.requests.post")
    def test_nvidia_generate_retry(self, mock_post, mock_sleep):
        """First 2 attempts fail with RequestException, 3rd succeeds."""
        fail_effect = req.exceptions.ConnectionError("timeout")
        mock_post.side_effect = [
            fail_effect,
            fail_effect,
            _mock_chat_response("recovered"),
        ]
        client = NVIDIANimClient(api_key="test-key")
        result = client.generate("retry question")
        assert result == "recovered"
        assert mock_post.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("llm_client.time.sleep")
    @patch("llm_client.requests.post")
    def test_nvidia_generate_all_fail(self, mock_post, mock_sleep):
        """All 3 attempts fail -> RuntimeError."""
        mock_post.side_effect = req.exceptions.ConnectionError("dead")
        client = NVIDIANimClient(api_key="test-key")
        with pytest.raises(RuntimeError, match="Gagal mendapatkan respons"):
            client.generate("doomed question")
        assert mock_post.call_count == 3

    def test_nvidia_missing_api_key(self):
        """No API key -> ValueError."""
        with patch("llm_client.NVIDIA_API_KEY", None):
            with pytest.raises(ValueError, match="NVIDIA_API_KEY"):
                NVIDIANimClient(api_key=None)


# ---------------------------------------------------------------------------
# CopilotChatClient tests
# ---------------------------------------------------------------------------


class TestCopilotChatClient:
    """Tests for CopilotChatClient with mocked HTTP and file system."""

    # -- auto-discover tests --

    @patch("llm_client.requests.get")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "gho_env_token"}, clear=False)
    def test_copilot_auto_discover_env_var(self, mock_get):
        """GITHUB_TOKEN env var found -> used as OAuth token."""
        mock_get.return_value = _mock_token_exchange_response()
        client = CopilotChatClient()
        assert client._oauth_token == "gho_env_token"
        mock_get.assert_called_once()  # token exchange happened

    @patch("llm_client.requests.get")
    @patch("llm_client.platform.system", return_value="Windows")
    @patch.dict(os.environ, {"LOCALAPPDATA": ""}, clear=False)
    def test_copilot_auto_discover_hosts_json(self, mock_system, mock_get, tmp_path):
        """Mocked hosts.json -> extracts oauth_token."""
        # Remove GITHUB_TOKEN so it falls through to file discovery
        env = os.environ.copy()
        env.pop("GITHUB_TOKEN", None)

        # Create fake hosts.json
        config_dir = tmp_path / "github-copilot"
        config_dir.mkdir()
        hosts_file = config_dir / "hosts.json"
        hosts_file.write_text(
            json.dumps({"github.com": {"oauth_token": "gho_from_hosts"}}),
            encoding="utf-8",
        )

        mock_get.return_value = _mock_token_exchange_response()

        with patch.dict(os.environ, {"LOCALAPPDATA": str(tmp_path), "GITHUB_TOKEN": ""}, clear=False):
            # Clear GITHUB_TOKEN so env var path returns falsy
            with patch.dict(os.environ, {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}):
                client = CopilotChatClient()
                assert client._oauth_token == "gho_from_hosts"

    @patch("llm_client.platform.system", return_value="Windows")
    @patch.dict(os.environ, {"LOCALAPPDATA": ""}, clear=False)
    def test_copilot_auto_discover_not_found(self, mock_system, tmp_path):
        """No token anywhere and interactive=False -> ValueError."""
        with patch.dict(os.environ, {"LOCALAPPDATA": str(tmp_path)}, clear=False):
            env_no_token = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
            with patch.dict(os.environ, env_no_token, clear=True):
                with pytest.raises(ValueError, match="GitHub OAuth token not found"):
                    CopilotChatClient(interactive=False)

    # -- token exchange tests --

    @patch("llm_client.requests.get")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "gho_test"}, clear=False)
    def test_copilot_exchange_token_success(self, mock_get):
        """Successful token exchange stores bearer token."""
        mock_get.return_value = _mock_token_exchange_response(
            token="bearer-abc-123", expires_in=3600
        )
        client = CopilotChatClient()
        assert client._bearer_token == "bearer-abc-123"
        assert client._token_expires_at > time.time()

    @patch("llm_client.requests.get")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "gho_expired"}, clear=False)
    def test_copilot_exchange_token_401(self, mock_get):
        """401 from token exchange -> ValueError."""
        resp_401 = MagicMock()
        resp_401.status_code = 401
        mock_get.return_value = resp_401
        with pytest.raises(ValueError, match="invalid or expired"):
            CopilotChatClient()

    # -- generate tests --

    @patch("llm_client.requests.post")
    @patch("llm_client.requests.get")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "gho_test"}, clear=False)
    def test_copilot_generate_success(self, mock_get, mock_post):
        """Successful generate returns content string."""
        mock_get.return_value = _mock_token_exchange_response()
        mock_post.return_value = _mock_chat_response("copilot answer")
        client = CopilotChatClient()
        result = client.generate("What is PT?", system_message="You are a lawyer")
        assert result == "copilot answer"
        mock_post.assert_called_once()

    @patch("llm_client.time.sleep")
    @patch("llm_client.requests.post")
    @patch("llm_client.requests.get")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "gho_test"}, clear=False)
    def test_copilot_generate_401_refresh(self, mock_get, mock_post, mock_sleep):
        """First POST returns 401 -> refresh token -> retry succeeds."""
        # Token exchange succeeds (called during __init__ and refresh)
        mock_get.return_value = _mock_token_exchange_response()

        # First POST: 401, second POST: success
        resp_401 = MagicMock()
        resp_401.status_code = 401
        resp_401.raise_for_status = MagicMock(
            side_effect=req.exceptions.HTTPError("401")
        )

        mock_post.side_effect = [resp_401, _mock_chat_response("after refresh")]

        client = CopilotChatClient()
        result = client.generate("test question")
        assert result == "after refresh"
        # get called at least twice: init exchange + refresh on 401
        assert mock_get.call_count >= 2

    @patch("llm_client.requests.post")
    @patch("llm_client.requests.get")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "gho_test"}, clear=False)
    def test_copilot_generate_stream_yields_chunks(self, mock_get, mock_post):
        """generate_stream yields SSE chunks from Copilot API."""
        mock_get.return_value = _mock_token_exchange_response()

        # Simulate SSE stream
        lines = [
            b'data: {"choices":[{"delta":{"content":"chunk1"}}]}',
            b'data: {"choices":[{"delta":{"content":"chunk2"}}]}',
            b'data: [DONE]',
        ]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_lines.return_value = lines
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client = CopilotChatClient()
        chunks = list(client.generate_stream("test"))
        assert chunks == ["chunk1", "chunk2"]

    @patch("llm_client.requests.get")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "gho_test"}, clear=False)
    def test_copilot_premium_model_warning(self, mock_get, caplog):
        """Model not in COPILOT_INCLUDED_MODELS -> logs WARNING."""
        mock_get.return_value = _mock_token_exchange_response()
        premium_model = "o1-preview"
        assert premium_model not in COPILOT_INCLUDED_MODELS

        with caplog.at_level(logging.WARNING, logger="llm_client"):
            client = CopilotChatClient(model=premium_model)

        assert any("NOT in Copilot Pro included models" in msg for msg in caplog.messages)
        assert client.model == premium_model


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------


class TestThreadSafety:
    """Tests for concurrent access to CopilotChatClient."""

    @patch("llm_client.time.sleep")
    @patch("llm_client.requests.post")
    @patch("llm_client.requests.get")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "gho_test"}, clear=False)
    def test_copilot_concurrent_generate(self, mock_get, mock_post, mock_sleep):
        """5 threads call generate() simultaneously -> no crashes, all return valid results."""
        mock_get.return_value = _mock_token_exchange_response()
        mock_post.return_value = _mock_chat_response("concurrent ok")

        client = CopilotChatClient()

        results = [None] * 5
        errors = [None] * 5

        def _worker(idx):
            try:
                results[idx] = client.generate(f"question {idx}")
            except Exception as exc:
                errors[idx] = exc

        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        for i in range(5):
            assert errors[i] is None, f"Thread {i} raised: {errors[i]}"
            assert results[i] == "concurrent ok"


# ---------------------------------------------------------------------------
# Device Flow tests
# ---------------------------------------------------------------------------


def _mock_device_code_response():
    """Simulate POST github.com/login/device/code success."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "device_code": "dc_test_123",
        "user_code": "ABCD-1234",
        "verification_uri": "https://github.com/login/device",
        "interval": 1,  # short for testing
        "expires_in": 60,
    }
    return resp


def _mock_access_token_response(token="gho_device_flow_token"):
    """Simulate POST github.com/login/oauth/access_token with token."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"access_token": token}
    return resp


def _mock_pending_response():
    """Simulate authorization_pending poll response."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"error": "authorization_pending"}
    return resp


def _mock_slow_down_response():
    """Simulate slow_down poll response."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"error": "slow_down"}
    return resp


class TestDeviceFlowLogin:
    """Tests for CopilotChatClient._device_flow_login (mocked HTTP)."""

    @patch("llm_client.CopilotChatClient._store_oauth_token")
    @patch("llm_client.time.sleep")
    @patch("llm_client.requests.post")
    def test_device_flow_success(self, mock_post, mock_sleep, mock_store):
        """Immediate authorization -> returns access_token and stores it."""
        mock_post.side_effect = [
            _mock_device_code_response(),     # Step 1: device code
            _mock_access_token_response(),    # Step 3: poll -> token
        ]

        token = CopilotChatClient._device_flow_login()

        assert token == "gho_device_flow_token"
        mock_store.assert_called_once_with("gho_device_flow_token")
        # First POST = device code, second POST = poll
        assert mock_post.call_count == 2

    @patch("llm_client.CopilotChatClient._store_oauth_token")
    @patch("llm_client.time.sleep")
    @patch("llm_client.requests.post")
    def test_device_flow_pending_then_success(self, mock_post, mock_sleep, mock_store):
        """2 pending polls, then authorized -> returns token."""
        mock_post.side_effect = [
            _mock_device_code_response(),     # device code
            _mock_pending_response(),         # poll 1: pending
            _mock_pending_response(),         # poll 2: pending
            _mock_access_token_response(),    # poll 3: success
        ]

        token = CopilotChatClient._device_flow_login()

        assert token == "gho_device_flow_token"
        assert mock_post.call_count == 4
        # sleep called once per poll (3 polls total)
        assert mock_sleep.call_count == 3

    @patch("llm_client.CopilotChatClient._store_oauth_token")
    @patch("llm_client.time.sleep")
    @patch("llm_client.requests.post")
    def test_device_flow_slow_down(self, mock_post, mock_sleep, mock_store):
        """slow_down response -> increases interval, then succeeds."""
        mock_post.side_effect = [
            _mock_device_code_response(),     # device code
            _mock_slow_down_response(),       # poll 1: slow_down
            _mock_access_token_response(),    # poll 2: success
        ]

        token = CopilotChatClient._device_flow_login()

        assert token == "gho_device_flow_token"
        assert mock_post.call_count == 3

    @patch("llm_client.time.sleep")
    @patch("llm_client.requests.post")
    def test_device_flow_access_denied(self, mock_post, mock_sleep):
        """User denies authorization -> RuntimeError."""
        denied_resp = MagicMock()
        denied_resp.status_code = 200
        denied_resp.raise_for_status = MagicMock()
        denied_resp.json.return_value = {"error": "access_denied"}

        mock_post.side_effect = [
            _mock_device_code_response(),
            denied_resp,
        ]

        with pytest.raises(RuntimeError, match="denied by user"):
            CopilotChatClient._device_flow_login()

    @patch("llm_client.time.sleep")
    @patch("llm_client.requests.post")
    def test_device_flow_expired_token(self, mock_post, mock_sleep):
        """Device code expires -> RuntimeError."""
        expired_resp = MagicMock()
        expired_resp.status_code = 200
        expired_resp.raise_for_status = MagicMock()
        expired_resp.json.return_value = {"error": "expired_token"}

        mock_post.side_effect = [
            _mock_device_code_response(),
            expired_resp,
        ]

        with pytest.raises(RuntimeError, match="Device code expired"):
            CopilotChatClient._device_flow_login()

    @patch("llm_client.requests.post")
    def test_device_flow_network_error(self, mock_post):
        """Network error on initial device code request -> RuntimeError."""
        mock_post.side_effect = req.exceptions.ConnectionError("no network")

        with pytest.raises(RuntimeError, match="Failed to start device login"):
            CopilotChatClient._device_flow_login()

    @patch("llm_client.CopilotChatClient._store_oauth_token")
    @patch("llm_client.time.sleep")
    @patch("llm_client.requests.post")
    def test_device_flow_uses_correct_client_id(self, mock_post, mock_sleep, mock_store):
        """Device code request uses the correct GitHub client_id."""
        mock_post.side_effect = [
            _mock_device_code_response(),
            _mock_access_token_response(),
        ]

        CopilotChatClient._device_flow_login()

        # Check first POST call (device code request)
        first_call = mock_post.call_args_list[0]
        assert first_call[0][0] == GITHUB_DEVICE_CODE_URL
        posted_json = first_call[1]["json"]
        assert posted_json["client_id"] == GITHUB_COPILOT_CLIENT_ID
        assert posted_json["scope"] == "read:user"

        # Check second POST call (poll for access token)
        second_call = mock_post.call_args_list[1]
        assert second_call[0][0] == GITHUB_ACCESS_TOKEN_URL
        poll_json = second_call[1]["json"]
        assert poll_json["client_id"] == GITHUB_COPILOT_CLIENT_ID
        assert poll_json["grant_type"] == "urn:ietf:params:oauth:grant-type:device_code"
        assert poll_json["device_code"] == "dc_test_123"


# ---------------------------------------------------------------------------
# Token storage tests
# ---------------------------------------------------------------------------


class TestTokenStorage:
    """Tests for CopilotChatClient._store_oauth_token (mocked filesystem)."""

    @patch("llm_client.platform.system", return_value="Windows")
    @patch.dict(os.environ, {"LOCALAPPDATA": ""}, clear=False)
    def test_store_token_creates_hosts_json(self, mock_system, tmp_path):
        """Stores token in new hosts.json when file doesn't exist."""
        with patch.dict(os.environ, {"LOCALAPPDATA": str(tmp_path)}, clear=False):
            CopilotChatClient._store_oauth_token("gho_new_token")

        hosts_file = tmp_path / "github-copilot" / "hosts.json"
        assert hosts_file.exists()
        data = json.loads(hosts_file.read_text(encoding="utf-8"))
        assert data["github.com"]["oauth_token"] == "gho_new_token"

    @patch("llm_client.platform.system", return_value="Windows")
    @patch.dict(os.environ, {"LOCALAPPDATA": ""}, clear=False)
    def test_store_token_merges_existing(self, mock_system, tmp_path):
        """Merges with existing hosts.json content."""
        config_dir = tmp_path / "github-copilot"
        config_dir.mkdir()
        hosts_file = config_dir / "hosts.json"
        hosts_file.write_text(
            json.dumps({"other_host.com": {"some_key": "value"}}),
            encoding="utf-8",
        )

        with patch.dict(os.environ, {"LOCALAPPDATA": str(tmp_path)}, clear=False):
            CopilotChatClient._store_oauth_token("gho_merged_token")

        data = json.loads(hosts_file.read_text(encoding="utf-8"))
        # New token added
        assert data["github.com"]["oauth_token"] == "gho_merged_token"
        # Existing data preserved
        assert data["other_host.com"]["some_key"] == "value"

    @patch("llm_client.platform.system", return_value="Linux")
    def test_store_token_linux_path(self, mock_system, tmp_path):
        """Uses ~/.config/github-copilot/hosts.json on Linux."""
        with patch("llm_client.Path.home", return_value=tmp_path):
            CopilotChatClient._store_oauth_token("gho_linux_token")

        hosts_file = tmp_path / ".config" / "github-copilot" / "hosts.json"
        assert hosts_file.exists()
        data = json.loads(hosts_file.read_text(encoding="utf-8"))
        assert data["github.com"]["oauth_token"] == "gho_linux_token"


# ---------------------------------------------------------------------------
# Auto-discover with interactive fallback tests
# ---------------------------------------------------------------------------


class TestAutoDiscoverInteractive:
    """Tests for _auto_discover_oauth_token with interactive device flow fallback."""

    @patch("llm_client.CopilotChatClient._device_flow_login", return_value="gho_device")
    @patch("llm_client.requests.get")
    @patch("llm_client.platform.system", return_value="Windows")
    @patch.dict(os.environ, {"LOCALAPPDATA": ""}, clear=False)
    def test_auto_discover_falls_through_to_device_flow(
        self, mock_system, mock_get, mock_login, tmp_path
    ):
        """No env var + no hosts.json + interactive=True -> device flow."""
        mock_get.return_value = _mock_token_exchange_response()

        with patch.dict(os.environ, {"LOCALAPPDATA": str(tmp_path)}, clear=False):
            env_no_token = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
            with patch.dict(os.environ, env_no_token, clear=True):
                # Re-add LOCALAPPDATA since clear=True wiped it
                with patch.dict(os.environ, {"LOCALAPPDATA": str(tmp_path)}):
                    client = CopilotChatClient()

        mock_login.assert_called_once()
        assert client._oauth_token == "gho_device"

    @patch("llm_client.platform.system", return_value="Windows")
    @patch.dict(os.environ, {"LOCALAPPDATA": ""}, clear=False)
    def test_auto_discover_interactive_false_raises(self, mock_system, tmp_path):
        """No token + interactive=False -> ValueError with instructions."""
        with patch.dict(os.environ, {"LOCALAPPDATA": str(tmp_path)}, clear=False):
            env_no_token = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
            with patch.dict(os.environ, env_no_token, clear=True):
                with pytest.raises(ValueError, match="python -m backend.llm_client login"):
                    CopilotChatClient(interactive=False)


# ---------------------------------------------------------------------------
# KNOWN_PROVIDERS registry tests
# ---------------------------------------------------------------------------


class TestKnownProviders:
    """Verify all 5 providers are in the registry."""

    def test_known_providers_complete(self):
        assert KNOWN_PROVIDERS == {"nvidia", "copilot", "groq", "gemini", "mistral"}


# ---------------------------------------------------------------------------
# OpenAICompatibleClient tests
# ---------------------------------------------------------------------------


class TestOpenAICompatibleClient:
    """Tests for OpenAICompatibleClient base class."""

    @patch("llm_client.requests.post")
    def test_generate_success(self, mock_post):
        mock_post.return_value = _mock_chat_response("base response")
        api_key = "test-key"  # pragma: allowlist secret
        client = OpenAICompatibleClient(
            base_url="https://api.example.com/v1/chat/completions",
            api_key=api_key,
            model="test-model",
        )
        result = client.generate("hello")
        assert result == "base response"
        mock_post.assert_called_once()

    @patch("llm_client.requests.post")
    def test_generate_with_system_message(self, mock_post):
        mock_post.return_value = _mock_chat_response("sys response")
        client = OpenAICompatibleClient(
            base_url="https://api.example.com/v1/chat/completions",
            api_key="test-key",  # pragma: allowlist secret
            model="test-model",
        )
        result = client.generate("hello", system_message="You are helpful")
        assert result == "sys response"
        # Verify system message was included in payload
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][0]["content"] == "You are helpful"

    @patch("llm_client.time.sleep")
    @patch("llm_client.requests.post")
    def test_generate_retry_on_failure(self, mock_post, mock_sleep):
        """First 2 fail, 3rd succeeds."""
        fail = req.exceptions.ConnectionError("down")
        mock_post.side_effect = [fail, fail, _mock_chat_response("recovered")]
        client = OpenAICompatibleClient(
            base_url="https://api.example.com/v1/chat/completions",
            api_key="test-key",  # pragma: allowlist secret
            model="test-model",
        )
        result = client.generate("retry")
        assert result == "recovered"
        assert mock_post.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("llm_client.time.sleep")
    @patch("llm_client.requests.post")
    def test_generate_all_fail(self, mock_post, mock_sleep):
        """All 3 attempts fail -> RuntimeError."""
        mock_post.side_effect = req.exceptions.ConnectionError("dead")
        client = OpenAICompatibleClient(
            base_url="https://api.example.com/v1/chat/completions",
            api_key="test-key",  # pragma: allowlist secret
            model="test-model",
        )
        with pytest.raises(RuntimeError, match="failed after 3 attempts"):
            client.generate("doomed")
        assert mock_post.call_count == 3

    @patch("llm_client.requests.post")
    def test_generate_stream_success(self, mock_post):
        """Streaming yields chunks from SSE lines."""
        sse_lines = [
            b'data: {"choices":[{"delta":{"content":"Hello"}}]}',
            b'data: {"choices":[{"delta":{"content":" world"}}]}',
            b"data: [DONE]",
        ]
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.iter_lines.return_value = sse_lines
        mock_post.return_value = resp

        client = OpenAICompatibleClient(
            base_url="https://api.example.com/v1/chat/completions",
            api_key="test-key",  # pragma: allowlist secret
            model="test-model",
        )
        chunks = list(client.generate_stream("hello"))
        assert chunks == ["Hello", " world"]


# ---------------------------------------------------------------------------
# GroqClient tests
# ---------------------------------------------------------------------------


class TestGroqClient:
    """Tests for GroqClient instantiation and API key validation."""

    @patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test_groq_key"})  # pragma: allowlist secret
    @patch("llm_client.requests.post")
    def test_groq_generate(self, mock_post):
        mock_post.return_value = _mock_chat_response("groq response")
        client = GroqClient()
        result = client.generate("test prompt")
        assert result == "groq response"
        assert "groq.com" in client.base_url

    def test_groq_missing_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="GROQ_API_KEY"):
                GroqClient()

    @patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test"})  # pragma: allowlist secret
    def test_groq_default_model(self):
        client = GroqClient()
        assert client.model == "llama-3.3-70b-versatile"

    @patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test"})  # pragma: allowlist secret
    def test_groq_custom_model(self):
        client = GroqClient(model="llama-3.1-8b-instant")
        assert client.model == "llama-3.1-8b-instant"


# ---------------------------------------------------------------------------
# GeminiClient tests
# ---------------------------------------------------------------------------


class TestGeminiClient:
    """Tests for GeminiClient instantiation and API key validation."""

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_gemini_key"})  # pragma: allowlist secret
    @patch("llm_client.requests.post")
    def test_gemini_generate(self, mock_post):
        mock_post.return_value = _mock_chat_response("gemini response")
        client = GeminiClient()
        result = client.generate("test prompt")
        assert result == "gemini response"
        assert "generativelanguage.googleapis.com" in client.base_url

    def test_gemini_missing_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                GeminiClient()

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})  # pragma: allowlist secret
    def test_gemini_default_model(self):
        client = GeminiClient()
        assert client.model == "gemini-2.5-flash"


# ---------------------------------------------------------------------------
# MistralClient tests
# ---------------------------------------------------------------------------


class TestMistralClient:
    """Tests for MistralClient instantiation and API key validation."""

    @patch.dict(os.environ, {"MISTRAL_API_KEY": "test_mistral_key"})  # pragma: allowlist secret
    @patch("llm_client.requests.post")
    def test_mistral_generate(self, mock_post):
        mock_post.return_value = _mock_chat_response("mistral response")
        client = MistralClient()
        result = client.generate("test prompt")
        assert result == "mistral response"
        assert "mistral.ai" in client.base_url

    def test_mistral_missing_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="MISTRAL_API_KEY"):
                MistralClient()

    @patch.dict(os.environ, {"MISTRAL_API_KEY": "test_key"})  # pragma: allowlist secret
    def test_mistral_default_model(self):
        client = MistralClient()
        assert client.model == "mistral-small-latest"


# ---------------------------------------------------------------------------
# Factory tests for new providers
# ---------------------------------------------------------------------------


class TestFactoryNewProviders:
    """Tests for create_llm_client with new providers."""

    @patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test"})  # pragma: allowlist secret
    def test_create_groq_client(self):
        client = create_llm_client("groq")
        assert isinstance(client, GroqClient)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})  # pragma: allowlist secret
    def test_create_gemini_client(self):
        client = create_llm_client("gemini")
        assert isinstance(client, GeminiClient)

    @patch.dict(os.environ, {"MISTRAL_API_KEY": "test_key"})  # pragma: allowlist secret
    def test_create_mistral_client(self):
        client = create_llm_client("mistral")
        assert isinstance(client, MistralClient)

    @patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test"})  # pragma: allowlist secret
    def test_create_groq_with_custom_model(self):
        client = create_llm_client("groq", model="llama-3.1-8b-instant")
        assert isinstance(client, GroqClient)
        assert client.model == "llama-3.1-8b-instant"


# ---------------------------------------------------------------------------
# CircuitBreaker tests
# ---------------------------------------------------------------------------


class TestCircuitBreaker:
    """Tests for CircuitBreaker resilience pattern."""

    def test_initial_state_closed(self):
        cb = CircuitBreaker("test")
        assert not cb.is_open()
        assert cb.consecutive_failures == 0

    def test_stays_closed_below_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert not cb.is_open()  # 2 < 3

    def test_opens_after_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open()  # 3 >= 3

    def test_resets_on_success(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.consecutive_failures == 0
        assert not cb.is_open()

    @patch("llm_client.time.time")
    def test_half_open_after_timeout(self, mock_time):
        """After recovery_timeout, circuit becomes half-open (allows one request)."""
        cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=60)

        # Trip the circuit
        mock_time.return_value = 1000.0
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open()

        # Not enough time passed
        mock_time.return_value = 1050.0
        assert cb.is_open()

        # Enough time passed -> half-open
        mock_time.return_value = 1060.0
        assert not cb.is_open()

    def test_default_parameters(self):
        cb = CircuitBreaker("test")
        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 60

    def test_thread_safety(self):
        """Concurrent failures from multiple threads don't corrupt state."""
        cb = CircuitBreaker("test", failure_threshold=100)
        threads = []
        for _ in range(50):
            t = threading.Thread(target=cb.record_failure)
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        assert cb.consecutive_failures == 50


# ---------------------------------------------------------------------------
# FallbackChain tests
# ---------------------------------------------------------------------------


class TestFallbackChain:
    """Tests for FallbackChain with mocked providers."""

    def _make_provider(self, name, response="ok", should_fail=False):
        """Create a mock (name, client) tuple."""
        client = MagicMock()
        if should_fail:
            client.generate.side_effect = RuntimeError(f"{name} failed")
            client.generate_stream.side_effect = RuntimeError(f"{name} stream failed")
        else:
            client.generate.return_value = response
            client.generate_stream.return_value = iter([response])
        return (name, client)

    def test_first_provider_succeeds(self):
        chain = FallbackChain([
            self._make_provider("groq", "groq answer"),
            self._make_provider("gemini", "gemini answer"),
        ])
        result = chain.generate("question")
        assert result == "groq answer"

    def test_fallback_to_second(self):
        chain = FallbackChain([
            self._make_provider("groq", should_fail=True),
            self._make_provider("gemini", "gemini answer"),
        ])
        result = chain.generate("question")
        assert result == "gemini answer"

    def test_all_fail_raises(self):
        chain = FallbackChain([
            self._make_provider("groq", should_fail=True),
            self._make_provider("gemini", should_fail=True),
        ])
        with pytest.raises(RuntimeError, match="All providers in fallback chain failed"):
            chain.generate("question")

    def test_skips_open_circuit(self):
        chain = FallbackChain([
            self._make_provider("groq", "groq answer"),
            self._make_provider("gemini", "gemini answer"),
        ])
        # Manually open groq's circuit
        cb = chain.circuit_breakers["groq"]
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open()

        result = chain.generate("question")
        assert result == "gemini answer"
        # Groq client should NOT have been called
        groq_client = chain.providers[0][1]
        groq_client.generate.assert_not_called()

    def test_records_success(self):
        chain = FallbackChain([
            self._make_provider("groq", "groq answer"),
        ])
        chain.generate("question")
        assert chain.circuit_breakers["groq"].consecutive_failures == 0

    def test_records_failure(self):
        chain = FallbackChain([
            self._make_provider("groq", should_fail=True),
            self._make_provider("gemini", "gemini answer"),
        ])
        chain.generate("question")
        assert chain.circuit_breakers["groq"].consecutive_failures == 1
        assert chain.circuit_breakers["gemini"].consecutive_failures == 0

    def test_stream_first_succeeds(self):
        chain = FallbackChain([
            self._make_provider("groq", "groq chunk"),
            self._make_provider("gemini", "gemini chunk"),
        ])
        chunks = list(chain.generate_stream("question"))
        assert chunks == ["groq chunk"]

    def test_stream_all_fail_raises(self):
        chain = FallbackChain([
            self._make_provider("groq", should_fail=True),
        ])
        with pytest.raises(RuntimeError, match="All providers in fallback chain failed"):
            list(chain.generate_stream("question"))
