"""Temporal configuration model for the MASSIVE forecast engine."""

from __future__ import annotations

import math
from datetime import date
from typing import ClassVar, Literal

from pydantic import BaseModel, Field


EventType = Literal[
    "viral_online",
    "protest_campaign",
    "labor_conflict",
    "electoral_campaign",
    "policy_adoption",
    "cultural_shift",
]


class TemporalConfig(BaseModel):
    """Calendar-aware temporal settings for forecast runs."""

    model_config = {"extra": "forbid"}

    _DEFAULTS: ClassVar[dict[str, dict[str, int]]] = {
        "viral_online": {"step_duration_days": 1, "time_horizon_days": 14},
        "protest_campaign": {"step_duration_days": 2, "time_horizon_days": 30},
        "labor_conflict": {"step_duration_days": 7, "time_horizon_days": 90},
        "electoral_campaign": {"step_duration_days": 7, "time_horizon_days": 120},
        "policy_adoption": {"step_duration_days": 30, "time_horizon_days": 365},
        "cultural_shift": {"step_duration_days": 60, "time_horizon_days": 720},
    }

    step_duration_days: int = Field(7, ge=1)
    time_horizon_days: int = Field(90, ge=1)
    event_type: EventType = "labor_conflict"
    calendar_start: date | None = None
    notes: str = ""

    @property
    def n_steps(self) -> int:
        """Discrete simulation steps needed to cover the configured horizon."""
        return int(math.ceil(self.time_horizon_days / self.step_duration_days))

    @classmethod
    def from_event_type(
        cls,
        event_type: EventType,
        *,
        calendar_start: date | None = None,
        notes: str = "",
    ) -> "TemporalConfig":
        """Builds a TemporalConfig using event-type defaults."""
        defaults = cls._DEFAULTS[event_type]
        return cls(
            event_type=event_type,
            step_duration_days=defaults["step_duration_days"],
            time_horizon_days=defaults["time_horizon_days"],
            calendar_start=calendar_start,
            notes=notes,
        )
