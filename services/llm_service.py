"""LLM service — credentials resolution and Social Architect client setup."""

from __future__ import annotations

import os
from typing import Any, Optional


def resolve_llm_credentials(
    provider: str = "groq",
    api_key: Optional[str] = None,
) -> dict[str, Any]:
    """Resolve provider credentials without mutating ``os.environ``.

    Args:
        provider: One of ``groq``, ``openai``, ``openrouter``, or other.
        api_key: Explicit key; if empty, environment variables are consulted.

    Returns:
        Dict with ``provider``, ``api_key``, and ``configured`` (bool).
    """
    key = api_key or ""
    if not key:
        if provider == "groq":
            key = os.getenv("GROQ_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
        elif provider == "openai":
            key = os.getenv("OPENAI_API_KEY", "")
        elif provider == "openrouter":
            key = os.getenv("OPENROUTER_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
        else:
            key = os.getenv("OPENAI_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
    return {"provider": provider, "api_key": key, "configured": bool(key)}


def setup_social_architect_client() -> Any:
    """Lazy-init the Social Architect LLM client.

    Returns:
        OpenAI-compatible client instance.

    Raises:
        ImportError: If the ``openai`` package is not installed.
    """
    from social_architect import setup_client

    return setup_client()


def wizard_config(
    description: str,
    provider: str = "groq",
    api_key: Optional[str] = None,
) -> dict[str, Any]:
    """Translate natural language into a MASSIVE config dict.

    Args:
        description: Scenario description in colloquial or technical language.
        provider: LLM provider name.
        api_key: Optional API key override.

    Returns:
        Flat config mapping suitable for UIL / simulator services.
    """
    from uil_adapter import create_uil_adapter

    creds = resolve_llm_credentials(provider, api_key)
    adapter = create_uil_adapter(
        llm_provider=creds["provider"],
        llm_api_key=creds["api_key"] or None,
    )
    return adapter.from_natural_language(description)
