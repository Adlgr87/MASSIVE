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

# (MASSIVE_ENV, MASSIVE_DEV_FALLBACK, expected_status_without_key)
# Dev fallback now requires BOTH MASSIVE_ENV=development AND MASSIVE_DEV_FALLBACK.
_ENV_CASES = [
    # Fail-closed: no key configured and dev fallback not explicitly opted in.
    (None, None, 503),  # unset env → fail-closed
    ("development", None, 503),  # dev env but no MASSIVE_DEV_FALLBACK → fail-closed
    ("dev", None, 503),  # legacy alias, no MASSIVE_DEV_FALLBACK → fail-closed
    ("staging", None, 503),  # fail-closed
    ("production", None, 503),  # fail-closed
    # Opt-in dev fallback: MASSIVE_ENV=development + MASSIVE_DEV_FALLBACK set.
    ("development", "1", 401),  # dev fallback active → key required → 401
    ("dev", "1", 401),  # legacy alias + opt-in → 401
    # MASSIVE_DEV_FALLBACK ignored outside development.
    ("staging", "1", 503),
    ("production", "1", 503),
]


def _set_env(monkeypatch, env_value, dev_fallback):
    if env_value is None:
        monkeypatch.delenv("MASSIVE_ENV", raising=False)
    else:
        monkeypatch.setenv("MASSIVE_ENV", env_value)
    if dev_fallback is None:
        monkeypatch.delenv("MASSIVE_DEV_FALLBACK", raising=False)
    else:
        monkeypatch.setenv("MASSIVE_DEV_FALLBACK", dev_fallback)


def test_legacy_env_semantics(monkeypatch):
    import api as api_mod

    for env_value, dev_fb, expected in _ENV_CASES:
        monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
        _set_env(monkeypatch, env_value, dev_fb)
        status = _auth_probe(api_mod.app, _LEGACY_PATH, None)
        assert status == expected, (
            f"legacy MASSIVE_ENV={env_value!r} MASSIVE_DEV_FALLBACK={dev_fb!r}: "
            f"{status} != {expected}"
        )


def test_canonical_env_semantics(monkeypatch):
    canonical_app = _canonical_app()
    for env_value, dev_fb, expected in _ENV_CASES:
        monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
        _set_env(monkeypatch, env_value, dev_fb)
        status = _auth_probe(canonical_app, _CANONICAL_PATH, None)
        assert status == expected, (
            f"canonical MASSIVE_ENV={env_value!r} MASSIVE_DEV_FALLBACK={dev_fb!r}: "
            f"{status} != {expected}"
        )


def test_both_backends_accept_dev_fallback_key(monkeypatch):
    """Dev fallback requires BOTH MASSIVE_ENV=development AND MASSIVE_DEV_FALLBACK."""
    import api as api_mod

    canonical_app = _canonical_app()
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    monkeypatch.setenv("MASSIVE_ENV", "development")
    monkeypatch.setenv("MASSIVE_DEV_FALLBACK", "1")
    assert _auth_probe(api_mod.app, _LEGACY_PATH, "dev-secret-key") != 401
    assert _auth_probe(canonical_app, _CANONICAL_PATH, "dev-secret-key") != 401


def test_both_backends_reject_dev_fallback_without_opt_in(monkeypatch):
    """Without MASSIVE_DEV_FALLBACK, dev-secret-key must NOT authenticate."""
    import api as api_mod

    canonical_app = _canonical_app()
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    monkeypatch.setenv("MASSIVE_ENV", "development")
    monkeypatch.delenv("MASSIVE_DEV_FALLBACK", raising=False)
    assert _auth_probe(api_mod.app, _LEGACY_PATH, "dev-secret-key") == 503
    assert _auth_probe(canonical_app, _CANONICAL_PATH, "dev-secret-key") == 503


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


def test_is_dev_env_none_is_false():
    """is_dev_env(None) must be False (fail-closed when MASSIVE_ENV unset)."""
    from massive_core.config import is_dev_env

    assert is_dev_env(None) is False
    assert is_dev_env("") is False
    assert is_dev_env("staging") is False
    assert is_dev_env("production") is False
    assert is_dev_env("development") is True
    assert is_dev_env("dev") is True


def test_constant_time_comparison_helper():
    from massive_core.config import api_key_matches

    assert api_key_matches("k", "k") is True
    assert api_key_matches("k", "x") is False
    assert api_key_matches(None, "k") is False
    assert api_key_matches("k", "") is False
    assert api_key_matches("ключ", "ключ") is True  # non-ascii safe


# ---------------------------------------------------------------------------
# Host header allow-list (A-03): must fail CLOSED outside development.
# ---------------------------------------------------------------------------


class TestHostHeaderFailsClosed:
    """Guards against the fail-open host validation fixed in Phase C.

    Two independent defects made production fail OPEN: the two branches of
    ``validate_host_header`` were textually identical (both called through),
    and the anti-wildcard guard emptied the allow-list, which then matched the
    "no allow-list -> open mode" branch.
    """

    @pytest.fixture(autouse=True)
    def _restore_backend_modules(self):
        """Restore the original ``backend.app.*`` modules after each test.

        These tests reload the app with a patched environment. Simply deleting
        the reloaded modules is not enough: other test modules hold references
        to the *original* ``app`` object through cached fixtures, so the real
        requirement is that ``sys.modules`` ends up pointing at exactly the
        module objects that were there before.
        """
        import sys

        saved = {m: sys.modules[m] for m in list(sys.modules) if m.startswith("backend.app")}
        try:
            yield
        finally:
            for name in [m for m in list(sys.modules) if m.startswith("backend.app")]:
                del sys.modules[name]
            sys.modules.update(saved)

    @staticmethod
    def _client(monkeypatch, env):
        import importlib
        import sys

        for key in ("MASSIVE_ENV", "MASSIVE_ALLOWED_HOSTS"):
            monkeypatch.delenv(key, raising=False)
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        for name in [m for m in list(sys.modules) if m.startswith("backend.app")]:
            del sys.modules[name]
        from fastapi.testclient import TestClient

        import backend.app.main as main

        return TestClient(importlib.reload(main).app)

    def test_dev_without_allowlist_is_open(self, monkeypatch):
        client = self._client(monkeypatch, {"MASSIVE_ENV": "development"})
        assert client.get("/health", headers={"host": "evil.com"}).status_code != 400

    def test_prod_without_allowlist_rejects(self, monkeypatch):
        client = self._client(monkeypatch, {"MASSIVE_ENV": "production"})
        assert client.get("/health", headers={"host": "evil.com"}).status_code == 400

    def test_prod_wildcard_is_not_honoured(self, monkeypatch):
        client = self._client(
            monkeypatch, {"MASSIVE_ENV": "production", "MASSIVE_ALLOWED_HOSTS": "*"}
        )
        assert client.get("/health", headers={"host": "evil.com"}).status_code == 400

    def test_unset_env_defaults_to_fail_closed(self, monkeypatch):
        client = self._client(monkeypatch, {})
        assert client.get("/health", headers={"host": "evil.com"}).status_code == 400

    def test_prod_allowlist_accepts_listed_host_only(self, monkeypatch):
        client = self._client(
            monkeypatch,
            {"MASSIVE_ENV": "production", "MASSIVE_ALLOWED_HOSTS": "massive.example.com"},
        )
        assert client.get("/health", headers={"host": "massive.example.com"}).status_code != 400
        assert client.get("/health", headers={"host": "evil.com"}).status_code == 400


# ---------------------------------------------------------------------------
# Upload limits + extension allow-list must be identical across both API
# surfaces (M-01) and must honour MASSIVE_MAX_UPLOAD_MB.
# ---------------------------------------------------------------------------


class TestUploadLimitsAreUnified:
    def test_both_surfaces_accept_and_reject_the_same_extensions(self):
        """Behavioural check: the two `_safe_suffix` gates must agree.

        Asserting on a module-level constant would not catch the real defect
        (the surfaces disagreeing on a given filename), and the legacy module
        no longer needs to re-export the allow-list now that it delegates.
        """
        pytest.importorskip("networkx", reason="canonical app needs the full stack")
        import backend.app.routers.llm as router_mod
        from massive_core.config.uploads import ALLOWED_UPLOAD_EXTENSIONS

        for ext in ALLOWED_UPLOAD_EXTENSIONS:
            name = f"upload{ext}"
            assert api_mod._safe_suffix(name) == ext
            assert router_mod._safe_suffix(name) == ext

        for bad in (".exe", ".sh", ".zip"):
            name = f"payload{bad}"
            for surface in (api_mod, router_mod):
                with pytest.raises(Exception) as excinfo:
                    surface._safe_suffix(name)
                assert getattr(excinfo.value, "status_code", None) == 400

    def test_max_upload_mb_is_honoured(self, monkeypatch):
        from massive_core.config.uploads import max_upload_bytes

        monkeypatch.setenv("MASSIVE_MAX_UPLOAD_MB", "3")
        assert max_upload_bytes() == 3 * 1024 * 1024

    def test_malformed_max_upload_mb_fails_safe_to_default(self, monkeypatch):
        from massive_core.config.uploads import DEFAULT_MAX_UPLOAD_MB, max_upload_bytes

        for bogus in ("not-a-number", "", "0", "-5"):
            monkeypatch.setenv("MASSIVE_MAX_UPLOAD_MB", bogus)
            assert max_upload_bytes() == DEFAULT_MAX_UPLOAD_MB * 1024 * 1024

    def test_disallowed_extension_is_rejected(self):
        from massive_core.config.uploads import safe_suffix

        with pytest.raises(ValueError):
            safe_suffix("payload.exe")
        assert safe_suffix("report.pdf") == ".pdf"


def test_frontend_does_not_hardcode_dev_api_key():
    """The client must never ship a credential literal (A-02)."""
    from pathlib import Path

    source = Path(__file__).resolve().parents[1] / "frontend" / "src" / "services" / "api.ts"
    text = source.read_text(encoding="utf-8")
    code = "\n".join(
        line for line in text.splitlines() if not line.strip().startswith(("//", "*", "/*"))
    )
    assert "dev-secret-key" not in code
