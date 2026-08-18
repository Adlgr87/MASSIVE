"""Live simulation WebSocket router.

Endpoint: ``/ws/live``

The client connects with query parameters describing the run (engine, size,
landscape archetype, seed, horizon) and receives:

- ``SimEventMessage`` lifecycle events (started / stopped / error)
- ``SimSnapshotMessage`` payloads every tick (energy engine) or chunk
  (massive engine), following the DTOs in ``dto_simulation.py``.

Client → server commands (JSON):
- ``{"action": "stop"}`` — end the run cleanly.
- ``{"action": "shock", "value": float, "fraction": float}`` — massive
  engine only; perturbs a fraction of super-agents mid-run.

Authentication: browsers cannot set WebSocket headers, so the API key is
passed as ``?api_key=...`` when ``MASSIVE_API_KEYS`` is configured. The same
key validation (constant-time) as the REST routers is used.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from backend.app.live_runner import LiveEnergySim, LiveMassiveSim
from backend.app.metrics import registry
from backend.app.models.dto_simulation import (
    SimEventKind,
    SimEventMessage,
    SimSnapshotMessage,
)
from backend.app.security import api_key_is_valid

log = logging.getLogger("massive.ui_ng.live")

router = APIRouter(tags=["live"])

# ── Limits (server-side; the UI exposes a narrower range) ──────────────────
_ENERGY_MAX_AGENTS = 200
_MASSIVE_MAX_AGENTS = 200_000
_MAX_STEPS = 600
_ENERGY_ARCHETYPES = [
    "polarizacion_extrema",
    "polarizacion_moderada",
    "consenso_moderado",
    "consenso_forzado",
    "fragmentacion_3_grupos",
    "fragmentacion_4_grupos",
    "caos_social",
    "radicalizacion_progresiva",
]


async def _drain_commands(ws: WebSocket, queue: asyncio.Queue) -> None:
    """Background task: forward client commands into the queue."""
    try:
        while True:
            message = await ws.receive_json()
            action = message.get("action") if isinstance(message, dict) else None
            await queue.put(message if action in ("stop", "shock") else {"action": "stop"})
    except Exception:  # noqa: BLE001 — disconnect ends the listener
        pass


@router.websocket("/ws/live")
async def ws_live(
    ws: WebSocket,
    engine: str = Query("energy"),
    n_agents: int = Query(60),
    connectivity: float = Query(0.25),
    range_type: str = Query("bipolar"),
    seed: int = Query(42),
    pasos: int = Query(120),
    user_goal: str = Query("polarizacion_moderada"),
    tick_interval_ms: int = Query(40),
    api_key: str | None = Query(None),
) -> None:
    """Stream a live simulation (see module docstring)."""
    registry.inc("ws_connections_total")
    await ws.accept()

    # ── Auth (query-param key; same validation as the REST routers) ───────
    keys = getattr(ws.app.state, "api_keys", [])
    if keys and (not api_key or not api_key_is_valid(api_key, keys)):
        await ws.close(code=4401)
        return

    # ── Validate parameters ────────────────────────────────────────────────
    if engine not in ("energy", "massive"):
        await ws.send_json(
            SimEventMessage(
                sim_id="",
                event=SimEventKind.error,
                detail=f"unknown engine: {engine}",
            ).model_dump(mode="json")
        )
        await ws.close(code=4400)
        return
    pasos = max(1, min(pasos, _MAX_STEPS))
    tick_ms = max(0, min(tick_interval_ms, 500))

    # ── Build runner ───────────────────────────────────────────────────────
    sim_id = uuid.uuid4().hex[:12]
    try:
        if engine == "energy":
            n_agents = max(2, min(n_agents, _ENERGY_MAX_AGENTS))
            runner = LiveEnergySim(
                n_agents=n_agents,
                connectivity=float(np_clip(connectivity, 0.01, 1.0)),
                range_type=range_type if range_type in ("bipolar", "unipolar") else "bipolar",
                seed=seed,
                user_goal=user_goal if user_goal in _ENERGY_ARCHETYPES else "polarizacion_moderada",
            )
        else:
            n_agents = max(100, min(n_agents, _MASSIVE_MAX_AGENTS))
            runner = LiveMassiveSim(n_agents=n_agents, seed=seed)
    except Exception as exc:  # noqa: BLE001
        log.exception("live runner construction failed")
        await ws.send_json(
            SimEventMessage(
                sim_id=sim_id,
                event=SimEventKind.error,
                detail=f"runner init failed: {exc}",
            ).model_dump(mode="json")
        )
        await ws.close(code=4400)
        return

    # ── Run loop ───────────────────────────────────────────────────────────
    queue: asyncio.Queue = asyncio.Queue()
    listener = asyncio.create_task(_drain_commands(ws, queue))

    await ws.send_json(
        SimEventMessage(
            sim_id=sim_id,
            event=SimEventKind.started,
            detail=f"engine={engine} agents={n_agents} pasos={pasos}",
        ).model_dump(mode="json")
    )

    stopped_by_client = False
    try:
        while runner.tick < pasos:
            # Listen for commands without blocking the stream.
            try:
                cmd = await asyncio.wait_for(queue.get(), timeout=0.05)
            except TimeoutError:
                cmd = None
            if cmd is not None:
                action = cmd.get("action")
                if action == "stop":
                    stopped_by_client = True
                    registry.inc("ws_stops_total")
                    break
                if action == "shock":
                    if engine == "massive":
                        runner.shock(
                            value=float(cmd.get("value", 0.3)),
                            fraction=float(cmd.get("fraction", 0.2)),
                        )
                        registry.inc("ws_shocks_total")
                    else:
                        await ws.send_json(
                            SimEventMessage(
                                sim_id=sim_id,
                                event=SimEventKind.error,
                                detail="shock is only available for the massive engine",
                            ).model_dump(mode="json")
                        )
                    continue

            runner.step()
            snapshot = runner.snapshot()
            registry.inc("ws_snapshots_total")
            await ws.send_json(
                SimSnapshotMessage(
                    sim_id=sim_id,
                    timestamp=datetime.now(UTC),
                    payload=snapshot,
                ).model_dump(mode="json")
            )
            if tick_ms > 0 and engine == "energy":
                await asyncio.sleep(tick_ms / 1000.0)

        await ws.send_json(
            SimEventMessage(
                sim_id=sim_id,
                event=SimEventKind.stopped,
                detail="client-requested stop" if stopped_by_client else "horizon reached",
            ).model_dump(mode="json")
        )
    except WebSocketDisconnect:
        log.info("live client disconnected (sim %s)", sim_id)
    except Exception as exc:  # noqa: BLE001
        log.exception("live loop failed (sim %s)", sim_id)
        with contextlib.suppress(Exception):  # noqa: BLE001
            await ws.send_json(
                SimEventMessage(
                    sim_id=sim_id,
                    event=SimEventKind.error,
                    detail=str(exc),
                ).model_dump(mode="json")
            )
    finally:
        listener.cancel()
        with contextlib.suppress(Exception):  # noqa: BLE001
            await ws.close()


def np_clip(v: float, lo: float, hi: float) -> float:
    """Clip without importing numpy at module import time."""
    return float(max(lo, min(hi, v)))
