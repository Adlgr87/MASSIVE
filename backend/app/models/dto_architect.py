"""DTOs for the Social Architect domain.

These types represent interventions, audit log entries, and WebSocket events
emitted by the Social Architect inverse-search agent.
All models use ``extra="forbid"`` to prevent silent schema drift.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel


class InterventionRecord(BaseModel):
    """A single intervention phase as planned by the Social Architect.

    Args:
        intervention_id: Unique identifier for this intervention.
        sim_id: Simulation run this intervention targets.
        time_start: Tick index when the intervention begins.
        time_end: Tick index when the intervention ends.
        model_name: Influence model applied (e.g. ``"hk"``, ``"umbral"``).
        parameters: Model-specific numeric parameters (e.g. ``{"epsilon": 0.3}``).
        target_nodes: Optional list of specific agent IDs to intervene on.
        rationale: Optional sociological / organizational justification.
    """

    model_config = {"extra": "forbid"}

    intervention_id: str
    sim_id: str
    time_start: int
    time_end: int
    model_name: str
    parameters: Dict[str, Any]
    target_nodes: Optional[List[str]] = None
    rationale: Optional[str] = None


class InterventionLogEntry(BaseModel):
    """Audit log entry recording the observed effect of an intervention tick.

    Args:
        entry_id: Unique log entry identifier.
        intervention_id: The intervention that caused this effect.
        tick: Tick at which the effect was measured.
        timestamp: UTC timestamp of the measurement.
        effect_delta: Change in mean opinion attributed to the intervention.
        notes: Optional free-text notes.
    """

    model_config = {"extra": "forbid"}

    entry_id: str
    intervention_id: str
    tick: int
    timestamp: datetime
    effect_delta: float
    notes: Optional[str] = None


class ArchitectEventMessage(BaseModel):
    """WebSocket message emitted when the Architect applies an intervention.

    Args:
        type: Discriminator field, always ``"architect_event"``.
        sim_id: Simulation run identifier.
        intervention: The intervention being applied.
        timestamp: UTC timestamp of the event.
        schema_version: Optional DTO schema version.
    """

    model_config = {"extra": "forbid"}

    type: Literal["architect_event"] = "architect_event"
    sim_id: str
    intervention: InterventionRecord
    timestamp: datetime
    schema_version: Optional[str] = None
