"""DTOs for the MASSIVE-LLM orchestration endpoint.

These types govern the request/response contract for ``POST /v1/llm/run_simulation``
as specified in ``configs/llm_contract/massive_llm_contract.json`` (section
``llm_endpoint``).

All models use ``extra="forbid"`` to prevent silent schema drift.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

# Motor families aligned to the contract `supported_flows`.
LLMMotor = Literal[
    "energy_engine",
    "social_architect",
    "forecast",
    "multilayer_engine",
    "massive_engine",
    "micro_massive",
    "benchmark_offline",
    "factbook_validation",
]


class LLMLlmHint(BaseModel):
    """Optional LLM provider/model hint supplied by the client."""

    model_config = {"extra": "forbid"}

    provider: Literal["groq", "openai", "openrouter"] = "groq"
    model: Optional[str] = None


class LLMRunRequest(BaseModel):
    """Request payload for ``POST /v1/llm/run_simulation``.

    Args:
        intent: Natural-language intent describing the desired simulation.
        motor: Optional engine-family override. If omitted, the backend
            classifies intent via the MASSIVE-LLM contract rules.
        country: Optional country name/CIA code for Factbook augmentation.
        partial_config: Optional structured overrides merged atop the
            LLM-translated config.
        llm: Optional provider/model hint.
        simulation_steps: Optional step-count override.
        seed: Optional RNG seed (default 42).
        config_overrides: Optional extra engine-specific configuration keys.
    """

    model_config = {"extra": "forbid"}

    intent: str = Field(..., min_length=1, description="Natural-language intent")
    motor: Optional[LLMMotor] = Field(
        default=None, description="Engine family override"
    )
    country: Optional[str] = Field(
        default=None, description="Country for Factbook augmentation"
    )
    partial_config: Optional[Dict[str, Any]] = Field(
        default=None, description="Structured overrides merged with NL-translated config"
    )
    llm: Optional[LLMLlmHint] = Field(
        default=None, description="LLM provider/model hint"
    )
    simulation_steps: Optional[int] = Field(
        default=None, ge=1, description="Step-count override"
    )
    seed: Optional[int] = Field(
        default=42, ge=0, description="RNG seed for reproducibility"
    )
    config_overrides: Optional[Dict[str, Any]] = Field(
        default=None, description="Extra engine-specific config keys"
    )


# ---------------------------------------------------------------------------
# Response pieces
# ---------------------------------------------------------------------------

class LLMSummary(BaseModel):
    """Normalized summary emitted by the orchestrator."""

    model_config = {"extra": "forbid"}

    motor: str
    indicators: Dict[str, Any]
    regla_dominante: Optional[str] = None
    factbook_country: Optional[str] = None


class LLMTimelinePoint(BaseModel):
    """A single tick from a simulation timeline (abridged history)."""

    model_config = {"extra": "forbid"}

    tick: int
    mean_opinion: Optional[float] = None
    polarization: Optional[float] = None
    active_agents: Optional[int] = None


class LLMResults(BaseModel):
    """Engine-agnostic envelope for raw result artifacts.

    The inner ``payload`` is intentionally ``Dict[str, Any]`` because each
    engine (scalar / energy / architect / forecast) exposes a different shape.
    """

    model_config = {"extra": "forbid"}

    sim_id: str
    motor: LLMMotor
    payload: Dict[str, Any]
    # Abridged timeline (first/last N ticks) for large histories.
    timeline: Optional[List[LLMTimelinePoint]] = None
    final_state: Optional[Dict[str, Any]] = None


class LLMRunResponse(BaseModel):
    """Response payload for ``POST /v1/llm/run_simulation``.

    Args:
        sim_id: Unique run identifier.
        motor: Engine that was dispatched.
        config: Final resolved configuration.
        summary: Normalized numerical indicators + narrative hints.
        narrative: LLM-generated prose summary (``summary.narrative`` mirror).
        results: Engine-specific result artifacts.
        assumptions: Defaults applied / ambiguities resolved.
        factbook_params: Country params injected (when Factbook was used).
    """

    model_config = {"extra": "forbid"}

    sim_id: str
    motor: LLMMotor
    config: Dict[str, Any]
    summary: LLMSummary
    narrative: str
    results: LLMResults
    assumptions: List[str]
    factbook_params: Optional[Dict[str, Any]] = None


class LLMAmbiguityResponse(BaseModel):
    """422 response body returned when intent requires user clarification."""

    model_config = {"extra": "forbid"}

    detail: str = "Intent ambiguous; please provide the requested fields."
    requested_fields: List[str]
    motor: Optional[str] = None
