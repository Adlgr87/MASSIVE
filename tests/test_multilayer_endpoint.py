"""Contract tests for ``POST /v1/engine/multilayer`` (Fase 4).

The endpoint exists because the multilayer engine's *effective* dials were not
reachable over HTTP. These tests pin the contract: the parameters that matter are
accepted and actually change the result, the per-layer series are genuinely
distinct, and invalid input is rejected instead of silently ignored.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

AUTH = {"X-API-Key": "dev-secret-key"}
URL = "/v1/engine/multilayer"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Authenticated client using the documented dev fallback key."""
    monkeypatch.setenv("MASSIVE_ENV", "development")
    monkeypatch.setenv("MASSIVE_DEV_FALLBACK", "1")
    return TestClient(app)


def _post(client: TestClient, body: dict):
    return client.post(URL, json=body, headers=AUTH)


def test_endpoint_exists_and_returns_contract(client: TestClient):
    response = _post(client, {"n_agents": 60, "steps": 20})
    assert response.status_code == 200

    payload = response.json()
    assert set(payload) >= {"landscape", "series", "diagnostics", "parameters"}
    assert set(payload["series"]) == {"opinion", "layer_signal"}
    assert set(payload["series"]["layer_signal"]) == {"social", "digital", "economic"}
    assert len(payload["series"]["opinion"]) == payload["n_steps"] + 1


def test_requires_api_key(client: TestClient):
    response = client.post(URL, json={"n_agents": 20, "steps": 5})
    assert response.status_code == 401


def test_per_layer_series_are_not_duplicates(client: TestClient):
    """The three layer series must be genuinely different arrays.

    The previous /v1 multilayer response returned the same global trajectory
    three times, so the "multilayer" output was a single series duplicated.
    """
    payload = _post(client, {"n_agents": 200, "steps": 40, "seed": 42}).json()
    layers = payload["series"]["layer_signal"]
    assert layers["social"] != layers["digital"]
    assert layers["social"] != layers["economic"]
    assert layers["digital"] != layers["economic"]


def test_coupling_is_an_effective_dial(client: TestClient):
    """``coupling`` must change the headline output over HTTP."""
    polarizations = []
    for coupling in (0.0, 0.3, 0.6):
        payload = _post(
            client, {"n_agents": 200, "steps": 200, "seed": 42, "coupling": coupling}
        ).json()
        polarizations.append(payload["landscape"]["polarization"])

    assert polarizations == sorted(polarizations), polarizations
    assert polarizations[-1] - polarizations[0] > 0.02


def test_coupling_gains_override_is_honoured(client: TestClient):
    """An explicit matrix override must be able to ablate the feedback loop."""
    baseline = _post(client, {"n_agents": 200, "steps": 200, "seed": 42}).json()
    ablated = _post(
        client,
        {
            "n_agents": 200,
            "steps": 200,
            "seed": 42,
            "coupling_gains": {"info_access->opinion": 0.0},
        },
    ).json()

    assert ablated["parameters"]["coupling_gains"]["info_access->opinion"] == 0.0
    assert baseline["landscape"]["polarization"] != ablated["landscape"]["polarization"]


def test_unknown_state_variable_in_override_is_rejected(client: TestClient):
    response = _post(client, {"coupling_gains": {"nope->opinion": 1.0}})
    assert response.status_code == 422
    assert "unknown state variable" in str(response.json()["detail"])


def test_malformed_override_key_is_rejected(client: TestClient):
    response = _post(client, {"coupling_gains": {"opinion": 1.0}})
    assert response.status_code == 422


def test_unstable_dt_is_rejected(client: TestClient):
    """Above the explicit-Euler limit the clip would mask a blow-up."""
    assert _post(client, {"dt": 0.9}).status_code == 422
    assert _post(client, {"dt": 0.2}).status_code == 200


def test_unknown_field_is_rejected(client: TestClient):
    """extra='forbid': undocumented parameters must not be silently dropped."""
    assert _post(client, {"not_a_parameter": 1}).status_code == 422


def test_reproducible_for_a_fixed_seed(client: TestClient):
    body = {"n_agents": 150, "steps": 60, "seed": 123}
    first = _post(client, body).json()
    second = _post(client, body).json()
    assert first["series"]["opinion"] == second["series"]["opinion"]
