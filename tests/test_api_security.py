"""API security surface tests (no live server required for most checks)."""

from __future__ import annotations

import inspect

import pytest

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


# ---------------------------------------------------------------------------
# Auth parity between legacy api.py and canonical backend.app (SEC-02/SEC-03).
# Both backends must share identical environment + key-matching semantics.
#
# The canonical app pulls the full engine stack (networkx, pandas, ...) via
# services.simulation_service; the lightweight CI "api" job only installs
# numpy/scipy. Import it lazily so this module stays collectable there and
# the parity tests run wherever the full stack is available.
# ---------------------------------------------------------------------------

from fastapi.testclient import TestClient  # noqa: E402


def _canonical_app():
    pytest.importorskip("networkx", reason="canonical app needs the full stack")
    from backend.app.main import app

    return app


def _probe_status(app, path: str, headers: dict) -> int:
    """POST an (invalid) body; auth middleware must answer before validation."""
    with TestClient(app) as client:
        resp = client.post(path, json={}, headers=headers)
    return resp.status_code


def _auth_probe(app, path: str, api_key: str | None) -> int:
    headers = {"X-API-Key": api_key} if api_key is not None else {}
    return _probe_status(app, path, headers)


_LEGACY_PATH = "/api/v1/forecast"
_CANONICAL_PATH = "/v1/simulate"

_ENV_CASES = [
    # (MASSIVE_ENV, expected_status_without_key)
    (None, 401),  # unset -> dev fallback active -> key required (wrong/absent key -> 401)
    ("development", 401),
    ("dev", 401),  # legacy alias
    ("staging", 503),  # fail-closed: no key configured
    ("production", 503),
]


def test_legacy_env_semantics(monkeypatch):
    import api as api_mod

    for env_value, expected in _ENV_CASES:
        monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
        if env_value is None:
            monkeypatch.delenv("MASSIVE_ENV", raising=False)
        else:
            monkeypatch.setenv("MASSIVE_ENV", env_value)
        # Recreate the app so module-level env is irrelevant (auth reads env per-request).
        status = _auth_probe(api_mod.app, _LEGACY_PATH, None)
        assert status == expected, f"legacy MASSIVE_ENV={env_value!r}: {status} != {expected}"


def test_canonical_env_semantics(monkeypatch):
    canonical_app = _canonical_app()
    for env_value, expected in _ENV_CASES:
        monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
        if env_value is None:
            monkeypatch.delenv("MASSIVE_ENV", raising=False)
        else:
            monkeypatch.setenv("MASSIVE_ENV", env_value)
        status = _auth_probe(canonical_app, _CANONICAL_PATH, None)
        assert status == expected, f"canonical MASSIVE_ENV={env_value!r}: {status} != {expected}"


def test_both_backends_accept_dev_fallback_key(monkeypatch):
    import api as api_mod

    canonical_app = _canonical_app()
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    monkeypatch.delenv("MASSIVE_ENV", raising=False)
    assert _auth_probe(api_mod.app, _LEGACY_PATH, "dev-secret-key") != 401
    assert _auth_probe(canonical_app, _CANONICAL_PATH, "dev-secret-key") != 401


def test_both_backends_reject_wrong_key_when_configured(monkeypatch):
    import api as api_mod

    canonical_app = _canonical_app()
    monkeypatch.setenv("MASSIVE_API_KEY", "testkey111")
    for app, path in ((api_mod.app, _LEGACY_PATH), (canonical_app, _CANONICAL_PATH)):
        assert _auth_probe(app, path, "wrong-key") == 401
        assert _auth_probe(app, path, None) == 401
        # Correct key passes auth (may fail validation with 422 — never 401/503).
        status = _auth_probe(app, path, "testkey111")
        assert status not in (401, 503)


def test_constant_time_comparison_helper():
    from massive_core.config import api_key_matches

    assert api_key_matches("k", "k") is True
    assert api_key_matches("k", "x") is False
    assert api_key_matches(None, "k") is False
    assert api_key_matches("k", "") is False
    assert api_key_matches("ключ", "ключ") is True  # non-ascii safe
