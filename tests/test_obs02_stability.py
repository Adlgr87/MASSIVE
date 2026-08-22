"""OBS-02: retry + circuit-breaker stability for LLM transport.

Validates that transient/5xx/429 failures are retried with backoff,
that the circuit opens after the configured threshold, and that after
cooldown the simulator recovers — never propagating exceptions.
"""
from unittest.mock import MagicMock, patch

import requests

from simulator import (
    CircuitBreaker,
    _circuit_breaker,
    llamar_llm,
)


def _cfg(provider: str = "groq", retries: int = 3, backoff: float = 0.0):
    """Minimal cfg that exercises a real provider (requires API key bypass)."""
    return {
        "proveedor": provider,
        "api_key": "test-key",            # bypasses resolve_provider_api_key absence check
        "modelo": "llama-3.1-8b-instant",
        "llm_retries": retries,
        "llm_retry_backoff": backoff,     # 0 so we don't sleep during tests
    }


def _estado():
    return {"opinion": 0.3, "propaganda": 0.4, "confianza": 0.5}


# --------------------------------------------------------------------------- #
# test 1 — 3 successive failures then recovery → fallback returned, no raise
# --------------------------------------------------------------------------- #
def test_obs02_retry_fallback_then_recovery():
    # reset global circuit to a clean closed state
    _circuit_breaker.record_success()

    call_seq = []

    def fake_post(url, **kwargs):
        call_seq.append(url)
        if len(call_seq) <= 3:
            # first call (attempt 1, retry 1, retry 2) -> 503 transiently
            raise requests.exceptions.HTTPError(response=_resp(503))
        # 4th call -> 200 with a valid JSON body
        return _ok_response()

    with patch("simulator.requests.post", side_effect=fake_post), \
         patch("simulator.time.sleep") as sleep_mock:  # skip real backoff
        result = llamar_llm(_estado(), "test", [], _cfg(retries=3))

    assert sleep_mock.call_count >= 1
    assert "regla" in result
    assert "razon" in result
    assert result["regla"] in range(0, 11)
    # circuit should be CLOSED again after a successful recovery
    assert _circuit_breaker.state == "closed"


# --------------------------------------------------------------------------- #
# test 2 — circuit opens after threshold consecutive failures
# --------------------------------------------------------------------------- #
def test_obs02_circuit_opens_after_threshold(monkeypatch):
    cb = CircuitBreaker(failure_threshold=3, cooldown=60.0)

    # while closed, allow == True
    assert cb.state == "closed"
    assert cb.allow() is True

    for _ in range(3):
        cb.record_failure()
    assert cb.state == "open"
    assert cb.allow() is False

    # advance clock past cooldown -> half-open (allow == True)
    monkeypatch.setattr("simulator.time.time", lambda: cb._open_until + 1)
    assert cb.state == "half-open"
    assert cb.allow() is True

    monkeypatch.undo()  # restore real clock
    cb.record_success()
    assert cb.state == "closed"
    assert cb.allow() is True


# --------------------------------------------------------------------------- #
# test 3 — fast 429 retry then success
# --------------------------------------------------------------------------- #
def test_obs02_429_then_success():
    _circuit_breaker.record_success()

    attempts = []

    def fake_post(url, **kwargs):
        attempts.append(url)
        if len(attempts) == 1:
            raise requests.exceptions.HTTPError(response=_resp(429))
        return _ok_response()

    with patch("simulator.requests.post", side_effect=fake_post), \
         patch("simulator.time.sleep"):
        result = llamar_llm(_estado(), "test", [], _cfg(retries=2))

    assert "regla" in result
    assert len(attempts) == 2  # one failed 429, one succeeded


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _resp(code: int):
    r = requests.Response()
    r.status_code = code
    return r


def _ok_response():
    m = MagicMock()
    m.json.return_value = {
        "choices": [{"message": {"content": '{"regla": 4, "params": {"fuerza": 0.08}, "razon": "polarizacion"}'}}]
    }
    m.raise_for_status.return_value = None
    return m
