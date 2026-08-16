"""DTOs for historical snapshot and timeline queries.

These types are used by REST endpoints that return stored simulation data,
distinct from the live WebSocket message types in ``dto_simulation``.
All models use ``extra="forbid"`` to prevent silent schema drift.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SnapshotRecord(BaseModel):
    """A single stored snapshot record retrieved from persistence.

    Args:
        snapshot_id: Unique identifier for this snapshot record.
        sim_id: Simulation run that generated this snapshot.
        tick: Tick index at the time of the snapshot.
        timestamp: UTC timestamp when the snapshot was persisted.
        data: Raw snapshot data (metrics + optional agent states).
    """

    model_config = {"extra": "forbid"}

    snapshot_id: str
    sim_id: str
    tick: int
    timestamp: datetime
    data: Dict[str, Any]


class TimelineTick(BaseModel):
    """Condensed metrics for one tick in a timeline response.

    Args:
        tick: Tick index.
        mean_opinion: Population mean opinion at this tick.
        polarization: Polarization index at this tick.
        dominant_rule: Name of the dominant influence rule.
        timestamp: Optional UTC timestamp when the tick was recorded.
    """

    model_config = {"extra": "forbid"}

    tick: int
    mean_opinion: float
    polarization: float
    dominant_rule: str
    timestamp: Optional[datetime] = None


class TimelineResponse(BaseModel):
    """Paginated timeline for a simulation run.

    Args:
        sim_id: Simulation run identifier.
        ticks: Ordered list of condensed tick metrics.
        total: Total number of ticks available in the run.
    """

    model_config = {"extra": "forbid"}

    sim_id: str
    ticks: List[TimelineTick]
    total: int
