"""API security surface tests (no live server required for most checks)."""

from __future__ import annotations

import inspect

import api as api_mod


def test_cors_does_not_use_wildcard_with_credentials():
    assert "*" not in api_mod._cors_origins


def test_file_path_rejected_in_simulate_handler_source():
    src = inspect.getsource(api_mod.api_simulate)
    assert "file_path is not allowed" in src


def test_rate_limit_helper_exists():
    assert callable(api_mod._rate_limit)
    assert api_mod._RATE_LIMIT >= 1


def test_app_has_health_routes():
    paths = {getattr(r, "path", None) for r in api_mod.app.routes}
    assert "/health" in paths
    assert "/api/wizard" in paths


def test_app_has_run_route():
    paths = {getattr(r, "path", None) for r in api_mod.app.routes}
    assert "/api/run" in paths


def test_resolved_run_spec_rejects_unknown_fields():
    """ResolvedRunSpec must use extra='forbid' to block prompt-injection fields."""
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        api_mod.ResolvedRunSpec(engine="scalar", injected_field="bad")


def test_resolved_run_spec_defaults():
    spec = api_mod.ResolvedRunSpec()
    assert spec.engine == "scalar"
    assert spec.seed == 42
    assert spec.params == {}
    assert spec.spec_id is None


def test_resolved_run_spec_rejects_unsupported_engine():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        api_mod.ResolvedRunSpec(engine="unknown_engine")


def test_run_receipt_model_fields():
    receipt = api_mod.RunReceipt(
        sim_id="sim-test",
        status="success",
        started_at="2026-07-18T00:00:00Z",
        finished_at="2026-07-18T00:00:01Z",
        seed_used=42,
        engine="scalar",
    )
    assert receipt.status == "success"
    assert receipt.error is None
    assert receipt.checkpoint_path is None


def test_run_receipt_failed_status():
    receipt = api_mod.RunReceipt(
        sim_id="sim-err",
        status="failed",
        started_at="2026-07-18T00:00:00Z",
        finished_at="2026-07-18T00:00:00Z",
        seed_used=42,
        engine="scalar",
        error="ValueError",
    )
    assert receipt.status == "failed"
    assert receipt.error == "ValueError"


def test_run_from_spec_success(tmp_path, monkeypatch):
    """run_from_spec with scalar engine returns a success receipt."""
    import os

    monkeypatch.setenv("MASSIVE_REPORTS_DIR", str(tmp_path))
    # Reload the module so _REPORTS_DIR picks up the monkeypatched env var
    import importlib
    import services.simulation_service as svc

    importlib.reload(svc)

    spec = {
        "engine": "scalar",
        "seed": 42,
        "params": {
            "estado_inicial": {"opinion": 0.0, "propaganda": 0.0},
            "pasos": 3,
            "verbose": False,
        },
    }
    receipt = svc.run_from_spec(spec)
    assert receipt["status"] == "success"
    assert receipt["sim_id"].startswith("sim-")
    assert receipt["seed_used"] == 42
    assert receipt["engine"] == "scalar"
    assert receipt["summary"] is not None
    assert receipt["checkpoint_path"] is not None


def test_run_from_spec_unsupported_engine():
    from services.simulation_service import run_from_spec

    receipt = run_from_spec({"engine": "nonexistent", "seed": 1})
    assert receipt["status"] == "failed"
    assert "unsupported_engine" in receipt["error"]


def test_api_run_endpoint_no_stack_trace_on_failure(monkeypatch):
    """POST /api/run must never surface Python stack traces to the caller."""
    from fastapi.testclient import TestClient

    def _bad_spec(*_a, **_kw):
        raise RuntimeError("boom")

    monkeypatch.setattr("services.simulation_service.run_from_spec", _bad_spec)

    import importlib
    import api as api_reload

    client = TestClient(api_reload.app, raise_server_exceptions=False)
    resp = client.post(
        "/api/run",
        json={"engine": "scalar", "seed": 42, "params": {}},
        headers={"X-API-Key": "default-secret-key"},
    )
    assert resp.status_code == 500
    body = resp.json()
    assert "boom" not in str(body)
    assert "traceback" not in str(body).lower()
