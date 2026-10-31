"""Contract tests for the HTTP routers that had the weakest coverage.

At the time of writing: ``benchmarks`` 18 %, ``forecast`` 29 %, ``engine`` 42 %,
``llm`` 40 %. These are the product's public surface — every one is reachable by
an authenticated client — so their auth, validation and failure behaviour needs to
be pinned rather than assumed.

These tests exercise the *contract*, not the numerics: who may call, what is
rejected, and that a success response validates against its DTO.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

AUTH = {"X-API-Key": "dev-secret-key"}
ROUTER_PATHS = ("/v1/simulate", "/v1/forecast", "/v1/benchmarks")


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Authenticated client using the documented dev fallback key."""
    for var in ("GROQ_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("MASSIVE_ENV", "development")
    monkeypatch.setenv("MASSIVE_DEV_FALLBACK", "1")
    return TestClient(app)


class TestAuthIsEnforcedEverywhere:
    """Every documented router must reject an unauthenticated caller."""

    @pytest.mark.parametrize("path", ROUTER_PATHS)
    def test_missing_api_key_is_rejected(self, client: TestClient, path: str):
        response = client.post(path, json={})
        assert response.status_code == 401, f"{path} accepted a request with no API key"

    @pytest.mark.parametrize("path", ROUTER_PATHS)
    def test_wrong_api_key_is_rejected(self, client: TestClient, path: str):
        response = client.post(path, json={}, headers={"X-API-Key": "not-the-key"})
        assert response.status_code == 401


class TestBenchmarkRouter:
    def test_rejects_absolute_cases_path(self, client: TestClient):
        response = client.post(
            "/v1/benchmarks", json={"cases": "/etc/passwd", "mode": "offline"}, headers=AUTH
        )
        assert response.status_code == 400
        assert "relative" in str(response.json()["detail"]).lower()

    def test_rejects_directory_traversal(self, client: TestClient):
        response = client.post(
            "/v1/benchmarks", json={"cases": "a/../../etc", "mode": "offline"}, headers=AUTH
        )
        assert response.status_code == 400
        assert "traversal" in str(response.json()["detail"]).lower()

    def test_rejects_traversal_in_output_path(self, client: TestClient):
        response = client.post(
            "/v1/benchmarks", json={"out": "../escape", "mode": "offline"}, headers=AUTH
        )
        assert response.status_code == 400

    def test_llm_mode_without_key_fails_closed(self, client: TestClient):
        """No provider key configured ⇒ 503, never a silent offline run."""
        response = client.post("/v1/benchmarks", json={"mode": "llm"}, headers=AUTH)
        assert response.status_code == 503
        assert "api key" in str(response.json()["detail"]).lower()

    def test_negative_seed_is_rejected(self, client: TestClient):
        response = client.post("/v1/benchmarks", json={"seed": -1}, headers=AUTH)
        assert response.status_code == 422


class TestForecastRouter:
    def test_requires_simulation_state(self, client: TestClient):
        assert client.post("/v1/forecast", json={}, headers=AUTH).status_code == 422

    def test_analytical_mode_returns_validated_dto(self, client: TestClient):
        response = client.post(
            "/v1/forecast",
            json={"simulation_state": {"opinion": 0.2}, "mode": "analytical"},
            headers=AUTH,
        )
        assert response.status_code == 200
        body = response.json()
        # ForecastResponse shape: a trajectory plus a feasibility verdict.
        assert set(body) >= {"sim_id", "horizon_ticks", "points", "feasibility"}
        assert isinstance(body["points"], list)
        assert body["points"], "forecast returned no points"
        point = body["points"][0]
        assert set(point) >= {"tick", "mean_opinion", "polarization"}
        feasibility = body["feasibility"]
        assert 0.0 <= float(feasibility["score"]) <= 1.0
        assert feasibility["label"]

    def test_invalid_mode_is_rejected(self, client: TestClient):
        response = client.post(
            "/v1/forecast",
            json={"simulation_state": {"opinion": 0.2}, "mode": "not-a-mode"},
            headers=AUTH,
        )
        assert response.status_code == 422

    def test_n_runs_bound_is_enforced(self, client: TestClient):
        response = client.post(
            "/v1/forecast",
            json={"simulation_state": {"opinion": 0.2}, "n_runs": 10_001},
            headers=AUTH,
        )
        assert response.status_code == 422


class TestEngineRouter:
    def test_energy_requires_user_goal(self, client: TestClient):
        assert client.post("/v1/engine/energy", json={}, headers=AUTH).status_code == 422

    def test_energy_rejects_empty_goal(self, client: TestClient):
        response = client.post("/v1/engine/energy", json={"user_goal": ""}, headers=AUTH)
        assert response.status_code == 422

    def test_architect_requires_objective(self, client: TestClient):
        assert client.post("/v1/engine/architect", json={}, headers=AUTH).status_code == 422

    def test_multilayer_rejects_out_of_range_coupling(self, client: TestClient):
        response = client.post("/v1/engine/multilayer", json={"coupling": 99.0}, headers=AUTH)
        assert response.status_code == 422

    def test_multilayer_rejects_population_below_two(self, client: TestClient):
        response = client.post("/v1/engine/multilayer", json={"n_agents": 1}, headers=AUTH)
        assert response.status_code == 422


class TestLlmsRouterValidation:
    def test_run_simulation_rejects_empty_prompt(self, client: TestClient):
        response = client.post("/v1/llm/run_simulation", json={"prompt": ""}, headers=AUTH)
        assert response.status_code == 422

    def test_extract_rejects_unsupported_content(self, client: TestClient):
        """A document upload without a usable payload must fail cleanly."""
        response = client.post("/v1/llm/extract", json={}, headers=AUTH)
        assert response.status_code in (400, 422)


class TestUnknownRoutes:
    def test_unknown_path_is_404(self, client: TestClient):
        assert client.get("/v1/does-not-exist", headers=AUTH).status_code == 404
