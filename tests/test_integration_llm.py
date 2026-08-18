from unittest.mock import MagicMock, patch

import requests.exceptions

from simulator import DEFAULT_CONFIG, llamar_llm, simular


def test_llm_selector_fallback():
    """
    Test that when the LLM provider fails (connection error), the system falls
    back to the heuristic selector and returns a valid rule dictionary.
    """
    estado = {"opinion": 0.5, "propaganda": 0.1}
    cfg = {**DEFAULT_CONFIG, "proveedor": "openai", "api_key": "fake"}

    with patch("requests.post") as mock_post:
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection Error")

        resultado = llamar_llm(estado, "campana", [estado], cfg)

        assert "regla" in resultado
        assert "razon" in resultado
        assert isinstance(resultado["regla"], int)


def test_llm_selector_success():
    """
    Test a successful LLM rule selection mock.
    """
    estado = {"opinion": 0.5, "propaganda": 0.8}
    cfg = {**DEFAULT_CONFIG, "proveedor": "groq", "api_key": "fake"}

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"regla": 1, "params": {}, "razon": "High propaganda detected"}'
                }
            }
        ]
    }

    with patch("requests.post", return_value=mock_response):
        resultado = llamar_llm(estado, "campana", [estado], cfg)

        assert resultado["regla"] == 1
        assert "High propaganda" in resultado["razon"]


def test_simulation_integration():
    """
    Test that the simular function runs end-to-end with the heuristic selector.
    """
    estado_inicial = {"opinion": 0.0, "propaganda": 0.5}
    config = {"proveedor": "heurístico", "rango": "[-1, 1] — Bipolar"}

    historial = simular(estado_inicial, pasos=10, cada_n_pasos=2, config=config)

    assert len(historial) == 11  # t=0 + 10 steps
    assert "_regla_nombre" in historial[1]
    assert all("opinion" in h for h in historial)


def test_circuit_breaker_closes_after_success():
    """Circuit stays closed while requests succeed."""
    from simulator import CircuitBreaker

    cb = CircuitBreaker(failure_threshold=3, cooldown=0.1)
    assert cb.state == "closed"
    cb.record_success()
    assert cb.state == "closed"


def test_circuit_breaker_opens_after_threshold():
    """Circuit opens after the configured failure threshold."""
    from simulator import CircuitBreaker

    cb = CircuitBreaker(failure_threshold=3, cooldown=0.5)
    for _ in range(3):
        cb.record_failure()
    assert cb.state == "open"
    assert cb.allow() is False


def test_circuit_breaker_half_open_after_cooldown():
    """Circuit returns to half-open after cooldown, then closed on success."""
    from simulator import CircuitBreaker

    cb = CircuitBreaker(failure_threshold=2, cooldown=0.2)
    for _ in range(2):
        cb.record_failure()
    import time

    time.sleep(0.25)  # supera cooldown
    assert cb.state == "half-open"
    assert cb.allow() is True
    cb.record_success()
    assert cb.state == "closed"


def test_llm_retry_on_timeout():
    """Timeout triggers retries but still yields fallback heuristic result."""
    from simulator import DEFAULT_CONFIG, llamar_llm

    estado = {"opinion": 0.5, "propaganda": 0.1}
    cfg = {
        **DEFAULT_CONFIG,
        "proveedor": "openai",
        "api_key": "fake",
        "llm_retries": 2,
        "llm_retry_backoff": 0.0,
    }

    call_count = {"n": 0}

    def _flaky_post(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] <= 2:
            raise requests.exceptions.Timeout("timeout")
        return MagicMock(
            status_code=200,
            json=lambda: {
                "choices": [{"message": {"content": '{"regla": 0, "params": {}, "razon": "ok"}'}}]
            },
        )

    with patch("requests.post", side_effect=_flaky_post):
        resultado = llamar_llm(estado, "campana", [estado], cfg)

    assert "regla" in resultado
    assert call_count["n"] == 3  # 2 reintentos + 1 exitoso


def test_llm_no_retry_on_4xx():
    """Client-side HTTP errors (except 429) are not retried."""
    from simulator import DEFAULT_CONFIG, llamar_llm

    estado = {"opinion": 0.5, "propaganda": 0.1}
    cfg = {
        **DEFAULT_CONFIG,
        "proveedor": "openai",
        "api_key": "fake",
        "llm_retries": 3,
        "llm_retry_backoff": 0.0,
    }

    call_count = {"n": 0}

    def _bad_request(*args, **kwargs):
        call_count["n"] += 1
        resp = MagicMock()
        resp.status_code = 400
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=resp)
        return resp

    with patch("requests.post", side_effect=_bad_request):
        resultado = llamar_llm(estado, "campana", [estado], cfg)

    # Fallback heurístico al fallar
    assert "regla" in resultado
    assert call_count["n"] == 1  # sin reintentos
