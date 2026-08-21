"""Observability tests for the canonical backend (request-id, readiness).

Hito 4 of the production-readiness plan (docs/production-readiness-audit.md):

- ``X-Request-ID`` must be present on every response (echoed when provided).
- ``/ready`` decides readiness on REQUIRED dependencies only (settings +
  simulation core). Optional LLM credentials degrade ``/v1/llm/*`` but must
  not pull the whole service out of rotation (503).
"""

from __future__ import annotations

import os
import sys

import pytest
from fastapi.testclient import TestClient

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.app.main import app  # noqa: E402

_PROVIDER_KEY_VARS = ("GROQ_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY")


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    for var in _PROVIDER_KEY_VARS:
        monkeypatch.delenv(var, raising=False)
    return TestClient(app)


def test_request_id_generated(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    rid = resp.headers.get("x-request-id")
    assert rid, "X-Request-ID must always be present"
    assert len(rid) >= 8


def test_request_id_echoed_when_provided(client: TestClient):
    resp = client.get("/health", headers={"X-Request-ID": "corr-1234"})
    assert resp.status_code == 200
    assert resp.headers.get("x-request-id") == "corr-1234"


def test_ready_without_llm_keys_is_200_degraded(client: TestClient):
    """/ready must NOT 503 when only OPTIONAL deps are missing."""
    resp = client.get("/ready")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "ready"
    assert data["mode"] == "degraded"
    assert data["checks"]["settings"] == "ok"
    assert data["checks"]["simulation_core"] == "ok"
    assert data["checks"]["llm_provider"] == "not_configured"


def test_ready_with_llm_keys_is_200_full(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GROQ_API_KEY", "testkey111")
    resp = client.get("/ready")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["mode"] == "full"
    assert data["checks"]["llm_provider"] == "available"


def test_health_is_liveness_only(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


# ---------------------------------------------------------------------------
# Metrics endpoint (Hito 4)
# ---------------------------------------------------------------------------


def test_metrics_endpoint_prometheus_text(client: TestClient):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    body = resp.text
    assert "# TYPE http_requests_total counter" in body
    assert "http_requests_total{" in body  # at least one series recorded
    assert "massive_uptime_seconds" in body


def test_metrics_records_requests_by_group(client: TestClient):
    client.get("/health")
    client.get("/metrics")
    resp = client.get("/metrics")
    body = resp.text
    # The three infra calls above must be counted
    assert 'group="infra"' in body
    assert 'method="GET"' in body
    assert 'status="200"' in body


def test_body_size_limit_rejects_oversized_payload(client: TestClient, monkeypatch):
    """Requests with declared Content-Length above MASSIVE_MAX_BODY_MB get 413."""
    monkeypatch.setenv("MASSIVE_MAX_BODY_MB", "1")  # reload app to pick it up?
    # _MAX_BODY_BYTES is read at import time; re-import would need a fresh app.
    # Instead verify the guard logic against the imported constant:
    import backend.app.main as main_mod

    limit = main_mod._MAX_BODY_BYTES
    assert limit >= 1 * 1024 * 1024
    # Oversized declared length -> 413 without reading the body
    resp = client.post(
        "/v1/simulate",
        content=b"x",
        headers={"Content-Type": "application/json", "Content-Length": str(limit + 1)},
    )
    assert resp.status_code == 413
    assert "exceeds" in resp.json()["detail"]


def test_body_size_limit_allows_normal_payload(client: TestClient):
    resp = client.post(
        "/v1/simulate",
        json={"pasos": 3},
        headers={"X-API-Key": "dev-secret-key"},
    )
    assert resp.status_code == 200
