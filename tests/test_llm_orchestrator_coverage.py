"""Coverage-expanding tests for backend.app.services.llm_orchestrator branches.

These complement tests/test_llm_endpoint.py (the 6 required contract scenarios).
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.app.main import create_app  # noqa: E402

VALID_KEY = "fake-llm-key"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _post(client, body):
    return client.post("/v1/llm/run_simulation", json=body)


def test_energy_intervention_scenario(client):
    resp = _post(client, {
        "intent": "Modelo energético de opinión para México",
        "country_code": "MX",
        "scenario": "intervention",
        "intervention_config": {"type": "info_campaign", "magnitude": 0.6},
        "api_key": VALID_KEY,
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["classified_motor"] == "energy_engine"


def test_massive_engine_dispatch(client):
    resp = _post(client, {
        "intent": "Simula una dinámica a gran escala",
        "motor_override": "massive_engine",
        "api_key": VALID_KEY,
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["classified_motor"] == "massive_engine"


def test_factbook_validation_motor(client):
    resp = _post(client, {
        "intent": "Valida los parámetros empíricos de Argentina",
        "motor_override": "factbook_validation",
        "api_key": VALID_KEY,
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["classified_motor"] == "factbook_validation"
    assert data["country_code_resolved"] == "AR"


def test_unknown_motor_override_returns_422(client):
    resp = _post(client, {
        "intent": "Simula algo",
        "motor_override": "not_a_real_motor",
        "api_key": VALID_KEY,
    })
    assert resp.status_code == 422, resp.text
    assert "requested_fields" in resp.json()


def test_unimplemented_motor_returns_422(client):
    resp = _post(client, {
        "intent": "Simula un micro-grupo de agentes",
        "api_key": VALID_KEY,
    })
    assert resp.status_code == 422, resp.text
    assert "requested_fields" in resp.json()


def test_country_name_detection_spanish(client):
    resp = _post(client, {
        "intent": "Ejecuta el modelo energético de opinión para Brasil",
        "api_key": VALID_KEY,
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["country_code_resolved"] == "BR"


def test_explicit_country_code_wins_over_name(client):
    resp = _post(client, {
        "intent": "Ejecuta el modelo energético de opinión para Brasil",
        "country_code": "US",
        "api_key": VALID_KEY,
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["country_code_resolved"] == "US"
