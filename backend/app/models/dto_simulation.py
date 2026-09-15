"""DTOs for live simulation messages over WebSocket.

This module contains only the message types exchanged between the MASSIVE
simulation engine and connected clients (browser / API consumers).
All models use ``extra="forbid"`` to prevent silent schema drift.

Naming convention: snake_case in Python and JSON (zero migration friction).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

class SimMode(StrEnum):
    """Operating mode of a simulation snapshot."""

    live = "live"
    replay = "replay"

class SimEventKind(StrEnum):
    """Lifecycle events emitted by the simulation engine."""

    started = "started"
    stopped = "stopped"
    reset = "reset"
    error = "error"

class SimAgentLite(BaseModel):
    """Lightweight agent representation suitable for real-time streaming.."""

    model_config = {"extra": "forbid"}

    id: str
    layer: str
    x: float
    y: float
    z: float = 0.0
    opinion: float = Field(..., ge=-1.0, le=1.0)
    metadata: dict[str, Any] | None = None

class SimAggregateMetrics(BaseModel):
    """Aggregate population-level metrics for one simulation tick.."""

    model_config = {"extra": "forbid"}

    mean_opinion: float
    std_opinion: float
    polarization: float
    dominant_rule: str
    consensus_rate: float
    fragmentation_index: float
    active_agents: int
    schema_version: str | None = None

class SimulationSnapshotPayload(BaseModel):
    """State snapshot for a single tick, embedded inside ``SimSnapshotMessage``.."""

    model_config = {"extra": "forbid"}

    tick: int
    metrics: SimAggregateMetrics
    agents: list[SimAgentLite] | None = None
    mode: SimMode = SimMode.live
    schema_version: str | None = None

class SimSnapshotMessage(BaseModel):
    """WebSocket message carrying a full state snapshot.."""

    model_config = {"extra": "forbid"}

    type: Literal["snapshot"] = "snapshot"
    sim_id: str
    timestamp: datetime
    payload: SimulationSnapshotPayload
    schema_version: str | None = None

class SimEventMessage(BaseModel):
    """WebSocket message signalling a simulation lifecycle event.."""

    model_config = {"extra": "forbid"}

    type: Literal["event"] = "event"
    sim_id: str
    event: SimEventKind
    detail: str | None = None
    schema_version: str | None = None
