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
