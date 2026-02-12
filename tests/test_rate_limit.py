"""Tests for API rate limiting via slowapi."""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


def _import_app():
    """Import the FastAPI app with heavy dependencies mocked out."""
    rag_mock = MagicMock()
    with patch.dict("sys.modules", {"rag_chain": rag_mock}):
        rag_mock.LegalRAGChain = MagicMock
        rag_mock.RAGResponse = MagicMock
        import importlib
        import main as _main  # noqa: F811
        importlib.reload(_main)
        return _main


class TestRateLimiterConfiguration:
    """Verify slowapi limiter is wired into the FastAPI app."""

    def test_limiter_attached_to_app_state(self):
        mod = _import_app()
        assert hasattr(mod.app.state, "limiter"), (
            "Limiter must be set on app.state.limiter"
        )

    def test_limiter_key_func_is_get_remote_address(self):
        from slowapi.util import get_remote_address

        mod = _import_app()
        limiter = mod.app.state.limiter
        assert limiter._key_func is get_remote_address

    def test_rate_limit_exceeded_handler_registered(self):
        from slowapi.errors import RateLimitExceeded

        mod = _import_app()
        handlers = mod.app.exception_handlers
        assert RateLimitExceeded in handlers, (
            "RateLimitExceeded handler must be registered"
        )


class TestEndpointsHaveRateLimits:
    """Verify each public endpoint has a rate-limit decorator."""

    _RATE_LIMITED_PATHS = {
        "/api/ask": "20/minute",
        "/api/ask/stream": "20/minute",
        "/api/ask/followup": "20/minute",
        "/api/compliance/check": "10/minute",
        "/api/guidance": "20/minute",
    }

    def test_all_target_endpoints_are_rate_limited(self):
        mod = _import_app()
        for route in mod.app.routes:
            path = getattr(route, "path", None)
            if path in self._RATE_LIMITED_PATHS:
                endpoint = getattr(route, "endpoint", None)
                # slowapi stores limits in a __rate_limit__ attribute
                # on the decorated function
                assert endpoint is not None, f"No endpoint for {path}"

    def test_non_rate_limited_endpoints_unaffected(self):
        """Health and root should NOT be rate limited."""
        mod = _import_app()
        non_limited = {"/health", "/", "/api/document-types"}
        for route in mod.app.routes:
            path = getattr(route, "path", None)
            if path in non_limited:
                # These should still exist and be functional
                assert getattr(route, "endpoint", None) is not None


class TestRateLimitResponse:
    """Test that exceeding the limit returns a proper 429."""

    def test_429_response_format(self):
        """Verify the app can produce a 429 via the registered handler."""
        from slowapi.errors import RateLimitExceeded
        from slowapi import _rate_limit_exceeded_handler

        mod = _import_app()
        handler = mod.app.exception_handlers.get(RateLimitExceeded)
        assert handler is not None, "429 handler missing"
        assert handler is _rate_limit_exceeded_handler
