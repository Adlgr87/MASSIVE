"""DTOs for the LLM run_simulation contract (configs/llm_contract).

These models are the typed contract between the UI-NG backend and the
``POST /v1/llm/run_simulation`` endpoint. Pydantic v2 with ``extra="forbid"``
to catch contract drift early.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from backend.app.models.dto_simulation import SimAggregateMetrics
from backend.app.models.dto_snapshot import TimelineTick

MotorName = str

MOTOR_ENUM = (
    "multilayer_engine",
    "energy_engine",
    "massive_engine",
    "forecast_model",
    "micro_massive",
    "benchmark_runner",
    "factbook_validation",
    "scalar_legacy",
)


class LLMRunRequest(BaseModel):
    """Payload for one NL intent → simulation run.

    Args:
        intent: Free-text natural-language intent (min 5 chars).
        country_code: Optional ISO-3166-1 alpha-2 hint (e.g. BR, US).
        temporal_horizon: Horizon in days (1..3650), default 90.
        confidence_level: Statistical confidence for bounds (0.8..0.99).
        scenario: Named scenario; ``intervention`` requires intervention_config.
        intervention_config: Structured intervention description.
        hypothesis: Explicit hypothesis to evaluate against results.
        detail_level: Narrative detail granularity.
        motor_override: Force a specific engine instead of classifying.
        api_key: Optional provider key override (mainly for tests).
    """

    model_config = {"extra": "forbid"}

    intent: str = Field(min_length=5, max_length=2000, description="NL intent")
    country_code: Optional[str] = Field(
        default=None,
        pattern=r"^[A-Z]{2}$",
        description="ISO-3166-1 alpha-2 country code",
    )
    temporal_horizon: Optional[int] = Field(default=90, ge=1, le=3650)
    confidence_level: float = Field(default=0.95, ge=0.80, le=0.99)
    scenario: str = Field(default="baseline")
    intervention_config: Optional[dict[str, Any]] = None
    hypothesis: Optional[str] = None
    detail_level: str = Field(default="medium")
    motor_override: Optional[str] = None
    api_key: Optional[str] = None


class LLMRunResponse(BaseModel):
    """Structured result of an LLM-orchestrated run.

    Args:
        simulation_id: UUID for the run.
        classified_motor: Engine that executed the intent.
        country_code_resolved: Resolved country code or ``'none'``.
        assumptions: Assumptions declared by the orchestrator.
        result: Aggregate metrics + timeline ticks.
        narrative_summary: Human-readable summary of results.
        hypothesis_evaluated: How the hypothesis relates to the outcome.
        confidence_bounds: Statistical bounds around the headline metric.
        artifacts: Generated artifacts (file references / inline data).
    """

    model_config = {"extra": "forbid"}

    simulation_id: str
    classified_motor: str
    country_code_resolved: str
    assumptions: list[str]
    result: dict[str, Any]
    narrative_summary: str
    hypothesis_evaluated: str
    confidence_bounds: dict[str, Any]
    artifacts: dict[str, Any] = Field(default_factory=dict)


class LLMAmbiguityResponse(BaseModel):
    """422 response when intent classification needs more information.

    Args:
        detail: Human-readable description of the ambiguity.
        requested_fields: Client-facing fields the user should supply.
    """

    model_config = {"extra": "forbid"}

    detail: str
    requested_fields: list[str]
