"""Regression tests for two defects found during the repository sweep.

Both were silent: nothing failed, nothing logged, and the symptom only showed
up to whoever happened to look at the right thing afterwards.
"""

from __future__ import annotations

import sys

import pytest

pytest.importorskip("networkx", reason="canonical app needs the full stack")

from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def fresh_app(monkeypatch):
    """Reload `backend.app` under a patched environment.

    Other test modules hold references to the original module objects through
    cached fixtures, so `sys.modules` must end up pointing at exactly what was
    there before — deleting the reloaded modules is not enough.
    """
    saved = {m: sys.modules[m] for m in list(sys.modules) if m.startswith("backend.app")}

    def _build(env: dict[str, str]):
        for key in (
            "MASSIVE_ENV",
            "MASSIVE_API_KEY",
            "MASSIVE_API_KEYS",
            "MASSIVE_DEV_FALLBACK",
            "MASSIVE_ALLOWED_HOSTS",
        ):
            monkeypatch.delenv(key, raising=False)
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        for name in [m for m in list(sys.modules) if m.startswith("backend.app")]:
            del sys.modules[name]
        import backend.app.main as main

        return main.app

    try:
        yield _build
    finally:
        for name in [m for m in list(sys.modules) if m.startswith("backend.app")]:
            del sys.modules[name]
        sys.modules.update(saved)


class TestVersionedSpecIsReadOnly:
    """`GET /openapi/v1.json` used to mutate the app's cached schema in place.

    One request permanently stripped every non-/v1 route from `/openapi.json`
    and `/docs`, and rewrote the API title, for the lifetime of the process.
    """

    def test_main_schema_survives_a_request_to_the_v1_projection(self, fresh_app):
        app = fresh_app({"MASSIVE_ENV": "development"})
        client = TestClient(app)

        paths_before = set(app.openapi()["paths"])
        title_before = app.openapi()["info"]["title"]

        assert client.get("/openapi/v1.json").status_code == 200

        assert set(app.openapi()["paths"]) == paths_before
        assert app.openapi()["info"]["title"] == title_before

    def test_infra_routes_remain_documented(self, fresh_app):
        app = fresh_app({"MASSIVE_ENV": "development"})
        client = TestClient(app)
        client.get("/openapi/v1.json")

        paths = set(app.openapi()["paths"])
        for route in ("/health", "/ready", "/version", "/metrics"):
            assert route in paths, f"{route} vanished from the schema"

    def test_projection_itself_is_still_narrowed(self, fresh_app):
        """The filtering must keep working — the fix is a copy, not a removal."""
        app = fresh_app({"MASSIVE_ENV": "development"})
        spec = TestClient(app).get("/openapi/v1.json").json()
        assert spec["paths"]
        assert all(p.startswith("/v1") for p in spec["paths"])
        assert spec["info"]["title"] == "MASSIVE UIL API v1"

    def test_repeated_requests_are_stable(self, fresh_app):
        app = fresh_app({"MASSIVE_ENV": "development"})
        client = TestClient(app)
        first = client.get("/openapi/v1.json").json()
        second = client.get("/openapi/v1.json").json()
        assert first == second


class TestMultiKeyRotation:
    """`MASSIVE_API_KEYS` was documented in the README and shipped in
    `.env.example`, but no code read it: an operator rotating credentials with
    it had their keys silently ignored."""

    PATH = "/v1/simulate"

    @staticmethod
    def _status(app, key: str | None) -> int:
        headers = {"X-API-Key": key} if key else {}
        with TestClient(app) as client:
            return client.post(TestMultiKeyRotation.PATH, json={}, headers=headers).status_code

    def test_plural_variable_alone_authenticates(self, fresh_app):
        app = fresh_app({"MASSIVE_ENV": "development", "MASSIVE_API_KEYS": "beta,gamma"})
        assert self._status(app, "beta") != 401
        assert self._status(app, "gamma") != 401

    def test_singular_variable_still_authenticates(self, fresh_app):
        app = fresh_app({"MASSIVE_ENV": "development", "MASSIVE_API_KEY": "alpha"})
        assert self._status(app, "alpha") != 401

    def test_both_variables_are_accepted_together(self, fresh_app):
        """The actual rotation window: old key and new key valid at once."""
        app = fresh_app(
            {
                "MASSIVE_ENV": "development",
                "MASSIVE_API_KEY": "old-key",
                "MASSIVE_API_KEYS": "new-key",
            }
        )
        assert self._status(app, "old-key") != 401
        assert self._status(app, "new-key") != 401

    def test_whitespace_around_keys_is_tolerated(self, fresh_app):
        app = fresh_app({"MASSIVE_ENV": "development", "MASSIVE_API_KEYS": " spaced , other "})
        assert self._status(app, "spaced") != 401
        assert self._status(app, "other") != 401

    def test_unlisted_key_is_still_rejected(self, fresh_app):
        app = fresh_app({"MASSIVE_ENV": "development", "MASSIVE_API_KEYS": "beta"})
        assert self._status(app, "wrong") == 401
        assert self._status(app, None) == 401

    def test_empty_entries_do_not_authenticate(self, fresh_app):
        """`MASSIVE_API_KEYS=",,"` must not become "accept the empty key"."""
        app = fresh_app({"MASSIVE_ENV": "production", "MASSIVE_API_KEYS": ",,  ,"})
        with TestClient(app) as client:
            resp = client.post(self.PATH, json={}, headers={"X-API-Key": "", "Host": "testserver"})
        assert resp.status_code in (400, 503)

    def test_fail_closed_is_preserved_when_nothing_is_configured(self, fresh_app):
        app = fresh_app({"MASSIVE_ENV": "production", "MASSIVE_ALLOWED_HOSTS": "testserver"})
        assert self._status(app, "anything") == 503
