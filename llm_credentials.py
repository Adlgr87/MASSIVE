"""Backward-compatible re-export — implementation lives in massive.core.llm_credentials."""

from massive.core.llm_credentials import (  # noqa: F401
    PROVIDER_ENV_KEYS,
    get_provider_api_key,
    persist_provider_api_key,
    resolve_provider_api_key,
)

__all__ = [
    "PROVIDER_ENV_KEYS",
    "get_provider_api_key",
    "persist_provider_api_key",
    "resolve_provider_api_key",
]
