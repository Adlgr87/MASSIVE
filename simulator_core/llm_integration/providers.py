"""
LLM provider integration and API handling.
"""

import json
import requests
from typing import Dict, Optional
import logging

log = logging.getLogger(__name__)

# Provider configuration moved from simulator.py
PROVEEDORES = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "modelos_sugeridos": ["gpt-4o-mini", "gpt-4-turbo"],
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "modelos_sugeridos": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "modelos_sugeridos": ["gemini-2.0-flash-exp", "gemini-1.5-pro"],
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "modelos_sugeridos": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
    },
}


def resolve_provider_api_key(proveedor: str, fallback: str = "") -> str:
    """
    Resolves API key for a given provider.
    
    Args:
        proveedor: Provider name (openai, anthropic, gemini, groq, ollama).
        fallback: Fallback API key if provider-specific not found.
        
    Returns:
        The resolved API key or empty string.
    """
    import os
    
    # Try provider-specific env var first
    provider_key = os.getenv(f"{proveedor.upper()}_API_KEY", "")
    if provider_key:
        return provider_key
    
    # Fallback to generic API_KEY
    return fallback


def extraer_json(texto: str) -> Optional[dict]:
    """
    Extracts JSON from text response.
    
    Args:
        texto: Text potentially containing JSON.
        
    Returns:
        Parsed dict or None if parsing fails.
    """
    inicio = texto.find("{")
    fin    = texto.rfind("}") + 1
    if inicio == -1 or fin == 0:
        return None
    try:
        return json.loads(texto[inicio:fin])
    except json.JSONDecodeError:
        return None


def llamar_openai_compatible(
    prompt: str,
    base_url: str,
    modelo: str,
    cfg: dict,
    proveedor: str,
) -> Optional[dict]:
    """
    Calls OpenAI-compatible API endpoint.
    
    Args:
        prompt: The prompt to send.
        base_url: Base URL of the API.
        modelo: Model name to use.
        cfg: Configuration dictionary.
        proveedor: Provider name for API key resolution.
        
    Returns:
        Parsed response dict or None on error.
    """
    api_key = resolve_provider_api_key(proveedor, fallback=cfg.get("api_key", ""))
    if not api_key:
        log.warning(f"Sin API key para proveedor '{proveedor}'.")
        return None
        
    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": modelo,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": cfg.get("llm_temperature", 0.7),
                "max_tokens": 300,
            },
            timeout=cfg.get("llm_timeout", 30),
        )
        resp.raise_for_status()
        return extraer_json(resp.json()["choices"][0]["message"]["content"])
    except requests.exceptions.ConnectionError:
        log.error(f"No se pudo conectar a {base_url}.")
    except requests.exceptions.Timeout:
        log.warning(f"Timeout ({cfg.get('llm_timeout', 30)}s) en {base_url}.")
    except (KeyError, IndexError) as e:
        log.warning(f"Error parseando respuesta: {e}")
    return None


def llamar_ollama(prompt: str, cfg: dict) -> Optional[dict]:
    """
    Calls Ollama local LLM server.
    
    Args:
        prompt: The prompt to send.
        cfg: Configuration dictionary with ollama_host, modelo, etc.
        
    Returns:
        Parsed response dict or None on error.
    """
    try:
        resp = requests.post(
            f"{cfg['ollama_host']}/api/generate",
            json={
                "model":   cfg["modelo"],
                "prompt":  prompt,
                "stream":  False,
                "options": {"temperature": cfg["llm_temperature"]},
            },
            timeout=cfg["llm_timeout"],
        )
        resp.raise_for_status()
        return extraer_json(resp.json().get("response", ""))
    except requests.exceptions.ConnectionError:
        log.error("Ollama no responde. → ollama serve")
    except requests.exceptions.Timeout:
        log.warning(f"Timeout ({cfg['llm_timeout']}s) en Ollama.")
    except KeyError as e:
        log.warning(f"Error parseando Ollama: {e}")
    return None
