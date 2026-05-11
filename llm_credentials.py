"""Helpers compartidos para credenciales de proveedores LLM."""

from __future__ import annotations

import os

PROVIDER_ENV_KEYS: dict[str, str] = {
    "groq": "GROQ_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


def get_provider_api_key(proveedor: str) -> str:
    """Devuelve la API key del proveedor desde el entorno, o cadena vacía."""
    env_name = PROVIDER_ENV_KEYS.get(proveedor, "")
    if not env_name:
        return ""
    return os.getenv(env_name, "").strip()


def resolve_provider_api_key(proveedor: str, fallback: str = "") -> str:
    """Resuelve API key priorizando entorno y luego fallback explícito."""
    key = get_provider_api_key(proveedor)
    if key:
        return key
    return fallback.strip()


def persist_provider_api_key(proveedor: str, api_key: str) -> None:
    """Persiste la API key en variable de entorno del proceso actual."""
    env_name = PROVIDER_ENV_KEYS.get(proveedor, "")
    key = api_key.strip()
    if env_name and key:
        os.environ[env_name] = key
