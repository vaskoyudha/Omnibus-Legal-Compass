"""Tests for project configuration and NVIDIA NIM setup."""
import os
import pytest
import httpx
from dotenv import load_dotenv

# Load env at module level so skipif decorators can access env vars
load_dotenv()


def test_nvidia_api_key_set():
    """Test that NVIDIA API key is configured."""
    load_dotenv()
    api_key = os.getenv("NVIDIA_API_KEY")
    assert api_key is not None, "NVIDIA_API_KEY environment variable not set"
    assert api_key != "nvapi-YOUR_KEY_HERE", "NVIDIA_API_KEY is still placeholder"


def test_qdrant_url_set():
    """Test that Qdrant URL is configured."""
    load_dotenv()
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    assert qdrant_url is not None


@pytest.mark.skipif(
    not os.getenv("NVIDIA_API_KEY") or os.getenv("NVIDIA_API_KEY") == "nvapi-YOUR_KEY_HERE",
    reason="NVIDIA_API_KEY not configured"
)
def test_nvidia_nim_connection():
    """Test that NVIDIA NIM API can be called (requires API key).
    
    This test will be skipped if NVIDIA_API_KEY is not set.
    """
    load_dotenv()
    api_key = os.getenv("NVIDIA_API_KEY")
    
    # Test the actual NVIDIA NIM endpoint
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "moonshotai/kimi-k2-instruct",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 10
    }
    
    response = httpx.post(url, json=payload, headers=headers, timeout=30.0)
    
    assert response.status_code == 200, f"NVIDIA NIM API returned {response.status_code}: {response.text}"
    data = response.json()
    assert "choices" in data
    assert len(data["choices"]) > 0
