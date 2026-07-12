"""@deprecated — re-export only. Use massive.core.llm_credentials directly."""

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
