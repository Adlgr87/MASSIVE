"""Contract tests for POST /v1/llm/run_simulation (canonical backend).

Validates the endpoint against the canonical contract declared in
``configs/llm_contract/massive_llm_contract.json`` (v1.1.0) and implemented by
``backend/app/routers/llm.py`` + ``services/llm_orchestrator.py``:

    response = {sim_id, motor, config, summary, narrative,
                results{sim_id, motor, payload, timeline, final_state},
                assumptions, factbook_params}

Hermetic: all LLM provider keys are cleared from the environment so the
orchestrator uses its documented no-LLM fallbacks and no network calls occur.

Regression note (2026-08-20): an earlier revision of this file imported a
``create_app`` factory and asserted a ``classified_motor`` contract that never
existed in ``backend/app`` (PR #84 divergence). This version asserts the
shipped contract.
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

from backend.app.main import app  # noqa: E402

_PROVIDER_KEY_VARS = ("GROQ_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY")


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Authenticated client; provider keys cleared for hermetic (no-LLM) runs."""
    for var in _PROVIDER_KEY_VARS:
        monkeypatch.delenv(var, raising=False)
    return TestClient(app)


AUTH = {"X-API-Key": "dev-secret-key"}


def _post(client: TestClient, body: dict, headers: dict | None = None) -> object:
    return client.post(
        "/v1/llm/run_simulation", json=body, headers=headers if headers is not None else AUTH
    )


def test_multilayer_basic(client: TestClient):
    """Opinion-dynamics intent classifies as multilayer_engine and returns the
    canonical response envelope."""
    resp = _post(client, {"intent": "Simula la dinámica de opinión social en una red"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["motor"] == "multilayer_engine"
    assert data["sim_id"].startswith("sim_")
    results = data["results"]
    assert results["motor"] == data["motor"]
    assert results["sim_id"] == data["sim_id"]
    assert isinstance(results["payload"], dict)
    assert isinstance(results["timeline"], list) and results["timeline"]
    assert isinstance(data["assumptions"], list) and data["assumptions"]
    assert data["summary"]["motor"] == "multilayer_engine"
    assert "indicators" in data["summary"]


def test_energy_with_factbook_brasil(client: TestClient):
    """`energía` keyword + country BR dispatches energy_engine with Factbook
    augmentation (guards against silent scalar/multilayer fallback)."""
    resp = _post(
        client,
        {
            "intent": "Simula el paisaje de energía social para Brasil con desigualdad",
            "country": "BR",
            "simulation_steps": 20,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["motor"] == "energy_engine"
    assert data["factbook_params"], "Factbook augmentation expected for country=BR"
    assert data["summary"]["factbook_country"] is not None
    assert data["results"]["motor"] == "energy_engine"


def test_forecast_without_horizon_is_ambiguous_422(client: TestClient):
    """Forecast-classified intent without a temporal horizon asks the client
    for the missing field (422 + requested_fields)."""
    resp = _post(client, {"intent": "Predecir la viralidad de una noticia en Brasil"})
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert isinstance(detail, dict)
    assert "temporal_horizon_days" in detail["requested_fields"]
    assert detail["motor"] == "forecast"


def test_forecast_with_motor_override_runs(client: TestClient):
    """Explicit motor=forecast + simulation_steps bypasses the ambiguity gate."""
    resp = _post(
        client,
        {
            "intent": "Predecir la viralidad de una noticia en Brasil",
            "motor": "forecast",
            "simulation_steps": 14,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["motor"] == "forecast"
    assert data["results"]["motor"] == "forecast"


def test_social_architect_without_llm_key_returns_503(client: TestClient):
    """social_architect is inherently LLM-driven: without any provider key the
    endpoint must fail closed with 503 and an actionable message."""
    resp = _post(client, {"intent": "Qué intervención reduce la polarización en Estados Unidos"})
    assert resp.status_code == 503, resp.text
    assert "API key" in resp.json()["detail"]


def test_empty_intent_returns_422(client: TestClient):
    resp = _post(client, {"intent": ""})
    assert resp.status_code == 422, resp.text
    assert "intent" in resp.text


def test_unknown_fields_are_rejected_422(client: TestClient):
    """DTO is extra=forbid: contract drift must fail loudly (e.g. client-side
    `api_key` fields from foreign contracts)."""
    resp = _post(client, {"intent": "Simula una red", "api_key": "badkey00"})
    assert resp.status_code == 422, resp.text
    assert "extra_forbidden" in resp.text


def test_invalid_motor_returns_422(client: TestClient):
    resp = _post(client, {"intent": "Simula algo", "motor": "no_such_motor"})
    assert resp.status_code == 422, resp.text
    assert "literal_error" in resp.text


def test_requires_api_key_401(client: TestClient):
    """No X-API-Key → 401 (dev fallback key is still required in development)."""
    resp = _post(client, {"intent": "Simula una red"}, headers={})
    assert resp.status_code == 401, resp.text
