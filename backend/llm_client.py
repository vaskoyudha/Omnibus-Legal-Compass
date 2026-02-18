"""
Multi-Provider LLM Client Module.

Provides a unified interface (LLMClient Protocol) for interacting with
different AI model providers. Currently supports:
  - GitHub Copilot Chat API (default) — GPT-4o-mini, GPT-4o, Claude Sonnet 4, etc.
  - NVIDIA NIM (Kimi K2) — alternative provider

Both providers support streaming (generate_stream) and non-streaming (generate).

Usage:
    from llm_client import create_llm_client

    # Copilot Chat API (default)
    client = create_llm_client("copilot", model="gpt-4o-mini")

    # NVIDIA NIM (alternative)
    client = create_llm_client("nvidia")

    response = client.generate("What is PT?", system_message="You are a lawyer")
"""

from __future__ import annotations

import json
import logging
import os
import platform
import threading
import time
from pathlib import Path
from typing import Generator, Protocol

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# NVIDIA NIM constants (moved from rag_chain.py)
# ---------------------------------------------------------------------------
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_MODEL = "moonshotai/kimi-k2-instruct"
MAX_TOKENS = 4096
TEMPERATURE = 0.15

# ---------------------------------------------------------------------------
# Copilot Chat API constants
# ---------------------------------------------------------------------------
COPILOT_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"
COPILOT_CHAT_URL = "https://api.githubcopilot.com/chat/completions"
COPILOT_DEFAULT_MODEL = "gpt-4o-mini"

# Models included with Copilot Pro (unlimited, no premium cost)
# Note: Gemini models are NOT available via Copilot Chat API as of Feb 2026.
COPILOT_INCLUDED_MODELS = {
    "gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4",
    "gpt-4o-2024-11-20", "claude-sonnet-4",
}

# Premium models (300 requests/month on Copilot Pro)
COPILOT_PREMIUM_MODELS = {
    "claude-sonnet-4.5", "claude-opus-4.6",
    "gpt-5", "gpt-5.2", "gpt-5-mini",
}

# ---------------------------------------------------------------------------
# Device Flow constants (for interactive OAuth login — same as VS Code/OpenCode/Aider)
# ---------------------------------------------------------------------------
GITHUB_COPILOT_CLIENT_ID = "Iv1.b507a08c87ecfe98"
GITHUB_DEVICE_CODE_URL = "https://github.com/login/device/code"
GITHUB_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"


# ---------------------------------------------------------------------------
# LLMClient Protocol
# ---------------------------------------------------------------------------
class LLMClient(Protocol):
    """Protocol for LLM client implementations."""

    def generate(self, user_message: str, system_message: str | None = None) -> str:
        """Generate a response from the LLM."""
        ...

    def generate_stream(
        self, user_message: str, system_message: str | None = None
    ) -> Generator[str, None, None]:
        """Generate a streaming response from the LLM. Yields chunks of text."""
        ...


# ---------------------------------------------------------------------------
# NVIDIANimClient (moved from rag_chain.py — EXACT same behavior)
# ---------------------------------------------------------------------------
class NVIDIANimClient:
    """Client for NVIDIA NIM API with Kimi K2 model (moonshotai/kimi-k2-instruct)."""

    def __init__(
        self,
        api_key: str | None = None,
        api_url: str = NVIDIA_API_URL,
        model: str = NVIDIA_MODEL,
        max_tokens: int = MAX_TOKENS,
        temperature: float = TEMPERATURE,
    ):
        self.api_key = api_key or NVIDIA_API_KEY
        if not self.api_key:
            raise ValueError("NVIDIA_API_KEY not found in environment variables")

        self.api_url = api_url
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def generate(
        self,
        user_message: str,
        system_message: str | None = None,
    ) -> str:
        """Generate response from NVIDIA NIM API."""
        messages = []

        if system_message:
            messages.append({
                "role": "system",
                "content": system_message,
            })

        messages.append({
            "role": "user",
            "content": user_message,
        })

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False,
        }

        max_retries = 3
        last_exception: Exception | None = None
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=120,
                )
                response.raise_for_status()

                result = response.json()
                message = result["choices"][0]["message"]

                # Some models may return 'reasoning' or 'reasoning_content' instead of 'content'
                content = (
                    message.get("content")
                    or message.get("reasoning")
                    or message.get("reasoning_content")
                    or ""
                )

                if not content:
                    logger.warning(f"Empty response from model. Full message: {message}")

                return content

            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    logger.warning(
                        f"NVIDIA NIM API attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"NVIDIA NIM API error after {max_retries} attempts: {e}")

        raise RuntimeError(
            "Gagal mendapatkan respons dari layanan AI. Silakan coba lagi nanti."
        ) from last_exception

    def generate_stream(
        self,
        user_message: str,
        system_message: str | None = None,
    ):
        """Generate streaming response from NVIDIA NIM API. Yields chunks of text."""
        messages = []

        if system_message:
            messages.append({
                "role": "system",
                "content": system_message,
            })

        messages.append({
            "role": "user",
            "content": user_message,
        })

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": True,
        }

        max_retries = 3
        last_exception: Exception | None = None
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=120,
                    stream=True,
                )
                response.raise_for_status()

                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data = line[6:]  # Remove 'data: ' prefix
                            if data == '[DONE]':
                                break
                            try:
                                chunk = json.loads(data)
                                if 'choices' in chunk and len(chunk['choices']) > 0:
                                    delta = chunk['choices'][0].get('delta', {})
                                    content = delta.get('content', '')
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                continue
                return  # Success — exit retry loop

            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    logger.warning(
                        f"NVIDIA NIM API streaming attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"NVIDIA NIM API streaming error after {max_retries} attempts: {e}")

        raise RuntimeError(
            "Gagal mendapatkan respons streaming dari layanan AI. Silakan coba lagi nanti."
        ) from last_exception


# ---------------------------------------------------------------------------
# CopilotChatClient — GitHub Copilot Chat API
# ---------------------------------------------------------------------------
class CopilotChatClient:
    """Client for GitHub Copilot Chat API.

    Auth flow (same as OpenCode, Aider, LiteLLM):
      1. Get OAuth token from env var or hosts.json/apps.json
      2. Exchange for ephemeral bearer token via /copilot_internal/v2/token
      3. Use bearer token for chat completions
      4. Auto-refresh on 401 or pre-emptive (5 min before expiry)

    Requires: GitHub Copilot Pro subscription ($10/mo).
    """

    # Required Copilot headers (from OpenCode source)
    COPILOT_HEADERS = {
        "Content-Type": "application/json",
        "Copilot-Integration-Id": "vscode-chat",
        "Editor-Version": "vscode/1.95.0",
        "Editor-Plugin-Version": "copilot-chat/0.26.7",
        "User-Agent": "GitHubCopilotChat/0.26.7",
    }

    def __init__(
        self,
        model: str = COPILOT_DEFAULT_MODEL,
        api_key: str | None = None,
        max_tokens: int = MAX_TOKENS,
        temperature: float = TEMPERATURE,
        interactive: bool = True,
    ):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

        # Token management
        self._token_lock = threading.Lock()
        self._oauth_token = api_key or self._auto_discover_oauth_token(
            interactive=interactive
        )
        self._bearer_token: str = ""
        self._token_expires_at: float = 0.0

        # Warn about premium models
        if model not in COPILOT_INCLUDED_MODELS:
            logger.warning(
                f"Model '{model}' is NOT in Copilot Pro included models. "
                f"This may consume premium requests (300/month cap). "
                f"Included models: {sorted(COPILOT_INCLUDED_MODELS)}"
            )

        # Exchange OAuth token for bearer token immediately
        self._exchange_and_store_token()

        logger.info(
            f"CopilotChatClient initialized: model={self.model}, "
            f"token_expires_at={self._token_expires_at}"
        )

    @staticmethod
    def _auto_discover_oauth_token(*, interactive: bool = True) -> str:
        """Auto-discover GitHub OAuth token from env var, config files, or device flow.

        Search order:
          1. GITHUB_TOKEN env var
          2. hosts.json (platform-specific path)
          3. apps.json (platform-specific path, fallback)
          4. Interactive OAuth Device Flow (if interactive=True)

        Returns:
            OAuth token string.

        Raises:
            ValueError: If no token found and interactive=False.
        """
        # 1. Check env var
        env_token = os.environ.get("GITHUB_TOKEN")
        if env_token:
            logger.info("Using GITHUB_TOKEN from environment variable")
            return env_token

        # 2. Determine platform-specific config directories
        config_dirs: list[Path] = []
        if platform.system() == "Windows":
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            if local_appdata:
                config_dirs.append(Path(local_appdata) / "github-copilot")
        else:
            # Linux / macOS
            home = Path.home()
            config_dirs.append(home / ".config" / "github-copilot")

        # 3. Search hosts.json then apps.json in each config dir
        for config_dir in config_dirs:
            for filename in ("hosts.json", "apps.json"):
                filepath = config_dir / filename
                if not filepath.exists():
                    continue
                try:
                    data = json.loads(filepath.read_text(encoding="utf-8"))
                    # Find key containing "github.com"
                    for key, value in data.items():
                        if "github.com" in key and isinstance(value, dict):
                            token = value.get("oauth_token")
                            if token:
                                logger.info(
                                    f"Using OAuth token from {filepath}"
                                )
                                return token
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning(f"Could not read {filepath}: {e}")
                    continue

        # 4. Interactive device flow (if allowed)
        if interactive:
            logger.info(
                "No saved GitHub token found. Starting interactive login..."
            )
            return CopilotChatClient._device_flow_login()

        raise ValueError(
            "GitHub OAuth token not found. Options:\n"
            "  1. Set GITHUB_TOKEN environment variable\n"
            "  2. Run: python -m backend.llm_client login\n"
            "  3. Install 'GitHub Copilot' extension in VS Code and sign in\n"
            "Token should exist in "
            "%LOCALAPPDATA%\\github-copilot\\hosts.json (Windows) or "
            "~/.config/github-copilot/hosts.json (Linux/macOS)."
        )

    @staticmethod
    def _device_flow_login() -> str:
        """Interactive OAuth Device Flow login for GitHub Copilot.

        Same flow as VS Code Copilot, OpenCode, Aider, and LiteLLM:
          1. POST to github.com/login/device/code with client_id
          2. Show user_code + verification_uri to the user
          3. Poll github.com/login/oauth/access_token until authorized
          4. Store the OAuth token in hosts.json for future use

        Returns:
            The GitHub OAuth access_token string.

        Raises:
            RuntimeError: On network errors or timeout waiting for user.
        """
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # Step 1: Request device code
        try:
            resp = requests.post(
                GITHUB_DEVICE_CODE_URL,
                headers=headers,
                json={
                    "client_id": GITHUB_COPILOT_CLIENT_ID,
                    "scope": "read:user",
                },
                timeout=30,
            )
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(
                f"Failed to start device login flow: {e}"
            ) from e

        device_info = resp.json()
        device_code = device_info["device_code"]
        user_code = device_info["user_code"]
        verification_uri = device_info["verification_uri"]
        interval = device_info.get("interval", 5)
        expires_in = device_info.get("expires_in", 900)

        # Step 2: Display instructions to user
        print("\n" + "=" * 60)
        print("  GitHub Copilot — Device Login")
        print("=" * 60)
        print(f"\n  1. Open:  {verification_uri}")
        print(f"  2. Enter: {user_code}")
        print(f"\n  Waiting for authorization (expires in {expires_in // 60} min)...")
        print("=" * 60 + "\n")

        # Step 3: Poll for access token
        max_attempts = expires_in // interval
        poll_interval = interval

        for attempt in range(max_attempts):
            time.sleep(poll_interval)

            try:
                poll_resp = requests.post(
                    GITHUB_ACCESS_TOKEN_URL,
                    headers=headers,
                    json={
                        "client_id": GITHUB_COPILOT_CLIENT_ID,
                        "device_code": device_code,
                        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    },
                    timeout=30,
                )
                poll_resp.raise_for_status()
            except requests.exceptions.RequestException as e:
                logger.warning(f"Poll attempt {attempt + 1} failed: {e}")
                continue

            poll_data = poll_resp.json()

            if "access_token" in poll_data:
                access_token = poll_data["access_token"]
                print("  ✓ Login successful! Token saved.\n")
                logger.info("Device flow login successful")

                # Step 4: Store token for future use
                CopilotChatClient._store_oauth_token(access_token)
                return access_token

            error = poll_data.get("error", "")
            if error == "authorization_pending":
                # User hasn't clicked authorize yet — keep polling
                continue
            elif error == "slow_down":
                # GitHub wants us to back off
                poll_interval += 5
                logger.debug("Device flow: slow_down, increasing interval")
                continue
            elif error == "expired_token":
                raise RuntimeError(
                    "Device code expired. Please run login again."
                )
            elif error == "access_denied":
                raise RuntimeError(
                    "Authorization denied by user."
                )
            else:
                raise RuntimeError(
                    f"Unexpected device flow error: {error} — "
                    f"{poll_data.get('error_description', '')}"
                )

        raise RuntimeError(
            f"Timed out waiting for user authorization "
            f"(waited {expires_in}s). Please try again."
        )

    @staticmethod
    def _store_oauth_token(token: str) -> None:
        """Store OAuth token in the standard GitHub Copilot hosts.json location.

        - Windows: %LOCALAPPDATA%/github-copilot/hosts.json
        - Linux/macOS: ~/.config/github-copilot/hosts.json

        Creates the directory and file if they don't exist.
        Merges with existing hosts.json content if present.
        """
        if platform.system() == "Windows":
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            if not local_appdata:
                logger.warning(
                    "LOCALAPPDATA not set — cannot store token automatically. "
                    "Set GITHUB_TOKEN env var instead."
                )
                return
            config_dir = Path(local_appdata) / "github-copilot"
        else:
            config_dir = Path.home() / ".config" / "github-copilot"

        hosts_file = config_dir / "hosts.json"

        # Load existing data or start fresh
        existing_data: dict = {}
        if hosts_file.exists():
            try:
                existing_data = json.loads(
                    hosts_file.read_text(encoding="utf-8")
                )
            except (json.JSONDecodeError, OSError):
                existing_data = {}

        # Write/update the token
        existing_data["github.com"] = {"oauth_token": token}

        try:
            config_dir.mkdir(parents=True, exist_ok=True)
            hosts_file.write_text(
                json.dumps(existing_data, indent=2) + "\n",
                encoding="utf-8",
            )
            logger.info(f"OAuth token stored in {hosts_file}")
        except OSError as e:
            logger.warning(
                f"Could not write token to {hosts_file}: {e}. "
                f"Set GITHUB_TOKEN env var instead."
            )

    def _exchange_token(self, oauth_token: str) -> tuple[str, float]:
        """Exchange OAuth token for Copilot bearer token.

        Args:
            oauth_token: GitHub OAuth token.

        Returns:
            Tuple of (bearer_token, expires_at_timestamp).

        Raises:
            ValueError: If OAuth token is invalid/expired (401).
            RuntimeError: On other exchange errors.
        """
        headers = {
            "Authorization": f"token {oauth_token}",
            "User-Agent": "GitHubCopilotChat/0.26.7",
            "Accept": "application/json",
        }

        try:
            response = requests.get(
                COPILOT_TOKEN_URL,
                headers=headers,
                timeout=30,
            )
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to exchange token: {e}") from e

        if response.status_code == 401:
            raise ValueError(
                "GitHub OAuth token is invalid or expired. "
                "Re-authenticate with GitHub Copilot or update GITHUB_TOKEN."
            )

        if response.status_code != 200:
            raise RuntimeError(
                f"Copilot token exchange failed (HTTP {response.status_code}): "
                f"{response.text}"
            )

        data = response.json()
        bearer_token = data["token"]
        expires_at = float(data["expires_at"])

        return bearer_token, expires_at

    def _exchange_and_store_token(self) -> None:
        """Exchange OAuth token and store the bearer token (thread-safe)."""
        with self._token_lock:
            self._bearer_token, self._token_expires_at = self._exchange_token(
                self._oauth_token
            )

    def _ensure_valid_token(self) -> None:
        """Ensure bearer token is valid, refreshing if needed (thread-safe).

        Pre-emptive refresh: 5 minutes before expiry to avoid 401 storm
        with parallel workers.
        """
        if time.time() > self._token_expires_at - 300:
            logger.info("Copilot bearer token expired or near expiry, refreshing...")
            self._exchange_and_store_token()

    def generate(
        self,
        user_message: str,
        system_message: str | None = None,
    ) -> str:
        """Generate response from Copilot Chat API.

        Retry logic:
          - 3 attempts with exponential backoff
          - On 401: re-exchange token and retry (max 1 refresh per request)
          - On 429: respect Retry-After header
        """
        self._ensure_valid_token()

        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": user_message})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False,
        }

        max_retries = 3
        token_refreshed = False
        last_exception: Exception | None = None

        for attempt in range(max_retries):
            headers = {
                **self.COPILOT_HEADERS,
                "Authorization": f"Bearer {self._bearer_token}",
            }

            try:
                response = requests.post(
                    COPILOT_CHAT_URL,
                    headers=headers,
                    json=payload,
                    timeout=120,
                )

                # Handle 401 — token expired, refresh once
                if response.status_code == 401 and not token_refreshed:
                    logger.warning("Copilot API returned 401, refreshing token...")
                    self._exchange_and_store_token()
                    token_refreshed = True
                    continue  # Retry with new token (don't count as attempt)

                # Handle 429 — rate limited
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 2 ** attempt))
                    logger.warning(
                        f"Copilot API rate limited (429). "
                        f"Waiting {retry_after}s (attempt {attempt + 1}/{max_retries})..."
                    )
                    time.sleep(retry_after)
                    last_exception = requests.exceptions.HTTPError(
                        f"429 Too Many Requests", response=response
                    )
                    continue

                response.raise_for_status()

                result = response.json()
                content = result["choices"][0]["message"]["content"]

                if not content:
                    logger.warning(f"Empty response from Copilot. Full result: {result}")

                return content or ""

            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Copilot API attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"Copilot API error after {max_retries} attempts: {e}"
                    )

        raise RuntimeError(
            f"Copilot Chat API failed after {max_retries} attempts."
        ) from last_exception

    def generate_stream(
        self,
        user_message: str,
        system_message: str | None = None,
    ) -> Generator[str, None, None]:
        """Generate streaming response from Copilot Chat API. Yields chunks of text.

        Uses SSE (Server-Sent Events) format — same as OpenAI-compatible streaming.
        Handles 401 token refresh and 429 rate limiting, same as generate().
        """
        self._ensure_valid_token()

        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": user_message})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": True,
        }

        max_retries = 3
        token_refreshed = False
        last_exception: Exception | None = None

        for attempt in range(max_retries):
            headers = {
                **self.COPILOT_HEADERS,
                "Authorization": f"Bearer {self._bearer_token}",
            }

            try:
                response = requests.post(
                    COPILOT_CHAT_URL,
                    headers=headers,
                    json=payload,
                    timeout=120,
                    stream=True,
                )

                # Handle 401 — token expired, refresh once
                if response.status_code == 401 and not token_refreshed:
                    logger.warning("Copilot streaming API returned 401, refreshing token...")
                    self._exchange_and_store_token()
                    token_refreshed = True
                    continue

                # Handle 429 — rate limited
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 2 ** attempt))
                    logger.warning(
                        f"Copilot streaming API rate limited (429). "
                        f"Waiting {retry_after}s (attempt {attempt + 1}/{max_retries})..."
                    )
                    time.sleep(retry_after)
                    last_exception = requests.exceptions.HTTPError(
                        f"429 Too Many Requests", response=response
                    )
                    continue

                response.raise_for_status()

                for line in response.iter_lines():
                    if line:
                        line = line.decode("utf-8")
                        if line.startswith("data: "):
                            data = line[6:]  # Remove 'data: ' prefix
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                if "choices" in chunk and len(chunk["choices"]) > 0:
                                    delta = chunk["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                continue
                return  # Success — exit retry loop

            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Copilot streaming attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"Copilot streaming error after {max_retries} attempts: {e}"
                    )

        raise RuntimeError(
            f"Copilot Chat API streaming failed after {max_retries} attempts."
        ) from last_exception


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
KNOWN_PROVIDERS = {"nvidia", "copilot"}


def create_llm_client(
    provider: str = "copilot",
    model: str | None = None,
    **kwargs,
) -> LLMClient:
    """Create an LLM client for the specified provider.

    Args:
        provider: "copilot" (default) or "nvidia".
        model: Model name override (uses provider default if None).
        **kwargs: Additional arguments passed to the client constructor.

    Returns:
        An LLMClient instance.

    Raises:
        ValueError: If provider is unknown.
    """
    if provider == "nvidia":
        client_kwargs = {**kwargs}
        if model:
            client_kwargs["model"] = model
        return NVIDIANimClient(**client_kwargs)
    elif provider == "copilot":
        client_kwargs = {**kwargs}
        if model:
            client_kwargs["model"] = model
        return CopilotChatClient(**client_kwargs)
    else:
        raise ValueError(
            f"Unknown provider '{provider}'. Known providers: {sorted(KNOWN_PROVIDERS)}"
        )


# ---------------------------------------------------------------------------
# CLI — python -m llm_client login
# ---------------------------------------------------------------------------
def _cli_login() -> None:
    """Run interactive GitHub Copilot device flow login."""
    import sys

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print("GitHub Copilot Login — OAuth Device Flow")
    print("This stores a token so CopilotChatClient can authenticate.\n")

    try:
        token = CopilotChatClient._device_flow_login()
        # Verify the token works by exchanging it
        print("Verifying token with Copilot API...")
        headers = {
            "Authorization": f"token {token}",
            "User-Agent": "GitHubCopilotChat/0.26.7",
            "Accept": "application/json",
        }
        resp = requests.get(COPILOT_TOKEN_URL, headers=headers, timeout=30)
        if resp.status_code == 200:
            print("  ✓ Token verified — Copilot access confirmed!")
            print("\nYou can now use: create_llm_client('copilot')")
        elif resp.status_code == 401:
            print(
                "  ✗ Token exchange failed (401). "
                "Ensure you have an active GitHub Copilot subscription."
            )
            sys.exit(1)
        else:
            print(f"  ✗ Unexpected response: HTTP {resp.status_code}")
            sys.exit(1)
    except (RuntimeError, ValueError) as e:
        print(f"\nLogin failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "login":
        _cli_login()
    else:
        print("Usage: python -m llm_client login")
        print("       Authenticate with GitHub Copilot via browser.")
        sys.exit(1)
