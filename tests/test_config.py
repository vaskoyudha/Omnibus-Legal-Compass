"""Tests for project configuration and NVIDIA NIM setup."""
import pytest
from langchain_nvidia_ai_endpoints import ChatNVIDIA


def test_nvidia_nim_import():
    """Test that NVIDIA NIM package can be imported."""
    assert ChatNVIDIA is not None


def test_chatnvidia_instantiation():
    """Test that ChatNVIDIA can be instantiated with model name."""
    llm = ChatNVIDIA(model="moonshotai/kimi-k2.5")
    assert llm.model == "moonshotai/kimi-k2.5"


def test_nvidia_nim_connection():
    """Test that NVIDIA NIM API can be called (requires API key).
    
    This test will be skipped if NVIDIA_API_KEY is not set.
    """
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    api_key = os.getenv("NVIDIA_API_KEY")
    
    if not api_key or api_key == "nvapi-YOUR_KEY_HERE":
        pytest.skip("NVIDIA_API_KEY not configured")
    
    llm = ChatNVIDIA(
        model="moonshotai/kimi-k2.5",
        api_key=api_key
    )
    
    # Simple test query
    response = llm.invoke("Hello")
    assert response is not None
    assert len(response.content) > 0
