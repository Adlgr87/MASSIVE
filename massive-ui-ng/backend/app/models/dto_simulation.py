"""DTOs for live simulation messages over WebSocket.

This module contains only the message types exchanged between the MASSIVE
simulation engine and connected clients (browser / API consumers).
All models use ``extra="forbid"`` to prevent silent schema drift.

Naming convention: snake_case in Python and JSON (zero migration friction).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class SimMode(str, Enum):
    """Operating mode of a simulation snapshot."""

    live = "live"
    replay = "replay"


class SimEventKind(str, Enum):
    """Lifecycle events emitted by the simulation engine."""

    started = "started"
    stopped = "stopped"
    reset = "reset"
    error = "error"


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------


class SimAgentLite(BaseModel):
    """Lightweight agent representation suitable for real-time streaming.

    Keeps the payload small: only identity, position, and opinion.
    Use ``metadata`` for optional domain-specific attributes.

    Args:
        id: Unique agent identifier.
        layer: Network layer the agent belongs to (e.g. ``"social"``, ``"info"``).
        x: Spatial x-coordinate.
        y: Spatial y-coordinate.
        z: Spatial z-coordinate (default 0 for 2-D layouts).
        opinion: Opinion value; unipolar ``[0, 1]`` or bipolar ``[-1, 1]``.
        metadata: Optional free-form dict for domain-specific attributes.
    """

    model_config = {"extra": "forbid"}

    id: str
    layer: str
    x: float
    y: float
    z: float = 0.0
    opinion: float = Field(..., ge=-1.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = None


class SimAggregateMetrics(BaseModel):
    """Aggregate population-level metrics for one simulation tick.

    Args:
        mean_opinion: Population mean opinion.
        std_opinion: Standard deviation of opinions across all agents.
        polarization: Polarization index (higher → more split).
        dominant_rule: Name of the influence rule with highest activation.
        consensus_rate: Fraction of agent pairs whose opinions differ < 0.1.
        fragmentation_index: Structural fragmentation of the opinion network.
        active_agents: Number of agents that updated their opinion this tick.
        schema_version: Optional DTO schema version for forward-compatibility.
    """

    model_config = {"extra": "forbid"}

    mean_opinion: float
    std_opinion: float
    polarization: float
    dominant_rule: str
    consensus_rate: float
    fragmentation_index: float
    active_agents: int
    schema_version: Optional[str] = None


# ---------------------------------------------------------------------------
# Payload
# ---------------------------------------------------------------------------


class SimulationSnapshotPayload(BaseModel):
    """State snapshot for a single tick, embedded inside ``SimSnapshotMessage``.

    Args:
        tick: Simulation tick index (0-based).
        metrics: Aggregate metrics at this tick.
        agents: Optional per-agent data (omit for bandwidth-constrained streams).
        mode: Whether the snapshot comes from a live run or a replay.
        schema_version: Optional DTO schema version.
    """

    model_config = {"extra": "forbid"}

    tick: int
    metrics: SimAggregateMetrics
    agents: Optional[List[SimAgentLite]] = None
    mode: SimMode = SimMode.live
    schema_version: Optional[str] = None


# ---------------------------------------------------------------------------
# WebSocket messages
# ---------------------------------------------------------------------------


class SimSnapshotMessage(BaseModel):
    """WebSocket message carrying a full state snapshot.

    Args:
        type: Discriminator field, always ``"snapshot"``.
        sim_id: Unique simulation run identifier.
        timestamp: Server-side UTC timestamp of the snapshot.
        payload: The snapshot payload.
        schema_version: Optional DTO schema version.
    """

    model_config = {"extra": "forbid"}

    type: Literal["snapshot"] = "snapshot"
    sim_id: str
    timestamp: datetime
    payload: SimulationSnapshotPayload
    schema_version: Optional[str] = None


class SimEventMessage(BaseModel):
    """WebSocket message signalling a simulation lifecycle event.

    Args:
        type: Discriminator field, always ``"event"``.
        sim_id: Unique simulation run identifier.
        event: The lifecycle event kind.
        detail: Optional human-readable detail (e.g. error message).
        schema_version: Optional DTO schema version.
    """

    model_config = {"extra": "forbid"}

    type: Literal["event"] = "event"
    sim_id: str
    event: SimEventKind
    detail: Optional[str] = None
    schema_version: Optional[str] = None
