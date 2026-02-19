"""
Provider configuration and FallbackChain factory.

Creates a FallbackChain from available providers, ordered cheapest/fastest
first → most reliable last.  Providers whose API keys are missing are
silently skipped with a logger.warning.

Usage:
    from backend.provider_config import create_fallback_chain

    chain = create_fallback_chain()                      # default order
    chain = create_fallback_chain(["nvidia", "copilot"]) # custom order
    response = chain.generate("What is PT?")
"""

from __future__ import annotations

import logging
from typing import List, Optional

from backend.llm_client import (
    FallbackChain,
    LLMClient,
    create_llm_client,
    KNOWN_PROVIDERS,
)

logger = logging.getLogger(__name__)

DEFAULT_PROVIDER_ORDER: List[str] = [
    "groq",
    "gemini",
    "mistral",
    "copilot",
    "nvidia",
]


def create_fallback_chain(
    provider_order: Optional[List[str]] = None,
) -> FallbackChain:
    """Build a FallbackChain from available providers.

    Args:
        provider_order: Ordered list of provider names to try.
            Defaults to ``["groq", "gemini", "mistral", "copilot", "nvidia"]``.

    Returns:
        A ``FallbackChain`` instance containing only providers whose API
        keys / credentials are currently available.

    Raises:
        RuntimeError: If **no** providers could be initialised.
    """
    order = provider_order or DEFAULT_PROVIDER_ORDER

    providers: list[tuple[str, LLMClient]] = []
    for name in order:
        if name not in KNOWN_PROVIDERS:
            logger.warning(
                "Skipping unknown provider '%s' (known: %s)",
                name,
                sorted(KNOWN_PROVIDERS),
            )
            continue

        try:
            client = create_llm_client(provider=name)
            providers.append((name, client))
            logger.debug("FallbackChain: added provider '%s'", name)
        except (ValueError, EnvironmentError) as exc:
            logger.warning(
                "Skipping provider '%s' — not available: %s", name, exc
            )

    if not providers:
        raise RuntimeError(
            "No LLM providers available. Set at least one API key "
            f"for: {', '.join(order)}"
        )

    logger.info(
        "FallbackChain created with %d provider(s): %s",
        len(providers),
        [n for n, _ in providers],
    )
    return FallbackChain(providers)
