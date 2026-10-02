"""Regression test for the /v1/engine/energy numpy serialization failure.

``run_energy_simulation`` returns numpy arrays and scalars. The router used to
return that dict unchanged, and pydantic's response serialization — which runs
*after* the handler, outside its try/except — raised
``PydanticSerializationError: Unable to serialize unknown type: numpy.ndarray``.
Every single call to the endpoint therefore produced an unhandled 500, which
is why the GUI could never render a result.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("networkx", reason="canonical app needs the full stack")

from fastapi.testclient import TestClient  # noqa: E402

_KEY = "test-energy-key"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", _KEY)
    from backend.app.main import app

    return TestClient(app)


def test_energy_response_is_json_serializable(client):
    resp = client.post(
        "/v1/engine/energy",
        headers={"X-API-Key": _KEY},
        json={"user_goal": "test goal", "n_agents": 20, "steps": 5, "seed": 42},
    )
    assert resp.status_code == 200, resp.text

    body = resp.json()
    # Round-trips through json => contains no numpy types.
    json.dumps(body)

    for key in ("summary", "metrics_timeline", "final_state", "config_used"):
        assert key in body, f"missing {key} in response"

    assert isinstance(body["final_state"]["opinions"], list)
    assert all(isinstance(v, (int, float)) for v in body["final_state"]["opinions"])


def test_energy_is_deterministic_for_a_fixed_seed(client):
    payload = {"user_goal": "test goal", "n_agents": 20, "steps": 5, "seed": 123}
    first = client.post("/v1/engine/energy", headers={"X-API-Key": _KEY}, json=payload)
    second = client.post("/v1/engine/energy", headers={"X-API-Key": _KEY}, json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["summary"] == second.json()["summary"]
