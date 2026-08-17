"""TestClient validation for POST /v1/llm/run_simulation.

Covers the contract paths from configs/llm_contract/massive_llm_contract.json:
  - multilayer básico
  - energy + Factbook Brasil
  - forecast
  - LLM key faltante (503)
  - intent ambiguo (422 + requested_fields)
  - intent vacío (422)
"""

from __future__ import annotations

import os
import sys

import pytest
from fastapi.testclient import TestClient

# Ensure repo root on sys.path so `backend.app` and `services.*` resolve.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.app.main import create_app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    """App created without API keys -> auth disabled (open dev mode).

    Each scenario supplies its own api_key override where needed.
    """
    return TestClient(create_app())


VALID_KEY = "fake-llm-key"


def _post(client: TestClient, body: dict) -> object:
    return client.post("/v1/llm/run_simulation", json=body)


def test_multilayer_basic(client: TestClient):
    """Intent clasifica en multilayer_engine y devuelve timeline + métricas."""
    resp = _post(client, {
        "intent": "Simula la dinámica de opinión social en una red",
        "api_key": VALID_KEY,
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["classified_motor"] == "multilayer_engine"
    assert "simulation_id" in data
    assert data["country_code_resolved"] == "none"
    assert isinstance(data["assumptions"], list) and data["assumptions"]
    assert "timeline" in data["result"]
    assert len(data["result"]["timeline"]) >= 1
    assert "metrics" in data["result"]
    assert data["result"]["metrics"]["dominant_rule"] == "multilayer_engine"


def test_energy_with_factbook_brasil(client: TestClient):
    """Intent con Brasil + energía usa Factbook para parámetros de país."""
    resp = _post(client, {
        "intent": "Ejecuta el modelo energético de opinión para Brasil con escenario de crisis",
        "country_code": "BR",
        "api_key": VALID_KEY,
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["classified_motor"] == "energy_engine"
    assert data["country_code_resolved"] == "BR"
    assert any("Brasil" in a or "BR" in a for a in data["assumptions"])
    # Assert energy-specific output to guard against silent scalar fallback.
    payload = data["result"]["payload"]
    assert "metrics_timeline" in payload, (
        "energy_engine dispatch must return metrics_timeline; "
        "got scalar fallback or wrong engine"
    )
    assert payload.get("summary", {}).get("regla_dominante") == "langevin_energy", (
        "energy_engine summary must carry regla_dominante='langevin_energy'"
    )


def test_forecast(client: TestClient):
    """Intent de pronóstico clasifica en forecast_model."""
    resp = _post(client, {
        "intent": "Haz un forecast de polarización para los próximos 90 días",
        "api_key": VALID_KEY,
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["classified_motor"] == "forecast_model"
    assert len(data["result"]["timeline"]) >= 1


def test_missing_llm_key_returns_503(client: TestClient):
    """Sin api_key ni variables de entorno -> 503 ServiceUnavailable."""
    # Forzar ausencia de provider keys en el proceso.
    old_env = {k: os.environ.pop(k, None) for k in
               ("GROQ_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY")}
    try:
        resp = _post(client, {"intent": "Simula la dinámica de opinión social en una red"})
        assert resp.status_code == 503, resp.text
        assert "configured" in resp.json()["detail"] or "API key" in resp.json()["detail"]
    finally:
        for k, v in old_env.items():
            if v is not None:
                os.environ[k] = v


def test_ambiguous_intent_returns_422_with_fields(client: TestClient):
    """Intent ambigüo (vago) -> 422 + requested_fields."""
    resp = _post(client, {"intent": "Brasil", "api_key": VALID_KEY})
    # "Brasil" alone has no motor keyword -> AmbiguityError -> 422
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["detail"] is not None
    assert "requested_fields" in body
    assert "motor_override" in body["requested_fields"]


def test_empty_intent_returns_422(client: TestClient):
    """intent='' falla validación pydantic (min_length 5) -> 422."""
    resp = _post(client, {"intent": "", "api_key": VALID_KEY})
    assert resp.status_code == 422, resp.text
    # Pydantic validation error mentions 'intent'
    assert "intent" in resp.text.lower()
