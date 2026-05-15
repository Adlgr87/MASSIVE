"""backend.app.models — public surface for all domain DTOs.

Import any model from this single namespace::

    from backend.app.models import SimSnapshotMessage, ForecastResponse

All models are Pydantic v2 with ``extra="forbid"`` to catch contract drift early.
"""

from backend.app.models.dto_architect import (
    ArchitectEventMessage,
    InterventionLogEntry,
    InterventionRecord,
)
from backend.app.models.dto_forecast import (
    Feasibility,
    ForecastPoint,
    ForecastResponse,
)
from backend.app.models.dto_simulation import (
    SimAgentLite,
    SimAggregateMetrics,
    SimEventKind,
    SimEventMessage,
    SimMode,
    SimSnapshotMessage,
    SimulationSnapshotPayload,
)
from backend.app.models.dto_snapshot import (
    SnapshotRecord,
    TimelineTick,
    TimelineResponse,
)

__all__ = [
    # simulation (live WebSocket)
    "SimAgentLite",
    "SimAggregateMetrics",
    "SimulationSnapshotPayload",
    "SimSnapshotMessage",
    "SimEventMessage",
    "SimMode",
    "SimEventKind",
    # snapshot (historical REST)
    "SnapshotRecord",
    "TimelineTick",
    "TimelineResponse",
    # forecast
    "ForecastPoint",
    "Feasibility",
    "ForecastResponse",
    # architect
    "InterventionRecord",
    "InterventionLogEntry",
    "ArchitectEventMessage",
]
