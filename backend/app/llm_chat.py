"""Provider-agnostic chat-completions helper for UI-NG.

Uses plain ``requests`` (already a core dependency) against any
OpenAI-compatible endpoint so the translator works with Groq, OpenAI,
OpenRouter or a local Ollama instance. Every call is wrapped in a safe
fallback: if anything fails, callers degrade to the heuristic path.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Optional

import requests

log = logging.getLogger("massive.ui_ng.llm_chat")

# Provider base URLs (OpenAI-compatible chat completions).
_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}

_DEFAULT_MODELS = {
    "groq": "llama-3.3-70b-versatile",
    "openai": "gpt-4o-mini",
    "openrouter": "meta-llama/llama-3.3-70b-instruct",
}


def resolve_provider() -> dict[str, Any]:
    """Resolve provider, model, base URL and API key from environment.

    Returns:
        Dict with ``provider``, ``model``, ``base_url``, ``api_key`` and
        ``configured`` (bool). ``configured`` is False when no API key is
        available for cloud providers (Ollama counts as configured when its
        host is reachable — checked lazily at call time).
    """
    provider = os.getenv("PROVIDER", "groq").strip().lower() or "groq"
    api_key = ""
    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY", "")
    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
    elif provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
    elif provider == "ollama":
        api_key = "ollama"  # Ollama does not require a key.
    else:
        # Unknown provider → try generic OpenAI-compatible env config.
        api_key = os.getenv("OPENAI_API_KEY", "")

    if provider == "ollama":
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        base_url = host.rstrip("/") + "/v1"
        model = os.getenv("OLLAMA_MODEL", "llama3.2")
    else:
        base_url = _BASE_URLS.get(provider, _BASE_URLS["groq"])
        model = os.getenv("MASSIVE_LLM_MODEL", "") or _DEFAULT_MODELS.get(provider, "")

    configured = bool(api_key)
    return {
        "provider": provider,
        "model": model,
        "base_url": base_url,
        "api_key": api_key,
        "configured": configured,
    }


def chat_completion(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    max_tokens: int = 1200,
    timeout: float = 45.0,
    json_mode: bool = False,
) -> Optional[str]:
    """Send a chat completion request to the configured provider.

    Args:
        messages: OpenAI-style message list.
        temperature: Sampling temperature.
        max_tokens: Maximum completion tokens.
        timeout: Request timeout in seconds.
        json_mode: Request ``response_format={"type": "json_object"}`` when
            the provider supports it (Groq/OpenAI/OpenRouter). Falls back to
            a plain request if the provider rejects it.

    Returns:
        Assistant text, or ``None`` on any failure (callers fall back).
    """
    cfg = resolve_provider()
    if not cfg["configured"] and cfg["provider"] != "ollama":
        log.info("No LLM API key configured — chat_completion returns None")
        return None

    url = cfg["base_url"] + "/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {cfg['api_key']}",
    }
    payload: dict[str, Any] = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode and cfg["provider"] in ("groq", "openai", "openrouter"):
        payload["response_format"] = {"type": "json_object"}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        # Retry once without JSON mode when the provider rejects it.
        if resp.status_code in (400, 422) and json_mode:
            payload.pop("response_format", None)
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if resp.status_code != 200:
            log.warning("LLM chat failed (%s): %s", resp.status_code, resp.text[:300])
            from backend.app.metrics import registry

            registry.inc("llm_requests_total", {"provider": cfg["provider"], "outcome": "error"})
            return None
        data = resp.json()
        from backend.app.metrics import registry

        registry.inc("llm_requests_total", {"provider": cfg["provider"], "outcome": "ok"})
        return data["choices"][0]["message"]["content"]
    except Exception as exc:  # noqa: BLE001 — must never crash the request
        log.warning("LLM chat exception: %s", exc)
        from backend.app.metrics import registry

        registry.inc("llm_requests_total", {"provider": cfg["provider"], "outcome": "error"})
        return None


def chat_completion_stream(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    max_tokens: int = 1400,
    timeout: float = 60.0,
):
    """Stream chat-completion deltas from the configured provider.

    Yields:
        Text deltas (``str``). Stops silently on any error — callers must
        track how much text was accumulated and degrade gracefully.
    """
    cfg = resolve_provider()
    if not cfg["configured"] and cfg["provider"] != "ollama":
        log.info("No LLM API key configured — stream yields nothing")
        return

    url = cfg["base_url"] + "/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {cfg['api_key']}",
    }
    payload: dict[str, Any] = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    try:
        with requests.post(
            url, headers=headers, json=payload, stream=True, timeout=(10, timeout)
        ) as resp:
            if resp.status_code != 200:
                log.warning("LLM stream failed (%s): %s", resp.status_code, resp.text[:200])
                return
            for line in resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if chunk == "[DONE]":
                    break
                try:
                    obj = json.loads(chunk)
                except json.JSONDecodeError:
                    continue
                try:
                    delta = obj["choices"][0].get("delta", {}).get("content")
                except (IndexError, KeyError, AttributeError):
                    continue
                if delta:
                    yield delta
    except Exception as exc:  # noqa: BLE001
        log.warning("LLM stream exception: %s", exc)
        return


def extract_json(text: str) -> Optional[dict[str, Any]]:
    """Defensively extract the first JSON object from model output.

    Mirrors the tolerant parsing style of ``simulator._extraer_json``.
    """
    if not text:
        return None
    # Direct attempt.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fenced code block.
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # First {...} span (greedy from first brace to last).
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None
