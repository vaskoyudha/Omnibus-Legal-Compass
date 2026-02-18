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
