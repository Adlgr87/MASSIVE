"""Helpers compartidos para credenciales de proveedores LLM."""

from __future__ import annotations

import os

PROVIDER_ENV_KEYS: dict[str, str] = {
    "groq": "GROQ_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}

# In-memory store for provider API keys.  Avoids mutating os.environ
# which leaks keys to subprocesses, overwrites HF Secrets, and leaves
# stale values when providers are switched.
_provider_keys: dict[str, str] = {}


def get_provider_api_key(proveedor: str) -> str:
    """Devuelve la API key del proveedor desde el entorno, o cadena vacía."""
    env_name = PROVIDER_ENV_KEYS.get(proveedor, "")
    if not env_name:
        return ""
    # 1) In-memory store (highest priority)
    if key := _provider_keys.get(proveedor):
        return key
    # 2) os.environ fallback
    return os.getenv(env_name, "").strip()


def resolve_provider_api_key(proveedor: str, fallback: str = "") -> str:
    """Resuelve API key priorizando entorno/in-memory y luego fallback explícito."""
    key = get_provider_api_key(proveedor)
    if key:
        return key
    return fallback.strip()


def persist_provider_api_key(proveedor: str, api_key: str) -> None:
    """Persiste la API key en un dict en-memoria del módulo (no en os.environ)."""
    key = api_key.strip()
    if key:
        _provider_keys[proveedor] = key
        # Mirror to env for subprocess visibility (controlled, optional)
        env_name = PROVIDER_ENV_KEYS.get(proveedor, "")
        if env_name:
            os.environ[env_name] = key
