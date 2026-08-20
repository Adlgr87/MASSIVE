"""Live WebSocket + metrics tests for the UI-NG backend.

Covers the step-wise live runners, the /ws/live endpoint (energy + massive,
auth, client stop/shock commands) and the Prometheus /metrics endpoint.
"""

from __future__ import annotations

import pytest
from backend.app.live_runner import LiveEnergySim, LiveMassiveSim
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect as _WsDisconnect

from backend.app.main import create_app
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


# ─────────────────────────────────────────────────────────────────────────────
# Runners (unit)
# ─────────────────────────────────────────────────────────────────────────────


def test_live_energy_runner_snapshots():
    runner = LiveEnergySim(n_agents=12, connectivity=0.3, seed=1)
    for _ in range(8):
        runner.step()
    snap = runner.snapshot()
    assert snap.tick == 8
    assert snap.mode == "live"
    assert len(snap.agents) == 12
    assert snap.metrics.dominant_rule == "langevin_energy"
    assert 0.0 <= snap.metrics.consensus_rate <= 1.0
    assert 0.0 <= snap.metrics.fragmentation_index <= 1.0
    for a in snap.agents:
        assert -1.0 <= a.opinion <= 1.0
        assert -1.0 <= a.x <= 1.0 and -1.0 <= a.y <= 1.0


def test_live_massive_runner_and_shock():
    runner = LiveMassiveSim(n_agents=3000, seed=2)
    for _ in range(3):
        runner.step()
    snap = runner.snapshot()
    assert snap.tick == 15  # 3 chunks × 5 steps
    assert snap.agents is None  # aggregate-only at scale
    assert snap.metrics.dominant_rule == "super_agents_langevin"
    assert snap.metrics.active_agents >= 0

    runner.shock(0.4, 0.3)  # must not raise
    runner.step()
    assert runner.snapshot().tick == 20


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket endpoint
# ─────────────────────────────────────────────────────────────────────────────


def _collect_ws(client: TestClient, url: str) -> list[dict]:
    messages: list[dict] = []
    with client.websocket_connect(url) as ws:
        while True:
            try:
                messages.append(ws.receive_json())
            except _WsDisconnect:
                break
    return messages


def test_ws_live_energy_stream(client):
    url = (
        "/ws/live?engine=energy&n_agents=8&pasos=6&tick_interval_ms=0&seed=7&user_goal=caos_social"
    )
    msgs = _collect_ws(client, url)
    events = [m for m in msgs if m["type"] == "event"]
    snaps = [m for m in msgs if m["type"] == "snapshot"]
    assert events[0]["event"] == "started"
    assert events[-1]["event"] == "stopped"
    assert len(snaps) == 6
    ticks = [s["payload"]["tick"] for s in snaps]
    assert ticks == sorted(ticks)
    assert ticks[0] == 1 and ticks[-1] == 6
    assert len(snaps[0]["payload"]["agents"]) == 8
    assert snaps[0]["payload"]["mode"] == "live"


def test_ws_live_massive_stream_with_shock(client):
    url = "/ws/live?engine=massive&n_agents=2000&pasos=10&tick_interval_ms=0&seed=3"
    with client.websocket_connect(url) as ws:
        started = ws.receive_json()
        assert started["type"] == "event" and started["event"] == "started"
        first = ws.receive_json()
        assert first["type"] == "snapshot"
        assert first["payload"]["agents"] is None
        # Interactive shock mid-run.
        ws.send_json({"action": "shock", "value": 0.5, "fraction": 0.3})
        saw_error = False
        last_event = None
        while True:
            try:
                msg = ws.receive_json()
            except _WsDisconnect:
                break
            if msg["type"] == "event":
                last_event = msg
                if msg["event"] == "error":
                    saw_error = True
        assert not saw_error
        assert last_event is not None and last_event["event"] == "stopped"


def test_ws_live_client_stop(client):
    url = "/ws/live?engine=energy&n_agents=8&pasos=300&tick_interval_ms=20&seed=1"
    with client.websocket_connect(url) as ws:
        started = ws.receive_json()
        assert started["event"] == "started"
        first = ws.receive_json()
        assert first["type"] == "snapshot"
        ws.send_json({"action": "stop"})
        msgs: list[dict] = []
        while True:
            try:
                msgs.append(ws.receive_json())
            except _WsDisconnect:
                break
        events = [m for m in msgs if m["type"] == "event"]
        stopped = events[-1] if events else None
        assert stopped is not None and stopped["event"] == "stopped"
        assert "client-requested" in stopped.get("detail", "")


def test_ws_live_auth_required():
    app = create_app(_settings(api_keys=["live-secret"]))
    with TestClient(app) as client:
        # Without a key the server closes the socket with 4401.
        with client.websocket_connect("/ws/live?engine=energy&n_agents=8&pasos=3") as ws:
            with pytest.raises(_WsDisconnect) as excinfo:
                ws.receive_json()
            assert excinfo.value.code == 4401

        # With the right key the stream runs.
        with client.websocket_connect(
            "/ws/live?engine=energy&n_agents=8&pasos=3&api_key=live-secret&tick_interval_ms=0"
        ) as ws:
            assert ws.receive_json()["event"] == "started"


def test_ws_live_unknown_engine_rejected(client):
    with client.websocket_connect("/ws/live?engine=quantum&n_agents=8&pasos=3") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "event" and msg["event"] == "error"


# ─────────────────────────────────────────────────────────────────────────────
# Metrics endpoint
# ─────────────────────────────────────────────────────────────────────────────


def test_metrics_endpoint(client):
    # Generate some traffic first.
    client.get("/health")
    client.post(
        "/api/simulate",
        json={
            "engine": "scalar",
            "pasos": 20,
            "scientific": False,
            "language": "es",
            "audience": "general",
            "estado_inicial": {"opinion": 0.4, "propaganda": 0.7, "confianza": 0.4},
            "config": {"seed": 1},
        },
    )

    r = client.get("/metrics")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    body = r.text
    assert "# TYPE http_requests_total counter" in body
    assert 'http_requests_total{group="simulate"' in body
    assert 'simulations_total{engine="scalar"}' in body
    assert "# TYPE ws_snapshots_total counter" in body
