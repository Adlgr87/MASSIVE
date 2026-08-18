"""UI-NG backend test suite (Next-Gen UI — production path).

Covers the app factory, auth, rate limiting, the heuristic translator
contract, all engine adapters, run persistence (SQLite) and SSE streaming.
Run with::

    python -m pytest tests/test_ui_ng.py -q
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.run_store import RunStore
from backend.app.settings import UISettings


def _settings(**overrides) -> UISettings:
    base = dict(
        env="test",
        serve_frontend=False,
        data_dir=None,
        api_keys=[],
        rate_limit_enabled=False,
        trust_proxy_headers=False,
    )
    base.update(overrides)
    return UISettings(**base)


@pytest.fixture()
def client():
    app = create_app(_settings())
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_client():
    app = create_app(_settings(api_keys=["secret-123"]))
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def limited_client():
    app = create_app(
        _settings(
            rate_limit_enabled=True, rate_limit_per_minute=120, rate_limit_simulate_per_minute=2
        )
    )
    with TestClient(app) as c:
        yield c


# ─────────────────────────────────────────────────────────────────────────────
# Basics
# ─────────────────────────────────────────────────────────────────────────────


def test_health_and_root(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "MASSIVE UI-NG API"
    assert body["store"] == "ok"

    r = client.get("/api/status")
    assert r.status_code == 200
    s = r.json()
    assert set(s["engines"]) == {"scalar", "energy", "multilayer", "massive"}
    assert s["llm"]["configured"] is False
    assert set(s["languages"]) == {"es", "en"}


# ─────────────────────────────────────────────────────────────────────────────
# Conversation (translator contract)
# ─────────────────────────────────────────────────────────────────────────────


def test_conversation_heuristic_es(client):
    r = client.post(
        "/api/conversation",
        json={
            "language": "es",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "En mi ciudad lanzan una campaña muy agresiva y la gente "
                        "ya desconfía de las instituciones, hay mucha polarización."
                    ),
                }
            ],
        },
    )
    assert r.status_code == 200
    d = r.json()
    assert d["action"] == "propose"
    assert d["mode"] == "heuristic"
    assert len(d["assumptions"]) >= 3
    assert len(d["questions"]) <= 3
    params = {a["parameter"] for a in d["assumptions"]}
    assert {"propaganda", "confianza", "sesgo_confirmacion"} <= params
    draft = d["config_draft"]
    assert set(draft["estado_inicial"]) >= {"opinion", "propaganda", "confianza"}
    assert 5 <= draft["pasos"] <= 200


def test_conversation_english_with_country(client):
    r = client.post(
        "/api/conversation",
        json={
            "language": "en",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "What would happen with polarization if a party launches an "
                        "aggressive campaign before elections in Mexico with 40% support?"
                    ),
                }
            ],
        },
    )
    assert r.status_code == 200
    d = r.json()
    assert d["mode"] == "heuristic"
    draft = d["config_draft"]
    assert abs(draft["estado_inicial"]["opinion"] - 0.4) <= 0.05
    assert draft["config"].get("factbook_country") == "MX"
    assert draft["pasos"] >= 60


def test_conversation_empty_messages_400(client):
    # Pydantic rejects min_length violations at validation time (422).
    r = client.post("/api/conversation", json={"language": "es", "messages": []})
    assert r.status_code in (400, 422)


def test_conversation_stream_sse(client):
    with client.stream(
        "POST",
        "/api/conversation/stream",
        json={
            "language": "es",
            "messages": [{"role": "user", "content": "hay mucha polarización y desconfianza"}],
        },
    ) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        text = "".join(resp.iter_text())
    assert "event: status" in text
    assert "event: done" in text
    # Extract the done payload (the event carrying the full turn contract).
    done_lines = [
        line_ for line_ in text.splitlines() if line_.startswith("data: {") and '"action"' in line_
    ]
    payload = json.loads(done_lines[-1][len("data: ") :])
    assert payload["mode"] == "heuristic"
    assert payload["action"] == "propose"


# ─────────────────────────────────────────────────────────────────────────────
# Simulation endpoints
# ─────────────────────────────────────────────────────────────────────────────

_SCALAR = {
    "engine": "scalar",
    "pasos": 30,
    "scientific": True,
    "language": "es",
    "audience": "general",
    "estado_inicial": {"opinion": 0.4, "propaganda": 0.8, "confianza": 0.3},
    "config": {"sesgo_confirmacion": 0.5, "seed": 7},
}


def test_simulate_scalar(client):
    r = client.post("/api/simulate", json=_SCALAR)
    assert r.status_code == 200
    d = r.json()
    assert d["run_id"]
    assert d["engine"] == "scalar"
    assert d["mode"] == "heuristic"
    assert "opinion_final" in d["summary"]
    assert d["scientific_report"]["stability_label"] in ("stable", "marginal", "unstable")
    assert "¿Qué pasó?" in d["narrative"]
    assert len(d["highlights"]) >= 4
    assert len(d["series"]["opinion"]) == 31


def test_simulate_energy(client):
    r = client.post(
        "/api/simulate",
        json={
            "engine": "energy",
            "pasos": 25,
            "n_agents": 30,
            "range_type": "bipolar",
            "scientific": False,
            "language": "es",
            "audience": "general",
            "estado_inicial": {},
            "config": {},
        },
    )
    assert r.status_code == 200
    d = r.json()
    assert d["summary"]["regla_dominante"] == "langevin_energy"
    assert len(d["series"]["opinion"]) == 26


def test_simulate_multilayer(client):
    r = client.post(
        "/api/simulate",
        json={
            "engine": "multilayer",
            "pasos": 20,
            "n_agents": 40,
            "scientific": False,
            "language": "en",
            "audience": "general",
            "estado_inicial": {},
            "config": {},
        },
    )
    assert r.status_code == 200
    d = r.json()
    assert d["summary"]["regla_dominante"] == "multilayer_langevin"
    assert "What happened" in d["narrative"]


def test_simulate_unknown_engine_400(client):
    # Pydantic rejects non-Literal engine values at validation time (422).
    r = client.post("/api/simulate", json={**_SCALAR, "engine": "quantum"})
    assert r.status_code in (400, 422)


def test_simulate_stream_sse(client):
    with client.stream("POST", "/api/simulate/stream", json=_SCALAR) as resp:
        assert resp.status_code == 200
        text = "".join(resp.iter_text())
    assert "event: status" in text
    assert "event: done" in text
    done_lines = [
        line_ for line_ in text.splitlines() if line_.startswith("data: {") and '"run_id"' in line_
    ]
    payload = json.loads(done_lines[-1][len("data: ") :])
    assert payload["run_id"]
    assert payload["summary"]["opinion_final"] is not None


# ─────────────────────────────────────────────────────────────────────────────
# Runs CRUD + explain
# ─────────────────────────────────────────────────────────────────────────────


def test_runs_crud_and_explain(client):
    r = client.post("/api/simulate", json=_SCALAR)
    run_id = r.json()["run_id"]

    r = client.get("/api/runs")
    assert r.status_code == 200
    ids = [x["run_id"] for x in r.json()]
    assert run_id in ids

    r = client.get(f"/api/runs/{run_id}?language=en&audience=tecnico")
    assert r.status_code == 200
    d = r.json()
    assert "What happened" in d["narrative"]

    r = client.post(
        "/api/explain",
        json={"run_id": run_id, "language": "en", "audience": "general"},
    )
    assert r.status_code == 200
    assert r.json()["mode"] in ("template", "llm")

    r = client.delete(f"/api/runs/{run_id}")
    assert r.status_code == 200
    r = client.get(f"/api/runs/{run_id}")
    assert r.status_code == 404


def test_explain_unknown_404(client):
    r = client.post(
        "/api/explain",
        json={"run_id": "does-not-exist", "language": "es", "audience": "general"},
    )
    assert r.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Security & rate limiting
# ─────────────────────────────────────────────────────────────────────────────


def test_auth_required_when_keys_configured(auth_client):
    # Protected routers: /api/conversation and /api/runs (simulation router).
    r = auth_client.post(
        "/api/conversation",
        json={"language": "es", "messages": [{"role": "user", "content": "hola"}]},
    )
    assert r.status_code == 401

    r = auth_client.get("/api/runs")
    assert r.status_code == 401

    r = auth_client.get("/api/runs", headers={"X-API-Key": "wrong"})
    assert r.status_code == 401

    r = auth_client.get("/api/runs", headers={"X-API-Key": "secret-123"})
    assert r.status_code == 200

    # /api/status and /health stay open for UI bootstrapping and probes.
    assert auth_client.get("/api/status").status_code == 200
    assert auth_client.get("/health").status_code == 200


def test_rate_limit_on_simulate(limited_client):
    req = dict(_SCALAR)
    first = limited_client.post("/api/simulate", json=req)
    assert first.status_code == 200
    second = limited_client.post("/api/simulate", json=req)
    assert second.status_code == 200  # limit is 2/min
    third = limited_client.post("/api/simulate", json=req)
    assert third.status_code == 429
    assert "Retry-After" in third.headers


# ─────────────────────────────────────────────────────────────────────────────
# RunStore (SQLite persistence)
# ─────────────────────────────────────────────────────────────────────────────


def test_run_store_sqlite_persistence(tmp_path: Path):
    db = tmp_path / "runs.db"
    store = RunStore(db_path=db, capacity=10)
    payload = {
        "engine": "scalar",
        "mode": "heuristic",
        "language": "es",
        "summary": {"opinion_inicial": 0.1, "opinion_final": 0.9},
        "scientific_report": {"stability_label": "stable"},
        "series": {"t": [0, 1], "opinion": [0.1, 0.9]},
        "meta": {},
    }
    rid = store.put(payload)
    assert store.count() == 1
    assert store.get(rid)["summary"]["opinion_final"] == 0.9
    assert store.list()[0]["run_id"] == rid

    # A second instance reading the same DB file sees the run (persistence).
    store2 = RunStore(db_path=db, capacity=10)
    assert store2.get(rid) is not None
    assert store2.count() == 1

    assert store.delete(rid) is True
    assert store2.get(rid) is None


def test_run_store_memory_mode():
    store = RunStore(db_path=None, capacity=3)
    for i in range(5):
        store.put(
            {
                "engine": "scalar",
                "mode": "heuristic",
                "language": "es",
                "summary": {"opinion_inicial": i, "opinion_final": i},
                "scientific_report": None,
                "series": {},
                "meta": {},
            }
        )
    assert store.count() == 3  # capacity trims
